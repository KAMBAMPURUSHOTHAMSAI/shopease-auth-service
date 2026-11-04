"""Generate a signed, already-expired JWT for negative API testing only."""
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

settings = get_settings()
now = datetime.now(timezone.utc)
expired_payload = {
    "sub": "1",
    "role": "customer",
    "iat": now - timedelta(minutes=10),
    "exp": now - timedelta(minutes=5),
    "iss": settings.jwt_issuer,
}
token = jwt.encode(
    expired_payload,
    settings.jwt_secret_key.get_secret_value(),
    algorithm=settings.jwt_algorithm,
)
print(token)
