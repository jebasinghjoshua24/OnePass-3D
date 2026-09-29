import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "OnePass-3D - Drone 3D Reconstruction System"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://sih_user:sih_password@postgres:5432/sih_db"
    )
    # Fallback to SQLite for standalone local testing if PostgreSQL is unavailable
    SQLITE_FALLBACK_URL: str = "sqlite:///./storage/sih_local.db"
    
    # Redis & Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
    
    # Storage & MinIO
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage")
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "sih-artifacts")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    USE_MINIO: bool = os.getenv("USE_MINIO", "false").lower() == "true"

    # Processing & Hardware
    DEVICE: str = os.getenv("DEVICE", "cpu")  # 'cuda' or 'cpu'
    TARGET_HEIGHT: int = int(os.getenv("TARGET_HEIGHT", "720"))  # downscale to 720p on CPU
    TARGET_WIDTH: int = int(os.getenv("TARGET_WIDTH", "1280"))
    MAX_FPS: float = float(os.getenv("MAX_FPS", "3.0"))  # Extract 2-5 FPS as per PRD
    SHARPNESS_THRESHOLD: float = float(os.getenv("SHARPNESS_THRESHOLD", "85.0"))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.4"))

    class Config:
        case_sensitive = True

settings = Settings()
