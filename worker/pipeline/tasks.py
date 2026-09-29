import os
import time
import logging
from datetime import datetime
from typing import Dict, Any

try:
    from app.database import SessionLocal
    from app.models import Job
    from app.config import settings
    from app.storage import storage
    from app.core.celery_app import celery_app
except ImportError:
    from backend.app.database import SessionLocal
    from backend.app.models import Job
    from backend.app.config import settings
    from backend.app.storage import storage
    from backend.app.core.celery_app import celery_app

from worker.pipeline.extract_frames import extract_frames
from worker.pipeline.select_sharp_frames import select_sharp_frames
from worker.pipeline.preprocess_frames import preprocess_frames
from worker.pipeline.mask_dynamic_objects import mask_dynamic_objects
from worker.pipeline.estimate_poses import estimate_poses
from worker.pipeline.estimate_depth import estimate_depth
from worker.pipeline.fuse_depth import fuse_depth
from worker.pipeline.generate_mesh import generate_mesh
from worker.pipeline.georeference import georeference
from worker.pipeline.export_outputs import export_outputs
from worker.pipeline.mock_pipeline import generate_mock_drone_scene

logger = logging.getLogger(__name__)

def update_job_status(
    job_id: str,
    status: str,
    progress: float,
    current_stage: str,
    message: str,
    metrics: Dict[str, Any] = None,
    artifacts: Dict[str, str] = None,
    log_line: str = None
):
    """Updates the job record in the database with status, metrics, and progress."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = status
        job.progress = progress
        job.current_stage = current_stage
        job.message = message
        job.updated_at = datetime.utcnow()

        if log_line:
            logs = list(job.logs or [])
            ts_str = datetime.utcnow().strftime("%H:%M:%S")
            logs.append(f"[{ts_str}] {log_line}")
            job.logs = logs

        if metrics:
            if "total_frames" in metrics:
                job.total_frames = metrics["total_frames"]
            if "sharp_frames" in metrics:
                job.sharp_frames = metrics["sharp_frames"]
            if "dynamic_objects_detected" in metrics:
                job.dynamic_objects_detected = metrics["dynamic_objects_detected"]
            if "sparse_points_count" in metrics:
                job.sparse_points_count = metrics["sparse_points_count"]
            if "dense_points_count" in metrics:
                job.dense_points_count = metrics["dense_points_count"]
            if "mesh_faces_count" in metrics:
                job.mesh_faces_count = metrics["mesh_faces_count"]
            if "mean_confidence" in metrics:
                job.mean_confidence = metrics["mean_confidence"]
            if "utm_zone" in metrics:
                job.utm_zone = metrics["utm_zone"]

        if artifacts:
            job.artifacts = artifacts

        db.commit()
    except Exception as e:
        logger.error(f"Failed to update job status in DB: {e}")
        db.rollback()
    finally:
        db.close()

def run_pipeline_sync(job_id: str):
    """Executes the full 3D reconstruction pipeline for a job."""
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found in database.")
        db.close()
        return

    is_mock = job.is_mock
    video_filename = job.video_filename
    telemetry_filename = job.telemetry_filename
    db.close()

    output_dir = storage.get_job_dir(job_id)
    device = settings.DEVICE
    target_width = settings.TARGET_WIDTH
    target_height = settings.TARGET_HEIGHT

    try:
        # Check if job was cancelled
        def is_cancelled() -> bool:
            check_db = SessionLocal()
            j = check_db.query(Job).filter(Job.id == job_id).first()
            cancelled = (j.status == "cancelled") if j else False
            check_db.close()
            return cancelled

        if is_cancelled():
            return

        # ----------------------------------------------------
        # MOCK MODE BRANCH
        # ----------------------------------------------------
        if is_mock or not video_filename:
            update_job_status(job_id, "extracting", 10.0, "Frame Extraction", "Extracting drone survey frames (Mock Mode)...", log_line="Sampling video at 3 FPS. Applying 720p downscale for CPU.")
            time.sleep(1.0)

            if is_cancelled(): return
            update_job_status(job_id, "sharpness_filtering", 22.0, "Quality Selection", "Filtering blurry frames using Laplacian variance...", log_line="Laplacian variance computed. Retained 100% of high-sharpness frames.")
            time.sleep(1.0)

            if is_cancelled(): return
            update_job_status(job_id, "preprocessing", 35.0, "Frame Preprocessing", "Normalizing exposure (CLAHE) & suppressing sensor noise...", log_line="Exposure balanced, bilateral denoising complete.")
            time.sleep(1.0)

            if is_cancelled(): return
            update_job_status(job_id, "masking", 48.0, "Dynamic Object Masking", "Detecting and masking moving vehicles and pedestrians...", log_line="Detected 1 moving vehicle on access road. Generated binary staticness masks.")
            time.sleep(1.0)

            if is_cancelled(): return
            update_job_status(job_id, "pose_estimation", 60.0, "Camera Pose Estimation", "Estimating camera trajectory and visual feature matching...", log_line="Calculated 20 camera poses. Fused GPS soft constraints (RMSE < 2.5m).")
            time.sleep(1.0)

            if is_cancelled(): return
            update_job_status(job_id, "depth_estimation", 72.0, "Dense Depth Estimation", "Computing hybrid MVS disparity and AI metric depth...", log_line="Hybrid MVS + Monocular AI metric depth generated.")
            time.sleep(1.0)

            if is_cancelled(): return
            update_job_status(job_id, "depth_fusion", 82.0, "Confidence-Aware Fusion", "Fusing depth into 3D point cloud with confidence heatmap...", log_line="Backprojected 3D points. Voxel downsampling applied (0.2m grid).")

            mock_res = generate_mock_drone_scene(output_dir)

            if is_cancelled(): return
            update_job_status(job_id, "meshing", 90.0, "3D Mesh Generation", "Reconstructing surface mesh and baking textures...", log_line=f"Mesh complete: {mock_res['mesh_faces']} triangles. Exported to GLB and OBJ.")
            time.sleep(1.0)

            if is_cancelled(): return
            update_job_status(job_id, "georeference", 96.0, "Georeferencing", "Aligning model to UTM Zone 43N (WGS84)...", log_line="Sim3 Helmert transformation complete. Real-world RMSE: 1.42m.")
            time.sleep(0.5)

            # Complete
            metrics = {
                "total_frames": mock_res["total_frames"],
                "sharp_frames": mock_res["sharp_frames"],
                "dynamic_objects_detected": mock_res["dynamic_objects"],
                "sparse_points_count": 850,
                "dense_points_count": mock_res["points_count"],
                "mesh_faces_count": mock_res["mesh_faces"],
                "mean_confidence": mock_res["mean_confidence"],
                "utm_zone": "WGS 84 / UTM Zone 43N"
            }
            update_job_status(
                job_id, "completed", 100.0, "Completed",
                "Reconstruction successfully completed. Model ready for 3D visualization and measurement.",
                metrics=metrics,
                artifacts=mock_res["artifacts"],
                log_line="Survey complete. Model, point cloud, GeoTIFF DSM, and measurement report ready."
            )
            return

        # ----------------------------------------------------
        # REAL PIPELINE BRANCH
        # ----------------------------------------------------
        video_path = os.path.join(output_dir, video_filename)

        # Parse telemetry if available
        telemetry_points = []
        if telemetry_filename:
            telem_path = os.path.join(output_dir, telemetry_filename)
            try:
                import csv
                with open(telem_path, "r", encoding="utf-8") as tf:
                    reader = csv.DictReader(tf)
                    for r in reader:
                        telemetry_points.append({
                            "timestamp": float(r.get("timestamp", 0)),
                            "lat": float(r.get("lat", 28.6139)),
                            "lon": float(r.get("lon", 77.2090)),
                            "alt": float(r.get("alt", 120.0)),
                            "yaw": float(r.get("yaw", 0.0)),
                            "pitch": float(r.get("pitch", -45.0))
                        })
            except Exception as e:
                logger.warning(f"Telemetry parse error: {e}")

        # Step 1: extract_frames()
        if is_cancelled(): return
        update_job_status(job_id, "extracting", 10.0, "Frame Extraction", "Extracting video frames...", log_line=f"Extracting frames at {settings.MAX_FPS} FPS (Target: {target_width}x{target_height}).")
        raw_frames = extract_frames(video_path, output_dir, sample_fps=settings.MAX_FPS, target_width=target_width, target_height=target_height, downscale_on_cpu=(device == "cpu"))

        # Step 2: select_sharp_frames()
        if is_cancelled(): return
        update_job_status(job_id, "sharpness_filtering", 22.0, "Sharp Frame Selection", "Filtering blurry frames using Laplacian variance...", log_line=f"Scored {len(raw_frames)} frames.")
        sharp_frames, sharp_stats = select_sharp_frames(raw_frames, threshold=settings.SHARPNESS_THRESHOLD)

        # Step 3: preprocess_frames()
        if is_cancelled(): return
        update_job_status(job_id, "preprocessing", 35.0, "Preprocessing", "Normalizing exposure (CLAHE) & suppressing sensor noise...", log_line=f"Preprocessed {len(sharp_frames)} frames.")
        preprocessed_frames = preprocess_frames(sharp_frames, output_dir)

        # Step 4: mask_dynamic_objects()
        if is_cancelled(): return
        update_job_status(job_id, "masking", 48.0, "Dynamic Object Masking", "Masking moving vehicles and humans...", log_line="Running dynamic object segmentation.")
        masked_frames, dyn_count = mask_dynamic_objects(preprocessed_frames, output_dir, device=device)

        # Step 5: estimate_poses()
        if is_cancelled(): return
        update_job_status(job_id, "pose_estimation", 60.0, "Pose Estimation", "Estimating camera poses and visual SLAM...", log_line="Matching features and solving Essential matrix.")
        pose_res = estimate_poses(masked_frames, telemetry_points, output_dir)
        camera_poses = pose_res["camera_poses"]
        intrinsics = pose_res["intrinsics"]
        sparse_points = pose_res["sparse_points"]

        # Step 6: estimate_depth()
        if is_cancelled(): return
        update_job_status(job_id, "depth_estimation", 72.0, "Dense Depth Estimation", "Computing hybrid MVS disparity and AI metric depth...", log_line="Generating metric depth maps.")
        depth_records = estimate_depth(masked_frames, camera_poses, output_dir, device=device)

        # Step 7: fuse_depth()
        if is_cancelled(): return
        update_job_status(job_id, "depth_fusion", 84.0, "Depth Fusion", "Confidence-aware multi-view depth fusion...", log_line="Backprojecting rays and calculating confidence scores.")
        fusion_res = fuse_depth(depth_records, camera_poses, intrinsics, output_dir, confidence_threshold=settings.CONFIDENCE_THRESHOLD)
        points = fusion_res["points"]
        colors = fusion_res["colors"]
        confidences = fusion_res["confidences"]
        mean_conf = fusion_res["mean_confidence"]

        # Step 8: generate_mesh()
        if is_cancelled(): return
        update_job_status(job_id, "meshing", 92.0, "Mesh Generation", "Reconstructing surface mesh and textures...", log_line="Reconstructing 3D surface Delaunay mesh.")
        mesh_info = generate_mesh(points, colors, confidences, output_dir)

        # Step 9: georeference()
        if is_cancelled(): return
        update_job_status(job_id, "georeferencing", 96.0, "Georeferencing", "Georeferencing 3D reconstruction to UTM...", log_line="Calculating Sim3 Helmert transformation.")
        geo_info = georeference(points, camera_poses, telemetry_points, output_dir)

        # Step 10: export_outputs()
        if is_cancelled(): return
        update_job_status(job_id, "exporting", 98.0, "Exporting Outputs", "Exporting PLY, LAS, GLB, GeoTIFF DSM, and report...", log_line="Packaging all final artifacts.")
        artifacts = export_outputs(points, colors, confidences, mesh_info, geo_info, camera_poses, output_dir)

        # Final Update
        metrics = {
            "total_frames": len(raw_frames),
            "sharp_frames": len(sharp_frames),
            "dynamic_objects_detected": dyn_count,
            "sparse_points_count": len(sparse_points),
            "dense_points_count": len(points),
            "mesh_faces_count": mesh_info.get("face_count", 0),
            "mean_confidence": round(mean_conf, 3),
            "utm_zone": geo_info.get("utm_zone", "WGS 84 / UTM Zone 43N")
        }

        update_job_status(
            job_id, "completed", 100.0, "Completed",
            "3D model generated and georeferenced successfully.",
            metrics=metrics,
            artifacts=artifacts,
            log_line="Reconstruction complete! Open 3D viewer to inspect model."
        )

    except Exception as e:
        logger.exception(f"Pipeline error for job {job_id}: {e}")
        update_job_status(
            job_id, "failed", 0.0, "Failed",
            f"Pipeline failed: {str(e)}",
            log_line=f"ERROR: {str(e)}"
        )

@celery_app.task(name="worker.pipeline.tasks.run_pipeline")
def run_pipeline(job_id: str):
    """Celery entry point."""
    logger.info(f"Celery received job {job_id}")
    run_pipeline_sync(job_id)
