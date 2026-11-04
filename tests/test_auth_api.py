import os
from datetime import datetime, timedelta, timezone

# Provide test-only values before application settings are imported.
os.environ.setdefault("DB_PASSWORD", "TestOnlyDatabasePassword123!")
os.environ.setdefault("JWT_SECRET_KEY", "TestOnlyJWTSecretKey-AtLeast-32-Characters-Long-123")
os.environ.setdefault("JWT_ISSUER", "shopease-auth-service")

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.database.connection import Base, get_db
from app.main import app
from app.models.user_model import User

TEST_ENGINE = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=TEST_ENGINE)


def register_user(client: TestClient, email: str = "sai@example.com"):
    return client.post(
        "/api/auth/register",
        json={
            "full_name": "Sai User",
            "email": email,
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        },
    )


def login_user(client: TestClient, password: str = "StrongPass123!"):
    return client.post("/api/auth/login", json={"email": "sai@example.com", "password": password})


def test_register_success_and_never_return_hash(client):
    response = register_user(client)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "sai@example.com"
    assert body["user"]["role"] == "customer"
    assert "password" not in body and "password_hash" not in body["user"]

    with TestingSessionLocal() as db:
        saved_user = db.scalar(select(User).where(User.email == "sai@example.com"))
        assert saved_user is not None
        assert saved_user.password_hash != "StrongPass123!"


def test_duplicate_email_returns_409(client):
    assert register_user(client).status_code == 201
    assert register_user(client).status_code == 409


def test_invalid_email_returns_422(client):
    response = client.post(
        "/api/auth/register",
        json={"full_name": "Sai User", "email": "bad-email", "password": "StrongPass123!", "confirm_password": "StrongPass123!"},
    )
    assert response.status_code == 422


def test_password_mismatch_returns_422(client):
    response = client.post(
        "/api/auth/register",
        json={"full_name": "Sai User", "email": "sai@example.com", "password": "StrongPass123!", "confirm_password": "DifferentPass123!"},
    )
    assert response.status_code == 422


def test_login_valid_and_invalid_credentials(client):
    assert register_user(client).status_code == 201
    assert login_user(client).status_code == 200
    assert login_user(client, "WrongPassword123!").status_code == 401


def test_current_user_and_verify_token(client):
    assert register_user(client).status_code == 201
    login = login_user(client)
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    verified = client.post("/api/auth/verify-token", headers=headers)
    assert verified.status_code == 200
    assert verified.json()["valid"] is True


def test_missing_invalid_and_expired_tokens_return_401(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.value"}).status_code == 401

    settings = get_settings()
    expired_token = jwt.encode(
        {
            "sub": "1",
            "role": "customer",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iss": settings.jwt_issuer,
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


def test_change_password_and_login_with_new_password(client):
    assert register_user(client).status_code == 201
    token = login_user(client).json()["access_token"]
    response = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "StrongPass123!",
            "new_password": "NewStrongPass456!",
            "confirm_new_password": "NewStrongPass456!",
        },
    )
    assert response.status_code == 200
    assert "password_hash" not in response.json()["user"]
    assert login_user(client, "StrongPass123!").status_code == 401
    assert login_user(client, "NewStrongPass456!").status_code == 200


def test_wrong_current_password_returns_400(client):
    assert register_user(client).status_code == 201
    token = login_user(client).json()["access_token"]
    response = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "WrongPassword123!",
            "new_password": "NewStrongPass456!",
            "confirm_new_password": "NewStrongPass456!",
        },
    )
    assert response.status_code == 400


def test_inactive_user_cannot_login_or_use_protected_routes(client):
    assert register_user(client).status_code == 201
    with TestingSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "sai@example.com"))
        user.is_active = False
        db.commit()

    assert login_user(client).status_code == 403
