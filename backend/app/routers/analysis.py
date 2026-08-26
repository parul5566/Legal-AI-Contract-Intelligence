from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit import audit
from app.deps import client_ip, get_current_user, get_db, get_doc_or_404
from app.models import Clause, Document, ReviewAction, RiskFinding, User
from app.schemas import (
    ClauseOut,
    ReviewActionOut,
    ReviewIn,
    RiskOut,
    SummaryOut,
)

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/documents/{doc_id}/clauses", response_model=list[ClauseOut])
def document_clauses(
    doc_id: int,
    category: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = get_doc_or_404(db, doc_id, user)
    query = db.query(Clause).filter(Clause.document_id == doc.id)
    if category:
        query = query.filter(Clause.category == category)
    return query.order_by(Clause.char_start).all()


@router.get("/documents/{doc_id}/risks", response_model=list[RiskOut])
def document_risks(
    doc_id: int,
    severity: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = get_doc_or_404(db, doc_id, user)
    query = db.query(RiskFinding).filter(RiskFinding.document_id == doc.id)
    if severity:
        query = query.filter(RiskFinding.severity == severity)
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    risks = query.all()
    return sorted(risks, key=lambda r: order.get(r.severity, 4))


@router.get("/documents/{doc_id}/summary", response_model=SummaryOut)
def document_summary(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = get_doc_or_404(db, doc_id, user)
    if not doc.summary:
        raise HTTPException(status_code=404, detail="Summary not available yet")
    return doc.summary


@router.post("/documents/{doc_id}/summary/regenerate", response_model=SummaryOut)
def regenerate_summary(
    doc_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot regenerate summaries")
    doc = get_doc_or_404(db, doc_id, user)
    if doc.status != "ready":
        raise HTTPException(status_code=409, detail="Document is not analyzed yet")

    from app.engine.clauses import ClauseCandidate
    from app.engine.summarizer import summarize

    clauses = (
        db.query(Clause).filter(Clause.document_id == doc.id).order_by(Clause.char_start).all()
    )
    risks = db.query(RiskFinding).filter(RiskFinding.document_id == doc.id).all()
    full_text = "\n\n".join(s.body for s in sorted(doc.sections, key=lambda s: s.idx))

    cands = [
        ClauseCandidate(
            category=c.category, text=c.text, char_start=c.char_start,
            char_end=c.char_end, page=c.page, section_id=c.section_id,
            confidence=c.confidence, title=c.title, source=c.source,
        )
        for c in clauses
    ]
    from app.engine.risks import RiskHit

    hits = [
        RiskHit(
            category=r.category, severity=r.severity, title=r.title,
            explanation=r.explanation, suggestion=r.suggestion, evidence=r.evidence,
            confidence=r.confidence, clause_index=None,
        )
        for r in risks
    ]
    summ = summarize(doc.title or doc.original_name, full_text, cands, hits)

    if doc.summary:
        for k, v in summ.items():
            setattr(doc.summary, k, v)
    else:
        from app.models import Summary

        doc.summary = Summary(document_id=doc.id, **summ)
    audit(db, "summary_regenerate", "document", doc.id, None, user.id, client_ip(request))
    db.commit()
    db.refresh(doc.summary)
    return doc.summary


def _do_review(
    db: Session,
    request: Request,
    user: User,
    target_type: str,
    target: Clause | RiskFinding,
    body: ReviewIn,
    document_id: int,
):
    valid_actions = ("accept", "reject", "correct", "comment", "flag")
    if body.action not in valid_actions:
        raise HTTPException(status_code=422, detail="Invalid action")
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot review findings")

    if body.action == "accept":
        target.review_status = "accepted"
    elif body.action == "reject":
        target.review_status = "rejected"
    elif body.action == "correct":
        target.review_status = "corrected"
        if target_type == "clause" and body.category:
            from app.engine.taxonomy import CLAUSE_CATEGORIES

            if body.category not in CLAUSE_CATEGORIES:
                raise HTTPException(status_code=422, detail="Unknown clause category")
            target.category = body.category
    elif body.action in ("comment", "flag"):
        target.review_status = target.review_status  # unchanged

    if hasattr(target, "reviewer_id"):
        target.reviewer_id = user.id
    if hasattr(target, "review_note"):
        target.review_note = body.note or None

    db.add(
        ReviewAction(
            document_id=document_id,
            actor_id=user.id,
            target_type=target_type,
            target_id=target.id,
            action=body.action,
            detail=body.note,
        )
    )
    audit(
        db, f"review_{body.action}", target_type, target.id,
        (body.note or "")[:500], user.id, client_ip(request),
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/clauses/{clause_id}/review", response_model=ClauseOut)
def review_clause(
    clause_id: int,
    body: ReviewIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clause = db.get(Clause, clause_id)
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")
    get_doc_or_404(db, clause.document_id, user)
    return _do_review(db, request, user, "clause", clause, body, clause.document_id)


@router.post("/risks/{risk_id}/review", response_model=RiskOut)
def review_risk(
    risk_id: int,
    body: ReviewIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    risk = db.get(RiskFinding, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    get_doc_or_404(db, risk.document_id, user)
    return _do_review(db, request, user, "risk", risk, body, risk.document_id)


@router.get("/documents/{doc_id}/review-log", response_model=list[ReviewActionOut])
def review_log(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc: Document = get_doc_or_404(db, doc_id, user)
    return (
        db.query(ReviewAction)
        .filter(ReviewAction.document_id == doc.id)
        .order_by(ReviewAction.created_at.desc())
        .limit(200)
        .all()
    )
