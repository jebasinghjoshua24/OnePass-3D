import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def enhance_frame(
    img: np.ndarray,
    camera_matrix: Optional[np.ndarray] = None,
    dist_coeffs: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Applies lens distortion correction, illumination normalization (CLAHE),
    sensor denoising, and edge contrast sharpening.
    """
    # 1. Lens undistortion if camera calibration parameters are provided
    if camera_matrix is not None and dist_coeffs is not None:
        h, w = img.shape[:2]
        new_camera_mtx, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coeffs, (w, h), 1, (w, h))
        img = cv2.undistort(img, camera_matrix, dist_coeffs, None, new_camera_mtx)

    # 2. Exposure normalization via CLAHE on the L channel of LAB color space
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_norm = clahe.apply(l_channel)
    enhanced_lab = cv2.merge((l_norm, a_channel, b_channel))
    img_exposed = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

    # 3. Denoising while preserving high-contrast structural edges
    denoised = cv2.bilateralFilter(img_exposed, d=5, sigmaColor=35, sigmaSpace=35)

    # 4. Subtle unsharp masking for photogrammetric feature enhancement
    gaussian = cv2.GaussianBlur(denoised, (0, 0), 2.0)
    sharpened = cv2.addWeighted(denoised, 1.25, gaussian, -0.25, 0)

    return sharpened

def preprocess_frames(
    frames: List[Dict[str, Any]],
    output_dir: str,
    intrinsics: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Preprocesses retained keyframes: exposure correction, denoising, sharpening, and undistortion.
    Saves enhanced frames to preprocessed_frames/ directory.
    """
    prep_dir = os.path.join(output_dir, "preprocessed_frames")
    os.makedirs(prep_dir, exist_ok=True)

    camera_matrix = None
    dist_coeffs = None
    if intrinsics:
        try:
            fx = intrinsics.get("fx", 1000.0)
            fy = intrinsics.get("fy", 1000.0)
            cx = intrinsics.get("cx", 640.0)
            cy = intrinsics.get("cy", 360.0)
            camera_matrix = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float32)
            dist_coeffs = np.array(intrinsics.get("dist", [0, 0, 0, 0, 0]), dtype=np.float32)
        except Exception as e:
            logger.warning(f"Could not parse intrinsics: {e}")

    preprocessed = []
    for f in frames:
        img = cv2.imread(f["path"])
        if img is None:
            continue

        enhanced = enhance_frame(img, camera_matrix, dist_coeffs)

        fname = os.path.basename(f["path"])
        prep_path = os.path.join(prep_dir, f"prep_{fname}")
        cv2.imwrite(prep_path, enhanced, [cv2.IMWRITE_JPEG_QUALITY, 94])

        p_record = dict(f)
        p_record["original_path"] = f["path"]
        p_record["path"] = prep_path
        preprocessed.append(p_record)

    logger.info(f"Preprocessed {len(preprocessed)} frames (CLAHE exposure + bilateral denoising + sharpening).")
    return preprocessed
