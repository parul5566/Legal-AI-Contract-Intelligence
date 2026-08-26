from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    String,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"
ROLE_VIEWER = "viewer"

DOC_STATUSES = ("pending", "parsing", "analyzing", "ready", "failed")
SEVERITIES = ("low", "medium", "high", "critical")
REVIEW_STATUSES = ("pending", "accepted", "rejected", "corrected")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER, name="user_role"),
        default=ROLE_VIEWER,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    documents: Mapped[list["Document"]] = relationship(back_populates="owner")



class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(*DOC_STATUSES, name="doc_status"), default="pending", index=True
    )
    doc_type: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(255))
    parties: Mapped[list | None] = mapped_column(JSON)
    effective_date: Mapped[str | None] = mapped_column(String(64))
    expiry_date: Mapped[str | None] = mapped_column(String(64))
    jurisdiction: Mapped[str | None] = mapped_column(String(128))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime)

    owner: Mapped[User] = relationship(back_populates="documents")
    sections: Mapped[list["DocumentSection"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    clauses: Mapped[list["Clause"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    risks: Mapped[list["RiskFinding"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    summary: Mapped["Summary | None"] = relationship(
        back_populates="document", cascade="all, delete-orphan", uselist=False
    )


class DocumentSection(Base):
    __tablename__ = "document_sections"
    __table_args__ = (Index("ix_sections_doc_idx", "document_id", "idx"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String(512), default="")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, default=0)
    char_end: Mapped[int] = mapped_column(Integer, default=0)
    page: Mapped[int] = mapped_column(Integer, default=1)

    document: Mapped[Document] = relationship(back_populates="sections")


class Clause(Base):
    __tablename__ = "clauses"
    __table_args__ = (Index("ix_clauses_doc_cat", "document_id", "category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("document_sections.id"))
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, default=0)
    char_end: Mapped[int] = mapped_column(Integer, default=0)
    page: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str] = mapped_column(String(16), default="ai")
    review_status: Mapped[str] = mapped_column(
        Enum(*REVIEW_STATUSES, name="clause_review"), default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="clauses")


class RiskFinding(Base):
    __tablename__ = "risk_findings"
    __table_args__ = (Index("ix_risks_doc_sev", "document_id", "severity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    clause_id: Mapped[int | None] = mapped_column(ForeignKey("clauses.id"))
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Enum(*SEVERITIES, name="risk_severity"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="")
    suggestion: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    review_status: Mapped[str] = mapped_column(
        Enum(*REVIEW_STATUSES, name="risk_review"), default="pending"
    )
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="risks")


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), unique=True, nullable=False
    )
    executive: Mapped[str] = mapped_column(Text, default="")
    key_obligations: Mapped[list | None] = mapped_column(JSON)
    important_dates: Mapped[list | None] = mapped_column(JSON)
    payments: Mapped[list | None] = mapped_column(JSON)
    major_risks: Mapped[list | None] = mapped_column(JSON)
    termination: Mapped[str] = mapped_column(Text, default="")
    restrictions: Mapped[list | None] = mapped_column(JSON)
    compliance: Mapped[list | None] = mapped_column(JSON)
    health_score: Mapped[int] = mapped_column(Integer, default=0)
    health_verdict: Mapped[str] = mapped_column(String(255), default="")
    model: Mapped[str] = mapped_column(String(64), default="deterministic")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="summary")


class Comparison(Base):
    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_a_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    doc_b_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "ready", "failed", name="cmp_status"), default="pending"
    )
    summary: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    changes: Mapped[list["ComparisonChange"]] = relationship(
        back_populates="comparison", cascade="all, delete-orphan"
    )


class ComparisonChange(Base):
    __tablename__ = "comparison_changes"
    __table_args__ = (Index("ix_cmp_changes_cmp", "comparison_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comparison_id: Mapped[int] = mapped_column(ForeignKey("comparisons.id"), nullable=False)
    kind: Mapped[str] = mapped_column(
        Enum("added", "removed", "modified", name="change_kind"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), default="")
    clause_a_id: Mapped[int | None] = mapped_column(ForeignKey("clauses.id"))
    clause_b_id: Mapped[int | None] = mapped_column(ForeignKey("clauses.id"))
    text_a: Mapped[str] = mapped_column(Text, default="")
    text_b: Mapped[str] = mapped_column(Text, default="")
    similarity: Mapped[float] = mapped_column(Float, default=0.0)
    material: Mapped[bool] = mapped_column(Boolean, default=False)
    rationale: Mapped[str] = mapped_column(Text, default="")

    comparison: Mapped[Comparison] = relationship(back_populates="changes")


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(
        Enum("clause", "risk", "summary", "comparison", name="target_type"), nullable=False
    )
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(
        Enum("accept", "reject", "correct", "comment", "flag", name="review_action_kind"),
        nullable=False,
    )
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_created", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    entity: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), unique=True, nullable=True
    )
    comparison_id: Mapped[int | None] = mapped_column(ForeignKey("comparisons.id"))
    kind: Mapped[str] = mapped_column(
        Enum("document", "comparison", name="job_kind"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum("queued", "running", "done", "failed", name="job_status"),
        default="queued",
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
