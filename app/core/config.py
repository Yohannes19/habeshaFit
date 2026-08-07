"""
Core configuration and security settings.
Centralized environment management with validation.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
import secrets


class Settings(BaseSettings):
    """Application settings with validation."""
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")
    
    # App Info
    APP_NAME: str = "HabeshaFit"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database (PostgreSQL)
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/habeshafit"
    
    # Security & JWT
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Password Hashing
    PASSWORD_HASH_ROUNDS: int = 12  # Bcrypt rounds
    
    # File Uploads
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_IMAGE_TYPES: set = {"image/jpeg", "image/png", "image/webp"}
    UPLOAD_DIR: str = "./app/static/uploads"
    
    # Rate Limiting (requests per minute)
    RATE_LIMIT_PER_MINUTE: int = 60
    
    @property
    def is_dev(self) -> bool:
        return self.DEBUG


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance for performance."""
    return Settings()


settings = get_settings()
