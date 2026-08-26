from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Clause, Comparison, Document, RiskFinding, Summary, User
from app.schemas import DashboardStats

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats/dashboard", response_model=DashboardStats)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    base = db.query(Document)
    if user.role != "admin":
        base = base.filter(Document.owner_id == user.id)

    docs = base.all()
    doc_ids = [d.id for d in docs]

    risks_q = db.query(RiskFinding)
    clauses_q = db.query(Clause)
    summaries_q = db.query(Summary)
    comparisons_q = db.query(Comparison)
    if doc_ids:
        risks_q = risks_q.filter(RiskFinding.document_id.in_(doc_ids))
        clauses_q = clauses_q.filter(Clause.document_id.in_(doc_ids))
        summaries_q = summaries_q.filter(Summary.document_id.in_(doc_ids))
    else:
        risks_q = risks_q.filter(False)
        clauses_q = clauses_q.filter(False)
        summaries_q = summaries_q.filter(False)
    if user.role != "admin":
        comparisons_q = comparisons_q.filter(Comparison.created_by == user.id)

    risks = risks_q.all()
    clauses = clauses_q.all()
    comparisons_count = comparisons_q.count()
    summaries = summaries_q.all()

    sev_counts = Counter(r.severity for r in risks)
    cat_counts = Counter(c.category for c in clauses)
    risk_cat_counts = Counter(r.category for r in risks)
    high_docs = {
        d.id for d in docs
        if any(r.document_id == d.id and r.severity in ("high", "critical") for r in risks)
    }

    # Health scores per document
    docs_health = []
    health_scores = []
    for s in summaries:
        health_scores.append(s.health_score)
        docs_health.append({
            "document_id": s.document_id,
            "title": next((d.title or d.original_name for d in docs if d.id == s.document_id), f"Doc #{s.document_id}"),
            "health_score": s.health_score,
            "health_verdict": s.health_verdict or "",
        })
    docs_health.sort(key=lambda x: x["health_score"])
    avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else None

    # Pending reviews (clauses + risks not yet reviewed)
    pending_clauses = db.query(Clause).filter(Clause.review_status == "pending")
    pending_risks = db.query(RiskFinding).filter(RiskFinding.review_status == "pending")
    if doc_ids:
        pending_clauses = pending_clauses.filter(Clause.document_id.in_(doc_ids))
        pending_risks = pending_risks.filter(RiskFinding.document_id.in_(doc_ids))
    pending = pending_clauses.count() + pending_risks.count()
    # Active users
    active_users = db.query(User).count()

    recent = sorted(docs, key=lambda d: d.created_at, reverse=True)[:6]
    return DashboardStats(
        total_documents=len(docs),
        analyzed_documents=sum(1 for d in docs if d.status in ("ready", "failed")),
        ready_documents=sum(1 for d in docs if d.status == "ready"),
        failed_documents=sum(1 for d in docs if d.status == "failed"),
        high_risk_documents=len(high_docs),
        total_clauses=len(clauses),
        total_risks=len(risks),
        total_comparisons=comparisons_count,
        severity_histogram=dict(sev_counts),
        clause_category_counts=dict(cat_counts),
        recent_documents=recent,
        avg_health_score=avg_health,
        documents_health=docs_health,
        risk_category_counts=dict(risk_cat_counts),
        pending_reviews=pending,
        active_users=active_users,
    )
