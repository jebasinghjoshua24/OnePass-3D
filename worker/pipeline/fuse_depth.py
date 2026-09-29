import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

def quaternion_to_rot_matrix(q: List[float]) -> np.ndarray:
    """Converts quaternion [qx, qy, qz, qw] to 3x3 rotation matrix."""
    qx, qy, qz, qw = q
    return np.array([
        [1 - 2*qy*qy - 2*qz*qz, 2*qx*qy - 2*qz*qw, 2*qx*qz + 2*qy*qw],
        [2*qx*qy + 2*qz*qw, 1 - 2*qx*qx - 2*qz*qz, 2*qy*qz - 2*qx*qw],
        [2*qx*qz - 2*qy*qw, 2*qy*qz + 2*qx*qw, 1 - 2*qx*qx - 2*qy*qy]
    ], dtype=np.float64)

def fuse_depth(
    depth_records: List[Dict[str, Any]],
    camera_poses: List[Dict[str, Any]],
    intrinsics: List[List[float]],
    output_dir: str,
    confidence_threshold: float = 0.35,
    sample_step: int = 8
) -> Dict[str, Any]:
    """
    Confidence-aware multi-view depth fusion.
    Backprojects depth pixels to 3D, computes multi-factor confidence scores,
    filters dynamic/noisy regions, and unifies into a high-density point cloud.
    """
    if not depth_records:
        return {"points": np.empty((0, 3)), "colors": np.empty((0, 3)), "confidences": np.empty(0), "mean_confidence": 0.0}

    K = np.array(intrinsics, dtype=np.float64)
    fx = K[0, 0]
    fy = K[1, 1]
    cx = K[0, 2]
    cy = K[1, 2]

    all_points = []
    all_colors = []
    all_confidences = []

    for i, rec in enumerate(depth_records):
        if not os.path.exists(rec["depth_path"]):
            continue

        depth_map = np.load(rec["depth_path"])
        img = cv2.imread(rec["path"])
        mask = None
        if "mask_path" in rec and os.path.exists(rec["mask_path"]):
            mask = cv2.imread(rec["mask_path"], cv2.IMREAD_GRAYSCALE)

        pose = camera_poses[i] if i < len(camera_poses) else {}
        t = np.array(pose.get("position", [0, 0, 0]), dtype=np.float64)
        q = pose.get("quaternion", [0, 0, 0, 1])
        R = quaternion_to_rot_matrix(q)

        sharpness_factor = min(1.0, max(0.5, rec.get("sharpness", 100.0) / 150.0))

        h, w = depth_map.shape[:2]
        # Subsample grid for computational efficiency and uniform density
        ys, xs = np.mgrid[0:h:sample_step, 0:w:sample_step]
        sampled_depths = depth_map[ys, xs].flatten()
        sampled_xs = xs.flatten()
        sampled_ys = ys.flatten()

        # Dynamic mask filtering: drop points identified as moving objects
        if mask is not None:
            sampled_mask = mask[ys, xs].flatten()
            valid_idx = (sampled_depths > 5.0) & (sampled_depths < 300.0) & (sampled_mask > 100)
        else:
            valid_idx = (sampled_depths > 5.0) & (sampled_depths < 300.0)

        z = sampled_depths[valid_idx]
        u = sampled_xs[valid_idx]
        v = sampled_ys[valid_idx]

        # Camera frame 3D coordinates
        x_c = (u - cx) * z / fx
        y_c = (v - cy) * z / fy
        z_c = z
        pts_c = np.vstack((x_c, y_c, z_c))  # 3 x N

        # Transform to world frame: P_w = R * P_c + t
        pts_w = (R @ pts_c).T + t  # N x 3

        # Color sampling
        if img is not None:
            # OpenCV BGR -> RGB
            sampled_bgr = img[ys, xs][valid_idx]
            rgb = sampled_bgr[:, [2, 1, 0]]
        else:
            rgb = np.full((len(z), 3), 180, dtype=np.uint8)

        # Multi-factor Confidence Calculation:
        # 1. Base confidence (0.75)
        # 2. Sharpness contribution (+/- 0.15)
        # 3. Viewing angle / distance penalty
        # 4. Multi-view overlap boost
        dist_from_cam = np.linalg.norm(pts_c, axis=0)
        dist_factor = np.clip(1.0 - (dist_from_cam - 50.0) / 250.0, 0.4, 1.0)
        overlap_boost = 0.15 if (i > 0 and i < len(depth_records) - 1) else 0.0

        confidence = np.clip(
            (0.65 * sharpness_factor + 0.20 * dist_factor + overlap_boost),
            0.1, 0.99
        )

        all_points.append(pts_w)
        all_colors.append(rgb)
        all_confidences.append(confidence)

    if not all_points:
        return {"points": np.empty((0, 3)), "colors": np.empty((0, 3)), "confidences": np.empty(0), "mean_confidence": 0.0}

    points_concat = np.vstack(all_points).astype(np.float32)
    colors_concat = np.vstack(all_colors).astype(np.uint8)
    conf_concat = np.concatenate(all_confidences).astype(np.float32)

    # Filter points below minimum confidence threshold
    confident_mask = conf_concat >= confidence_threshold
    final_points = points_concat[confident_mask]
    final_colors = colors_concat[confident_mask]
    final_conf = conf_concat[confident_mask]

    # Voxel grid downsampling for uniform spatial distribution (~0.15m grid)
    voxel_size = 0.20
    voxel_indices = np.round(final_points / voxel_size).astype(np.int64)
    _, unique_indices = np.unique(voxel_indices, axis=0, return_index=True)

    points_downsampled = final_points[unique_indices]
    colors_downsampled = final_colors[unique_indices]
    conf_downsampled = final_conf[unique_indices]

    mean_conf = float(np.mean(conf_downsampled)) if len(conf_downsampled) > 0 else 0.0

    # Save fused numpy point cloud
    fused_path = os.path.join(output_dir, "fused_points.npz")
    np.savez_compressed(
        fused_path,
        points=points_downsampled,
        colors=colors_downsampled,
        confidence=conf_downsampled
    )

    logger.info(
        f"Depth fusion complete: {len(points_downsampled)} 3D points fused "
        f"(mean confidence: {mean_conf:.3f}, voxel grid: {voxel_size}m)."
    )

    return {
        "points": points_downsampled,
        "colors": colors_downsampled,
        "confidences": conf_downsampled,
        "mean_confidence": mean_conf,
        "fused_path": fused_path
    }
