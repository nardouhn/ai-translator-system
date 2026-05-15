import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5432/ai_translator")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    r2_access_key_id: str | None = os.getenv("R2_ACCESS_KEY_ID")
    r2_secret_access_key: str | None = os.getenv("R2_SECRET_ACCESS_KEY")
    r2_endpoint_url: str | None = os.getenv("R2_ENDPOINT_URL")
    r2_bucket_name: str | None = os.getenv("R2_BUCKET_NAME")
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
print("DATABASE_URL =", settings.database_url)
