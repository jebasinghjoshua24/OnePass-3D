import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, JSON
from app.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), default="Drone 3D Reconstruction")
    status = Column(String(50), default="queued", index=True)
    # Statuses: queued, extracting, sharpness_filtering, preprocessing, masking,
    #           pose_estimation, depth_estimation, depth_fusion, meshing,
    #           georeferencing, completed, failed, cancelled
    progress = Column(Float, default=0.0)
    current_stage = Column(String(100), default="Queued")
    message = Column(Text, default="Job submitted to queue.")
    error_message = Column(Text, nullable=True)

    is_mock = Column(Boolean, default=False)
    video_filename = Column(String(255), nullable=True)
    telemetry_filename = Column(String(255), nullable=True)

    # Reconstruction Metrics
    total_frames = Column(Integer, default=0)
    sharp_frames = Column(Integer, default=0)
    dynamic_objects_detected = Column(Integer, default=0)
    sparse_points_count = Column(Integer, default=0)
    dense_points_count = Column(Integer, default=0)
    mesh_faces_count = Column(Integer, default=0)
    mean_confidence = Column(Float, default=0.0)
    utm_zone = Column(String(50), default="WGS84 / UTM Zone 43N")

    # Artifacts map (keys: point_cloud, mesh_glb, mesh_obj, dsm, confidence, orthomosaic, camera_poses, report)
    artifacts = Column(JSON, default=dict)
    
    # Live logs preview array
    logs = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "job_id": self.id,
            "name": self.name,
            "status": self.status,
            "progress": round(self.progress, 1),
            "current_stage": self.current_stage,
            "message": self.message,
            "error_message": self.error_message,
            "is_mock": self.is_mock,
            "video_filename": self.video_filename,
            "telemetry_filename": self.telemetry_filename,
            "metrics": {
                "total_frames": self.total_frames,
                "sharp_frames": self.sharp_frames,
                "dynamic_objects_detected": self.dynamic_objects_detected,
                "sparse_points_count": self.sparse_points_count,
                "dense_points_count": self.dense_points_count,
                "mesh_faces_count": self.mesh_faces_count,
                "mean_confidence": round(self.mean_confidence, 3),
                "utm_zone": self.utm_zone,
            },
            "artifacts": self.artifacts or {},
            "logs": self.logs[-50:] if self.logs else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
