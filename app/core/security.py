from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.connection import get_db
from app.models.user_model import User


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return password_context.verify(plain_password, password_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(user: User) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": now,
        "exp": now + expires_delta,
        "iss": settings.jwt_issuer,
    }
    token = jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        options={"require": ["sub", "role", "iat", "exp", "iss"]},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Reusable dependency for any endpoint that requires a valid bearer token."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        claims = decode_access_token(credentials.credentials)
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise unauthorized

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is inactive.")
    return user
