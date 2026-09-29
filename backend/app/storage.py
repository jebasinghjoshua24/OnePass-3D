import os
import shutil
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self):
        self.base_dir = os.path.abspath(settings.STORAGE_DIR)
        os.makedirs(self.base_dir, exist_ok=True)
        self.minio_client = None

        if settings.USE_MINIO:
            try:
                from minio import Minio
                self.minio_client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE
                )
                if not self.minio_client.bucket_exists(settings.MINIO_BUCKET):
                    self.minio_client.make_bucket(settings.MINIO_BUCKET)
                logger.info(f"Connected to MinIO at {settings.MINIO_ENDPOINT}")
            except Exception as e:
                logger.warning(f"MinIO connection failed: {e}. Using local storage at {self.base_dir}")
                self.minio_client = None

    def get_job_dir(self, job_id: str) -> str:
        job_dir = os.path.join(self.base_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        return job_dir

    def save_file(self, job_id: str, filename: str, content: bytes) -> str:
        job_dir = self.get_job_dir(job_id)
        file_path = os.path.join(job_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content)

        if self.minio_client:
            try:
                object_name = f"{job_id}/{filename}"
                self.minio_client.fput_object(
                    settings.MINIO_BUCKET,
                    object_name,
                    file_path
                )
            except Exception as e:
                logger.warning(f"Could not push {filename} to MinIO: {e}")

        return file_path

    def get_file_path(self, job_id: str, filename: str) -> Optional[str]:
        file_path = os.path.join(self.base_dir, job_id, filename)
        if os.path.exists(file_path):
            return file_path
        return None

    def get_artifact_url(self, job_id: str, artifact_name: str) -> str:
        # FastAPI serves artifacts from /api/jobs/{id}/download/{artifact_name}
        return f"/api/jobs/{job_id}/download/{artifact_name}"

storage = StorageManager()
