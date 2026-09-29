from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class JobCreateRequest(BaseModel):
    name: Optional[str] = "OnePass-3D Survey"
    is_mock: bool = False
    scale_calibration_distance: Optional[float] = None  # in meters

class JobStatusResponse(BaseModel):
    job_id: str
    name: str
    status: str
    progress: float
    current_stage: str
    message: str
    error_message: Optional[str] = None
    is_mock: bool
    video_filename: Optional[str] = None
    telemetry_filename: Optional[str] = None
    metrics: Dict[str, Any]
    artifacts: Dict[str, str]
    logs: List[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class JobResultsResponse(BaseModel):
    job_id: str
    status: str
    artifacts: Dict[str, str]
    metrics: Dict[str, Any]

class CalibrationRequest(BaseModel):
    job_id: str
    point_a: List[float] = Field(..., description="[x, y, z] in model coordinate")
    point_b: List[float] = Field(..., description="[x, y, z] in model coordinate")
    real_distance_meters: float

class TelemetryPoint(BaseModel):
    timestamp: float
    lat: float
    lon: float
    alt: float
    roll: Optional[float] = 0.0
    pitch: Optional[float] = 0.0
    yaw: Optional[float] = 0.0
    baro_alt: Optional[float] = None
