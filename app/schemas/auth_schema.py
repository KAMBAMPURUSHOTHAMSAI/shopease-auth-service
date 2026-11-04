from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator, model_validator


NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
PasswordStr = Annotated[str, StringConstraints(min_length=8, max_length=72)]


def validate_password_strength(value: str) -> str:
    """Require a strong password and keep it within bcrypt's 72-byte limit."""
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes.")
    checks = {
        "an uppercase letter": any(char.isupper() for char in value),
        "a lowercase letter": any(char.islower() for char in value),
        "a number": any(char.isdigit() for char in value),
        "a special character": any(not char.isalnum() for char in value),
    }
    missing = [label for label, passed in checks.items() if not passed]
    if missing:
        raise ValueError("Password must contain " + ", ".join(missing) + ".")
    return value


class RegisterRequest(BaseModel):
    full_name: NameStr
    email: EmailStr
    password: PasswordStr
    confirm_password: PasswordStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password", "confirm_password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def passwords_must_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Password and confirm_password must match.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=1, max_length=72)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class ChangePasswordRequest(BaseModel):
    current_password: Annotated[str, StringConstraints(min_length=1, max_length=72)]
    new_password: PasswordStr
    confirm_new_password: PasswordStr

    @field_validator("new_password", "confirm_new_password")
    @classmethod
    def check_new_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def validate_new_passwords(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("new_password and confirm_new_password must match.")
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password.")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse


class LoginResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class VerifyTokenResponse(BaseModel):
    valid: bool
    message: str
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
    user: UserResponse
