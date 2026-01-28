from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str  # service role key for admin ops
    SUPABASE_JWT_SECRET: str
    UPSTASH_REDIS_URL: str
    UPSTASH_REDIS_TOKEN: str
    CORS_ORIGINS: str = "http://localhost:3000"
    MAX_FILE_SIZE_MB: int = 500
    DATA_DIR: str = "/tmp/geolyze_data"

    class Config:
        env_file = ".env"


settings = Settings()
