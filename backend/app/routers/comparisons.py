from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit import audit
from app.deps import client_ip, get_current_user, get_db, get_doc_or_404
from app.models import AnalysisJob, Comparison, ComparisonChange, User
from app.schemas import ComparisonIn, ComparisonList, ComparisonOut

router = APIRouter(prefix="/api/comparisons", tags=["comparisons"])


@router.get("", response_model=ComparisonList)
def list_comparisons(
    page: int = 1,
    page_size: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Comparison).order_by(Comparison.created_at.desc())
    if user.role != "admin":
        query = query.filter(Comparison.created_by == user.id)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(min(page_size, 200)).all()
    out = []
    for c in items:
        c.changes = (
            db.query(ComparisonChange)
            .filter(ComparisonChange.comparison_id == c.id)
            .order_by(ComparisonChange.id)
            .all()
        )
        out.append(c)
    return ComparisonList(items=out, total=total)


@router.post("", response_model=ComparisonOut, status_code=201)
def create_comparison(
    body: ComparisonIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot create comparisons")
    if body.doc_a_id == body.doc_b_id:
        raise HTTPException(status_code=422, detail="Cannot compare a document with itself")
    doc_a = get_doc_or_404(db, body.doc_a_id, user)
    doc_b = get_doc_or_404(db, body.doc_b_id, user)
    for d in (doc_a, doc_b):
        if d.status != "ready":
            raise HTTPException(
                status_code=409,
                detail=f"Document '{d.original_name}' must be analyzed before comparison",
            )

    cmp_ = Comparison(doc_a_id=doc_a.id, doc_b_id=doc_b.id, created_by=user.id)
    db.add(cmp_)
    db.commit()
    db.refresh(cmp_)

    job = AnalysisJob(comparison_id=cmp_.id, kind="comparison", status="queued")
    db.add(job)
    audit(
        db, "compare", "comparison", cmp_.id,
        f"{doc_a.id} vs {doc_b.id}", user.id, client_ip(request),
    )
    db.commit()
    cmp_.changes = []
    return cmp_


@router.get("/{cmp_id}", response_model=ComparisonOut)
def get_comparison(
    cmp_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cmp_ = db.get(Comparison, cmp_id)
    if not cmp_ or (cmp_.created_by != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Comparison not found")
    cmp_.changes = (
        db.query(ComparisonChange)
        .filter(ComparisonChange.comparison_id == cmp_.id)
        .order_by(ComparisonChange.id)
        .all()
    )
    return cmp_
