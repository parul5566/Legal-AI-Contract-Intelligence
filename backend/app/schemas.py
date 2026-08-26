from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Allow .test / .example domains used by seed data
import email_validator

email_validator.TEST_ENVIRONMENT = True

Role = Literal["admin", "analyst", "viewer"]
Severity = Literal["low", "medium", "high", "critical"]
ReviewStatus = Literal["pending", "accepted", "rejected", "corrected"]
DocStatus = Literal["pending", "parsing", "analyzing", "ready", "failed"]


# ---------- auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: Role = "viewer"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: Role
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- documents ----------
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    original_name: str
    filename: str
    mime: str
    size_bytes: int
    status: DocStatus
    doc_type: str | None
    title: str | None
    parties: list | None
    effective_date: str | None
    expiry_date: str | None
    jurisdiction: str | None
    page_count: int
    char_count: int
    error: str | None
    created_at: datetime
    analyzed_at: datetime | None


class DocumentList(BaseModel):
    items: list[DocumentOut]
    total: int


class SectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    idx: int
    heading: str
    body: str
    page: int


class ClauseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    section_id: int | None
    category: str
    title: str
    text: str
    char_start: int
    char_end: int
    page: int
    confidence: float
    source: str
    review_status: ReviewStatus
    created_at: datetime


class RiskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    clause_id: int | None
    category: str
    severity: Severity
    title: str
    explanation: str
    suggestion: str
    evidence: str
    confidence: float
    review_status: ReviewStatus
    review_note: str | None
    created_at: datetime


class SummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    executive: str
    key_obligations: list | None
    important_dates: list | None
    payments: list | None
    major_risks: list | None
    termination: str
    restrictions: list | None
    compliance: list | None
    health_score: int
    health_verdict: str
    model: str
    created_at: datetime


class AnalyzeOut(BaseModel):
    job_id: int
    queued: bool


class StatusOut(BaseModel):
    status: DocStatus
    error: str | None = None


# ---------- review ----------
class ReviewIn(BaseModel):
    action: Literal["accept", "reject", "correct", "comment", "flag"]
    note: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, max_length=64)  # correction target for clauses


class ReviewActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    actor_id: int
    target_type: str
    target_id: int
    action: str
    detail: str | None
    created_at: datetime


# ---------- comparisons ----------
class ComparisonIn(BaseModel):
    doc_a_id: int
    doc_b_id: int


class ChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: Literal["added", "removed", "modified"]
    category: str
    clause_a_id: int | None
    clause_b_id: int | None
    text_a: str
    text_b: str
    similarity: float
    material: bool
    rationale: str


class ComparisonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_a_id: int
    doc_b_id: int
    created_by: int
    status: Literal["pending", "processing", "ready", "failed"]
    summary: str | None
    error: str | None
    created_at: datetime
    changes: list[ChangeOut] = []


class ComparisonList(BaseModel):
    items: list[ComparisonOut]
    total: int


# ---------- stats / audit ----------
class DashboardStats(BaseModel):
    total_documents: int
    analyzed_documents: int
    ready_documents: int
    failed_documents: int
    high_risk_documents: int
    total_clauses: int
    total_risks: int
    total_comparisons: int
    severity_histogram: dict[str, int]
    clause_category_counts: dict[str, int]
    recent_documents: list[DocumentOut]
    avg_health_score: float | None = None
    documents_health: list[dict[str, Any]] = []
    risk_category_counts: dict[str, int] = {}
    pending_reviews: int = 0
    active_users: int = 0


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    event: str
    entity: str
    entity_id: int | None
    detail: str | None
    ip: str
    created_at: datetime


class AuditList(BaseModel):
    items: list[AuditOut]
    total: int


class Msg(BaseModel):
    detail: str
