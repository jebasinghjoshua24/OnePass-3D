import os
import sys

# Ensure backend and worker packages are on python path
sys.path.insert(0, os.path.abspath("."))

try:
    from app.core.celery_app import celery_app
except ImportError:
    from backend.app.core.celery_app import celery_app
import worker.pipeline.tasks

if __name__ == "__main__":
    celery_app.start()
