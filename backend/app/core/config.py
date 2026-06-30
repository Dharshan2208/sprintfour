from typing import List, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # Ignore extra environment variables not defined in the model
    )

    APP_NAME: str = "AnonymizationService"
    ENVIRONMENT: Literal["development", "testing", "staging", "production"] = (
        "development"
    )
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["*"]  # Default to allow all for development

    # Database settings (placeholders for future phases)
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/dbname"

    # Redis settings (placeholders for future phases)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Example of a sensitive setting (will be loaded from env/secrets)
    SECRET_KEY: str = "your-super-secret-key"  # IMPORTANT: Change in production!

    # ── Gemini / AI Provider ─────────────────────────────────────
    GEMINI_API_KEY: str = ""  # Set in .env or environment
    GEMINI_MODEL: str = "gemini-3.5-flash"  # Default model
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_TIMEOUT_SECONDS: int = 30
    GEMINI_MAX_TOKENS: int = 8192


# Create a singleton instance of settings to be used throughout the application
settings = Settings()
