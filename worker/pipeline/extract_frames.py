import os
import cv2
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def extract_frames(
    video_path: str,
    output_dir: str,
    sample_fps: float = 3.0,
    target_width: int = 1280,
    target_height: int = 720,
    downscale_on_cpu: bool = True
) -> List[Dict[str, Any]]:
    """
    Extracts frames from drone video at a controlled sample rate.
    Downscales frames to 720p if GPU is unavailable.
    Returns list of extracted frame records with timestamps.
    """
    frames_dir = os.path.join(output_dir, "extracted_frames")
    os.makedirs(frames_dir, exist_ok=True)

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_video_frames / video_fps if video_fps > 0 else 0

    # Determine frame step interval
    step = max(1, int(round(video_fps / sample_fps)))
    logger.info(f"Video: {video_fps:.1f} FPS, {total_video_frames} frames ({duration_sec:.1f}s). Sampling every {step} frames (~{sample_fps} FPS).")

    extracted = []
    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % step == 0:
            timestamp = frame_count / video_fps
            h, w = frame.shape[:2]

            # Downscale to 720p if running on CPU or if source is 1080p/4K
            if downscale_on_cpu and (w > target_width or h > target_height):
                scale = min(target_width / w, target_height / h)
                new_w, new_h = int(w * scale), int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

            frame_filename = f"frame_{saved_count:05d}.jpg"
            frame_path = os.path.join(frames_dir, frame_filename)
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 92])

            extracted.append({
                "frame_idx": saved_count,
                "video_frame_id": frame_count,
                "timestamp": round(timestamp, 3),
                "path": frame_path,
                "width": frame.shape[1],
                "height": frame.shape[0]
            })
            saved_count += 1

        frame_count += 1

    cap.release()
    logger.info(f"Extracted {len(extracted)} frames to {frames_dir}")
    return extracted
