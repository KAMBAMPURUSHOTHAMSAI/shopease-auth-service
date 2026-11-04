from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user_model import User
from app.schemas.auth_schema import ChangePasswordRequest, LoginRequest, RegisterRequest


def register_user(db: Session, payload: RegisterRequest) -> User:
    existing_user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    user = User(
        full_name=payload.full_name,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role="customer",
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    return user


def authenticate_user(db: Session, payload: LoginRequest) -> User:
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is inactive.")
    return user


def update_password(db: Session, user: User, payload: ChangePasswordRequest) -> User:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
