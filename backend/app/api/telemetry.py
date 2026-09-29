import csv
import io
import json
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas import TelemetryPoint

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

@router.post("/parse")
async def parse_telemetry(file: UploadFile = File(...)):
    """
    Parse uploaded drone telemetry CSV or JSON and return structured trajectory points.
    Expected fields: timestamp, lat, lon, alt, roll, pitch, yaw, baro_alt
    """
    filename = file.filename.lower()
    content = await file.read()
    points: List[Dict[str, Any]] = []

    try:
        if filename.endswith(".json"):
            data = json.loads(content.decode("utf-8"))
            if isinstance(data, list):
                points = data
            elif isinstance(data, dict) and "points" in data:
                points = data["points"]
        elif filename.endswith(".csv") or filename.endswith(".txt"):
            text = content.decode("utf-8", errors="ignore")
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                # normalize keys
                clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                points.append({
                    "timestamp": float(clean_row.get("timestamp", clean_row.get("time", len(points) * 0.5))),
                    "lat": float(clean_row.get("lat", clean_row.get("latitude", 28.6139))),
                    "lon": float(clean_row.get("lon", clean_row.get("lng", clean_row.get("longitude", 77.2090)))),
                    "alt": float(clean_row.get("alt", clean_row.get("altitude", 120.0))),
                    "roll": float(clean_row.get("roll", 0.0)),
                    "pitch": float(clean_row.get("pitch", 0.0)),
                    "yaw": float(clean_row.get("yaw", clean_row.get("heading", 0.0))),
                    "baro_alt": float(clean_row.get("baro_alt", clean_row.get("baro", 120.0)))
                })
        else:
            raise HTTPException(status_code=400, detail="Unsupported telemetry format. Use CSV or JSON.")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse telemetry: {str(e)}")

    return {
        "count": len(points),
        "trajectory": points[:100],  # preview first 100 points
        "start": points[0] if points else None,
        "end": points[-1] if points else None
    }
