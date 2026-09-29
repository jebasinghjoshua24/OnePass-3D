import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# COCO classes representing dynamic / moving entities in drone aerial scenes
DYNAMIC_COCO_CLASSES = {0, 1, 2, 3, 5, 7, 14, 15, 16, 17, 18, 19}  # person, bike, car, moto, bus, truck, animals

def detect_dynamic_objects_yolo(img: np.ndarray, model) -> Tuple[np.ndarray, int]:
    """Runs YOLOv8 segmentation on the frame and returns binary mask and count."""
    h, w = img.shape[:2]
    # Default mask is all 255 (all static)
    static_mask = np.full((h, w), 255, dtype=np.uint8)
    dynamic_count = 0

    try:
        results = model(img, verbose=False, conf=0.35)
        for r in results:
            if r.boxes is not None and r.masks is not None:
                for cls_id, mask_poly in zip(r.boxes.cls, r.masks.data):
                    c = int(cls_id.item())
                    if c in DYNAMIC_COCO_CLASSES:
                        dynamic_count += 1
                        mask_np = mask_poly.cpu().numpy()
                        mask_resized = cv2.resize((mask_np * 255).astype(np.uint8), (w, h))
                        # Dilate mask slightly to prevent boundary blur artifacts
                        kernel = np.ones((7, 7), np.uint8)
                        mask_dilated = cv2.dilate(mask_resized, kernel, iterations=1)
                        # Dynamic regions become 0 (masked out)
                        static_mask[mask_dilated > 128] = 0
    except Exception as e:
        logger.warning(f"YOLO segmentation error: {e}")

    return static_mask, dynamic_count

def detect_dynamic_objects_optical_flow(
    curr_img: np.ndarray,
    prev_img: np.ndarray
) -> Tuple[np.ndarray, int]:
    """
    Detects dynamic moving objects using dense optical flow (Farneback)
    and frame difference subtraction.
    """
    h, w = curr_img.shape[:2]
    static_mask = np.full((h, w), 255, dtype=np.uint8)

    gray_curr = cv2.cvtColor(curr_img, cv2.COLOR_BGR2GRAY)
    gray_prev = cv2.cvtColor(prev_img, cv2.COLOR_BGR2GRAY)

    # Calculate dense optical flow
    flow = cv2.calcOpticalFlowFarneback(
        gray_prev, gray_curr, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0
    )
    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

    # Moving objects will exhibit flow magnitude significantly diverging from camera background motion
    bg_median = np.median(mag)
    diff = np.abs(mag - bg_median)
    thresh = np.percentile(diff, 96.0)

    motion_binary = (diff > max(thresh, 2.5)).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    motion_clean = cv2.morphologyEx(motion_binary, cv2.MORPH_OPEN, kernel)
    motion_dilated = cv2.dilate(motion_clean, kernel, iterations=2)

    contours, _ = cv2.findContours(motion_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    dynamic_count = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Filter realistic dynamic object size (e.g., cars/people: 150 - 50000 px)
        if 150 < area < (w * h * 0.25):
            cv2.drawContours(static_mask, [cnt], -1, 0, -1)
            dynamic_count += 1

    return static_mask, dynamic_count

def mask_dynamic_objects(
    frames: List[Dict[str, Any]],
    output_dir: str,
    device: str = "cpu"
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Detects and masks moving vehicles, pedestrians, and animals.
    Generates binary staticness masks (255 = static geometry, 0 = dynamic object).
    """
    masks_dir = os.path.join(output_dir, "dynamic_masks")
    os.makedirs(masks_dir, exist_ok=True)

    yolo_model = None
    try:
        from ultralytics import YOLO
        # Attempt to load lightweight YOLOv8-nano segmentation
        yolo_model = YOLO("yolov8n-seg.pt")
        logger.info("Loaded YOLOv8-seg model for dynamic entity removal.")
    except Exception as e:
        logger.info(f"Using high-performance optical motion segmentation fallback: {e}")

    total_dynamic_objects = 0
    masked_frames = []

    for i, f in enumerate(frames):
        img = cv2.imread(f["path"])
        if img is None:
            continue

        h, w = img.shape[:2]

        if yolo_model is not None:
            mask, count = detect_dynamic_objects_yolo(img, yolo_model)
        else:
            if i > 0:
                prev_img = cv2.imread(frames[i - 1]["path"])
                mask, count = detect_dynamic_objects_optical_flow(img, prev_img)
            else:
                mask = np.full((h, w), 255, dtype=np.uint8)
                count = 0

        total_dynamic_objects += count

        mask_filename = f"mask_{i:05d}.png"
        mask_path = os.path.join(masks_dir, mask_filename)
        cv2.imwrite(mask_path, mask)

        m_record = dict(f)
        m_record["mask_path"] = mask_path
        m_record["dynamic_objects"] = count
        masked_frames.append(m_record)

    logger.info(f"Dynamic object masking complete. {total_dynamic_objects} moving instances detected across {len(masked_frames)} frames.")
    return masked_frames, total_dynamic_objects
