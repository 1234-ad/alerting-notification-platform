"""
Configuration settings for the Alerting & Notification Platform.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str = "sqlite:///./alerts.db"
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Reminder Configuration
    REMINDER_INTERVAL_HOURS: int = 2
    REMINDER_CHECK_INTERVAL_SECONDS: int = 300  # Check every 5 minutes
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()