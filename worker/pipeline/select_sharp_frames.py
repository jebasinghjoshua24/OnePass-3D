import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

def compute_sharpness(image_path: str) -> float:
    """Computes frame sharpness using the variance of the Laplacian."""
    img = cv2.imread(image_path)
    if img is None:
        return 0.0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

def select_sharp_frames(
    frames: List[Dict[str, Any]],
    threshold: float = 85.0,
    min_keyframes: int = 8
) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """
    Evaluates sharpness for all frames.
    Filters out motion-blurred frames below threshold.
    Guarantees sufficient keyframes by adaptive selection if needed.
    """
    scored_frames = []
    scores = []

    for f in frames:
        score = compute_sharpness(f["path"])
        f_scored = dict(f)
        f_scored["sharpness"] = round(score, 2)
        scored_frames.append(f_scored)
        scores.append(score)

    if not scores:
        return [], {"mean_sharpness": 0.0, "retained_percentage": 0.0}

    mean_score = float(np.mean(scores))
    median_score = float(np.median(scores))

    # Initial filtering by threshold
    selected = [f for f in scored_frames if f["sharpness"] >= threshold]

    # Adaptive fallback: If threshold rejected too many, retain top N sharpest frames
    if len(selected) < min_keyframes and len(scored_frames) >= min_keyframes:
        logger.warning(
            f"Only {len(selected)} frames met sharpness threshold {threshold}. "
            f"Adaptive keyframe selection retaining top {min_keyframes} frames."
        )
        sorted_by_sharp = sorted(scored_frames, key=lambda x: x["sharpness"], reverse=True)
        selected = sorted_by_sharp[:min_keyframes]
        # Re-sort chronologically by frame_idx
        selected = sorted(selected, key=lambda x: x["frame_idx"])

    # If total frames is less than min_keyframes, retain all
    if not selected:
        selected = scored_frames

    stats = {
        "mean_sharpness": round(mean_score, 2),
        "median_sharpness": round(median_score, 2),
        "total_evaluated": len(frames),
        "sharp_retained": len(selected),
        "retained_percentage": round((len(selected) / len(frames)) * 100, 1) if frames else 0.0
    }

    logger.info(f"Sharp frame selection: retained {len(selected)}/{len(frames)} frames ({stats['retained_percentage']}%, mean sharpness: {mean_score:.1f}).")
    return selected, stats
