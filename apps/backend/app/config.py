"""Application configuration from environment variables."""

import os
from pathlib import Path
from typing import Literal

# Load .env file if it exists
from dotenv import load_dotenv

env_file = Path(__file__).parent.parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)


class Settings:
    # Server settings
    HOST: str = os.getenv('HOST', '127.0.0.1')
    PORT: int = int(os.getenv('PORT', '8000'))
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')
    ENVIRONMENT: Literal['development', 'staging', 'production'] = os.getenv('ENVIRONMENT', 'development')  # type: ignore
    
    # Database settings
    DB_PATH: str = os.getenv('DB_PATH', '')  # If empty, uses default in db.py
    
    # CORS settings
    CORS_ORIGINS: list[str] = [
        'http://127.0.0.1:5173',
        'http://localhost:5173',
        'http://127.0.0.1:3000',
        'app://.',
        'file://',
    ]
    if os.getenv('CORS_ORIGINS'):
        CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')
    
    # Integrations
    WEBHOOK_SIGNING_KEY: str = os.getenv('WEBHOOK_SIGNING_KEY', 'dev-key-change-in-prod')
    
    # Feature flags
    ENABLE_ANKI_IMPORT: bool = os.getenv('ENABLE_ANKI_IMPORT', 'true').lower() in ('true', '1', 'yes')
    ENABLE_WEBHOOKS: bool = os.getenv('ENABLE_WEBHOOKS', 'true').lower() in ('true', '1', 'yes')
    ENABLE_WEBHOOK_HTTP_DELIVERY: bool = os.getenv('ENABLE_WEBHOOK_HTTP_DELIVERY', 'false').lower() in ('true', '1', 'yes')
    ENABLE_OAUTH: bool = os.getenv('ENABLE_OAUTH', 'false').lower() in ('true', '1', 'yes')
    
    @classmethod
    def is_production(cls) -> bool:
        return cls.ENVIRONMENT == 'production'
    
    @classmethod
    def is_development(cls) -> bool:
        return cls.ENVIRONMENT == 'development'


settings = Settings()
