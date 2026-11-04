from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ShopEase Authentication Service"
    app_version: str = "1.0.0"
    app_description: str = "JWT-based authentication microservice for ShopEase."
    app_port: int = 8002

    db_host: str = "127.0.0.1"
    db_port: int = 3308
    db_name: str = "shopease_auth_db"
    db_user: str = "shopease_auth_user"
    db_password: SecretStr

    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = 30
    jwt_issuer: str = "shopease-auth-service"

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters.")
        return value

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_token_expiry(cls, value: int) -> int:
        if value < 1 or value > 1440:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 1440.")
        return value

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )


@lru_cache

def get_settings() -> Settings:
    return Settings()
