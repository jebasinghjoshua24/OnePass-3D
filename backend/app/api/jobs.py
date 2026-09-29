import os
import uuid
import threading
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job
from app.schemas import JobStatusResponse, JobResultsResponse, CalibrationRequest
from app.storage import storage
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])

def trigger_job_pipeline(job_id: str):
    """Attempt to trigger via Celery; fallback to local background thread if Celery/Redis is unreachable."""
    try:
        from app.core.celery_app import celery_app
        # Celery send_task by string name to avoid hard circular dependencies
        celery_app.send_task("worker.pipeline.tasks.run_pipeline", args=[job_id])
        logger.info(f"Queued job {job_id} on Celery worker")
    except Exception as e:
        logger.warning(f"Could not dispatch via Celery ({e}). Running via worker thread fallback.")
        try:
            from worker.pipeline.tasks import run_pipeline_sync
            thread = threading.Thread(target=run_pipeline_sync, args=(job_id,), daemon=True)
            thread.start()
            logger.info(f"Started job {job_id} in background thread")
        except Exception as e2:
            logger.error(f"Failed to launch background worker: {e2}")

@router.post("", response_model=JobStatusResponse)
async def create_job(
    name: Optional[str] = Form("Drone 3D Reconstruction"),
    is_mock: bool = Form(False),
    video: Optional[UploadFile] = File(None),
    telemetry: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Create and queue a new 3D reconstruction job.
    Accepts video (MP4/MOV) and telemetry (CSV/JSON).
    If is_mock is true, synthetic drone data is generated.
    """
    job_id = str(uuid.uuid4())
    job_dir = storage.get_job_dir(job_id)

    video_filename = None
    telemetry_filename = None

    if video and video.filename:
        video_filename = f"input_video{os.path.splitext(video.filename)[1]}"
        content = await video.read()
        storage.save_file(job_id, video_filename, content)

    if telemetry and telemetry.filename:
        telemetry_filename = f"telemetry{os.path.splitext(telemetry.filename)[1]}"
        content = await telemetry.read()
        storage.save_file(job_id, telemetry_filename, content)

    # If no video uploaded, automatically toggle mock mode so user gets an immediate demo
    if not video_filename and not is_mock:
        is_mock = True

    new_job = Job(
        id=job_id,
        name=name,
        status="queued",
        progress=0.0,
        current_stage="Queued",
        message="Job queued for processing",
        is_mock=is_mock,
        video_filename=video_filename,
        telemetry_filename=telemetry_filename,
        logs=[f"[{job_id}] Job created. Mode: {'Mock Demo' if is_mock else 'Standard Video'}"]
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Launch Celery worker task
    trigger_job_pipeline(job_id)

    return new_job.to_dict()

@router.post("/mock", response_model=JobStatusResponse)
async def create_mock_job(
    name: Optional[str] = Form("SinglePass3D Synthetic Demo Survey"),
    db: Session = Depends(get_db)
):
    """Convenience endpoint to immediately trigger a sample mock demo run."""
    job_id = str(uuid.uuid4())
    new_job = Job(
        id=job_id,
        name=name,
        status="queued",
        progress=0.0,
        current_stage="Queued",
        message="Mock drone survey queued with sample photogrammetry data",
        is_mock=True,
        logs=[f"[{job_id}] Demo survey initiated using synthetic drone telemetry & geometry."]
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    trigger_job_pipeline(job_id)
    return new_job.to_dict()

@router.get("", response_model=List[JobStatusResponse])
def list_jobs(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """List recent reconstruction jobs."""
    jobs = db.query(Job).order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    return [j.to_dict() for j in jobs]

@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Retrieve current job status, pipeline progress, metrics, and logs."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()

@router.get("/{job_id}/results", response_model=JobResultsResponse)
def get_job_results(job_id: str, db: Session = Depends(get_db)):
    """Retrieve output artifacts and summary metrics."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.id,
        "status": job.status,
        "artifacts": job.artifacts or {},
        "metrics": {
            "total_frames": job.total_frames,
            "sharp_frames": job.sharp_frames,
            "dynamic_objects_detected": job.dynamic_objects_detected,
            "dense_points_count": job.dense_points_count,
            "mesh_faces_count": job.mesh_faces_count,
            "mean_confidence": job.mean_confidence,
            "utm_zone": job.utm_zone
        }
    }

@router.get("/{job_id}/download/{artifact_name}")
def download_artifact(job_id: str, artifact_name: str, db: Session = Depends(get_db)):
    """Serve or download a reconstruction artifact (GLB, PLY, GeoTIFF, LAS, JSON, PNG)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    file_path = storage.get_file_path(job_id, artifact_name)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_name} not found")

    # Determine media type
    ext = os.path.splitext(artifact_name)[1].lower()
    media_types = {
        ".glb": "model/gltf-binary",
        ".gltf": "model/gltf+json",
        ".ply": "application/x-ply",
        ".obj": "text/plain",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".las": "application/octet-stream",
        ".laz": "application/octet-stream",
        ".json": "application/json",
        ".csv": "text/csv",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=artifact_name
    )

@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Cancel an active or queued job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in ["completed", "failed", "cancelled"]:
        return {"message": f"Job already in final state: {job.status}"}

    job.status = "cancelled"
    job.message = "Job was cancelled by user"
    db.commit()
    return {"message": "Job cancellation requested", "job_id": job_id}

@router.post("/calibrate")
def calibrate_scale(payload: CalibrationRequest, db: Session = Depends(get_db)):
    """Optional scale calibration: adjusts metric scale given two 3D coordinates and ground truth distance."""
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    import math
    p1 = payload.point_a
    p2 = payload.point_b
    measured = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
    if measured <= 0:
        raise HTTPException(status_code=400, detail="Points are identical")

    scale_factor = payload.real_distance_meters / measured
    return {
        "job_id": job.id,
        "measured_distance": round(measured, 3),
        "real_distance": round(payload.real_distance_meters, 3),
        "scale_factor": round(scale_factor, 5),
        "message": f"Calibration scale factor calculated: {scale_factor:.4f}x"
    }
