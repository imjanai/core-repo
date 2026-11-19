"""apps/api/core/config.py — instellingen via omgevingsvariabelen."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = (
        "postgresql+asyncpg://elektro:elektro@localhost:5432/elektro"
    )

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # S3-compatibele opslag (MinIO of AWS)
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "elektro-uploads"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_region: str = "eu-west-1"

    # vLLM (Qwen-VL)
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "elektro-vl"

    # Observability
    sentry_dsn: str = ""

    # Pipeline / worker
    pipeline_soft_time_limit: int = 1500   # seconden: waarschuwing
    pipeline_hard_time_limit: int = 1800   # seconden: harde stop
    pipeline_rate_limit: str = "30"        # taken per minuut per type
    stale_check_seconds: int = 300         # sweeper-interval
    stale_after_minutes: int = 15          # na zo lang is een run "gestrand"
    max_run_resumes: int = 3               # hoevaak een gestrande run opnieuw mag

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Uploads
    max_upload_bytes: int = 100 * 1024 * 1024  # 100 MB


settings = Settings()
