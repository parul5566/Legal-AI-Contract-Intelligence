import os
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.audit import audit
from app.config import settings
from app.deps import client_ip, get_current_user, get_db, get_doc_or_404
from app.models import AnalysisJob, Document, User
from app.schemas import (
    AnalyzeOut,
    DocumentList,
    DocumentOut,
    SectionOut,
    StatusOut,
)
from app.worker import claim_next_job  # noqa: F401  (keeps import graph simple)

router = APIRouter(prefix="/api/documents", tags=["documents"])

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ALLOWED = {"application/pdf": "pdf", DOCX_MIME: "docx", "text/plain": "txt"}
EXT_MIME = {"pdf": "application/pdf", "docx": DOCX_MIME, "txt": "text/plain"}


@router.get("", response_model=DocumentList)
def list_documents(
    q: str = "",
    status_filter: str = "",
    page: int = 1,
    page_size: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Document).order_by(Document.created_at.desc())
    if user.role != "admin":
        query = query.filter(Document.owner_id == user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Document.original_name.ilike(like), Document.title.ilike(like))
        )
    if status_filter:
        query = query.filter(Document.status == status_filter)
    total = query.count()
    items = (
        query.offset((page - 1) * page_size).limit(min(page_size, 200)).all()
    )
    return DocumentList(items=items, total=total)


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot upload documents")

    ext = None
    if file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else None
    mime = file.content_type or ""
    if mime not in ALLOWED and ext not in EXT_MIME:
        raise HTTPException(status_code=415, detail="Only PDF, DOCX and TXT files are allowed")

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds 10MB limit")
    if len(content.strip()) == 0:
        raise HTTPException(status_code=422, detail="File is empty")

    ext = ext or ALLOWED.get(mime, "txt")
    mime = EXT_MIME.get(ext, mime or "text/plain")
    if not re.match(r"^[a-zA-Z0-9._-]+$", file.filename or "doc"):
        raise HTTPException(status_code=422, detail="Invalid filename")

    stored = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(os.path.join(settings.upload_dir, stored), "wb") as fh:
        fh.write(content)
    try:
        os.chmod(os.path.join(settings.upload_dir, stored), 0o600)
    except OSError:
        pass

    doc = Document(
        owner_id=user.id,
        filename=stored,
        original_name=file.filename or stored,
        mime=mime,
        size_bytes=len(content),
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    job = AnalysisJob(document_id=doc.id, kind="document", status="queued")
    db.add(job)
    audit(db, "upload", "document", doc.id, doc.original_name, user.id, client_ip(request))
    db.commit()

    return doc


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_doc_or_404(db, doc_id, user)


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot delete documents")
    doc = get_doc_or_404(db, doc_id, user)
    for job in db.query(AnalysisJob).filter(AnalysisJob.document_id == doc.id).all():
        db.delete(job)
    db.delete(doc)
    try:
        os.remove(os.path.join(settings.upload_dir, doc.filename))
    except OSError:
        pass
    audit(db, "delete", "document", doc.id, doc.original_name, user.id, client_ip(request))
    db.commit()


@router.get("/{doc_id}/status", response_model=StatusOut)
def document_status(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = get_doc_or_404(db, doc_id, user)
    return StatusOut(status=doc.status, error=doc.error)


@router.get("/{doc_id}/sections", response_model=list[SectionOut])
def document_sections(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = get_doc_or_404(db, doc_id, user)
    return sorted(doc.sections, key=lambda s: s.idx)


@router.get("/{doc_id}/file")
def document_file(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = get_doc_or_404(db, doc_id, user)
    path = os.path.join(settings.upload_dir, doc.filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Stored file missing")
    from fastapi.responses import FileResponse

    return FileResponse(path, media_type=doc.mime, filename=doc.original_name)


@router.post("/{doc_id}/analyze", response_model=AnalyzeOut)
def reanalyze(
    doc_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot run analysis")
    doc = get_doc_or_404(db, doc_id, user)
    existing = (
        db.query(AnalysisJob)
        .filter(AnalysisJob.document_id == doc.id, AnalysisJob.status.in_(("queued", "running")))
        .first()
    )
    if existing:
        return AnalyzeOut(job_id=existing.id, queued=True)
    doc.status = "pending"
    doc.error = None
    job = AnalysisJob(document_id=doc.id, kind="document", status="queued")
    db.add(job)
    audit(db, "analyze", "document", doc.id, "re-analysis requested", user.id, client_ip(request))
    db.commit()
    db.refresh(job)
    return AnalyzeOut(job_id=job.id, queued=True)
