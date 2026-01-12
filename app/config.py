from pydantic_settings import BaseSettings
from typing import Optional
import sys

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:////data/app.db"
    LOG_LEVEL: str = "INFO"
    WEBHOOK_SECRET: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Validate that WEBHOOK_SECRET is set
if not settings.WEBHOOK_SECRET:
    print("ERROR: WEBHOOK_SECRET environment variable is not set", file=sys.stderr)
    sys.exit(1)


