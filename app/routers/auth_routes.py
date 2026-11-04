from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_user
from app.database.connection import get_db
from app.models.user_model import User
from app.schemas.auth_schema import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
    VerifyTokenResponse,
)
from app.services.auth_service import authenticate_user, register_user, update_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = register_user(db, payload)
    return RegisterResponse(message="User registered successfully.", user=UserResponse.model_validate(user))


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload)
    access_token, expires_in = create_access_token(user)
    return LoginResponse(
        message="Login successful.",
        access_token=access_token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/verify-token", response_model=VerifyTokenResponse)
def verify_token(current_user: User = Depends(get_current_user)):
    return VerifyTokenResponse(
        valid=True,
        message="Access token is valid.",
        user=UserResponse.model_validate(current_user),
    )


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated_user = update_password(db, current_user, payload)
    return MessageResponse(
        message="Password changed successfully.",
        user=UserResponse.model_validate(updated_user),
    )
