from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ROLE_ADMIN, ROLE_ANALYST, User

bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from app.security import decode_token

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return checker


require_analyst = require_roles(ROLE_ADMIN, ROLE_ANALYST)
require_admin = require_roles(ROLE_ADMIN)


def get_doc_or_404(db: Session, doc_id: int, user: User):
    from app.models import Document

    doc = db.get(Document, doc_id)
    if not doc or (doc.owner_id != user.id and user.role != ROLE_ADMIN):
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def client_ip(request: Request | None) -> str:
    if request is None:
        return ""
    return request.client.host if request.client else ""
