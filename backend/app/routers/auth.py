from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.audit import audit
from app.deps import client_ip, get_current_user, get_db
from app.models import ROLE_ADMIN, ROLE_ANALYST, User
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    role = body.role
    if role == ROLE_ADMIN:
        # only an existing admin can mint admins; default self-signups to analyst
        role = ROLE_ANALYST
    user = User(
        email=body.email.lower(),
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit(db, "register", "user", user.id, f"role={user.role}", user.id, client_ip(request))
    db.commit()
    token = create_access_token(user.id, user.role)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        audit(db, "login_failed", "user", None, body.email[:120], None, client_ip(request))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    audit(db, "login", "user", user.id, f"role={user.role}", user.id, client_ip(request))
    db.commit()
    token = create_access_token(user.id, user.role)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
