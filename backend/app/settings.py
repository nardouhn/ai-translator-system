from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://admin:password123@localhost:5432/ai_translator"
    redis_url: str = "redis://localhost:6379/0"
    
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_endpoint_url: str | None = None
    r2_bucket_name: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
print("DATABASE_URL =", settings.database_url)
