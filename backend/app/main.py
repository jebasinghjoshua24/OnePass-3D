import os
import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api import jobs, telemetry

app = FastAPI(
    title="OnePass-3D - Drone 3D Reconstruction API",
    description="High-fidelity single-pass drone photogrammetry + monocular metric depth AI reconstruction platform.",
    version="1.0.0"
)

# Enable CORS for frontend at localhost:3000 and arbitrary origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(jobs.router, prefix="/api")
app.include_router(telemetry.router, prefix="/api")

@app.on_event("startup")
def startup_event():
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    init_db()

@app.get("/")
def root():
    return {
        "system": "OnePass-3D Prototype",
        "status": "online",
        "docs_url": "/docs",
        "api_v1": "/api"
    }

@app.get("/health")
@app.get("/api/health")
def health_check():
    cuda_available = False
    device_name = "CPU"
    try:
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            device_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    return {
        "status": "healthy",
        "hardware": {
            "device": "cuda" if cuda_available else "cpu",
            "cuda_available": cuda_available,
            "device_name": device_name,
            "downscale_active": not cuda_available
        },
        "config": {
            "target_resolution": f"{settings.TARGET_WIDTH}x{settings.TARGET_HEIGHT}",
            "storage_dir": settings.STORAGE_DIR,
            "mock_mode": True
        }
    }
