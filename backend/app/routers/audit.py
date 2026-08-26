from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.models import AuditLog, User
from app.schemas import AuditList, AuditOut

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=AuditList)
def list_audit(
    page: int = 1,
    page_size: int = 100,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(min(page_size, 500)).all()
    return AuditList(items=items, total=total)
