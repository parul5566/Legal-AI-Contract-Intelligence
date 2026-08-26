from sqlalchemy.orm import Session

from app.models import AuditLog


def audit(
    db: Session,
    event: str,
    entity: str = "",
    entity_id: int | None = None,
    detail: str | None = None,
    user_id: int | None = None,
    ip: str = "",
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            event=event,
            entity=entity,
            entity_id=entity_id,
            detail=detail[:2000] if detail else None,
            ip=ip[:64],
        )
    )
