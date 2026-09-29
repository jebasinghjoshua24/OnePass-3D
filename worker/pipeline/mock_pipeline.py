import os
import json
import math
import numpy as np
import cv2
import trimesh
import logging
from typing import Dict, Any, Tuple
from worker.pipeline.export_outputs import export_outputs

logger = logging.getLogger(__name__)

def generate_mock_drone_scene(output_dir: str) -> Dict[str, Any]:
    """
    Generates a realistic synthetic drone survey dataset:
    - 24 drone camera positions in flight orbit over a building
    - Multi-storey architectural building with solar panel roof, ground, trees
    - Moving vehicle detected and masked out
    - Dense point cloud with realistic confidence heatmap values
    - Textured 3D GLB & OBJ mesh
    - DSM GeoTIFF and Orthomosaic
    """
    os.makedirs(output_dir, exist_ok=True)
    frames_dir = os.path.join(output_dir, "extracted_frames")
    prep_dir = os.path.join(output_dir, "preprocessed_frames")
    masks_dir = os.path.join(output_dir, "dynamic_masks")
    depth_dir = os.path.join(output_dir, "depth_maps")

    for d in [frames_dir, prep_dir, masks_dir, depth_dir]:
        os.makedirs(d, exist_ok=True)

    num_keyframes = 20
    camera_poses = []
    telemetry_records = []

    center_lat = 28.6139
    center_lon = 77.2090
    base_alt = 120.0  # meters altitude

    # 1. Generate Camera Trajectory along a realistic curved inspection flight pass
    radius = 35.0  # meters from center
    for i in range(num_keyframes):
        angle = (i / num_keyframes) * 1.5 * math.pi - 0.75 * math.pi
        cam_x = radius * math.cos(angle)
        cam_y = radius * math.sin(angle)
        cam_z = base_alt + 5.0 * math.sin(i * 0.5)

        # Forward/downward viewing direction toward center (0, 0, 8)
        dx = -cam_x
        dy = -cam_y
        dz = 8.0 - cam_z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        yaw = math.degrees(math.atan2(dy, dx))
        pitch = math.degrees(math.asin(dz / dist))
        roll = 0.0

        ts = i * 0.75
        lat_offset = (cam_y / 111320.0)
        lon_offset = (cam_x / (111320.0 * math.cos(math.radians(center_lat))))

        telem = {
            "timestamp": round(ts, 2),
            "lat": round(center_lat + lat_offset, 6),
            "lon": round(center_lon + lon_offset, 6),
            "alt": round(cam_z, 1),
            "roll": 0.5,
            "pitch": round(pitch, 1),
            "yaw": round(yaw, 1),
            "baro_alt": round(cam_z, 1)
        }
        telemetry_records.append(telem)

        # Quaternion pointing toward origin
        cy = math.cos(math.radians(yaw * 0.5))
        sy = math.sin(math.radians(yaw * 0.5))
        cp = math.cos(math.radians(pitch * 0.5))
        sp = math.sin(math.radians(pitch * 0.5))

        camera_poses.append({
            "frame_idx": i,
            "timestamp": round(ts, 2),
            "position": [round(cam_x, 2), round(cam_y, 2), round(cam_z - base_alt + 15.0, 2)],
            "quaternion": [float(sp * sy), float(sp * cy), float(cp * sy), float(cp * cy)],
            "lat": telem["lat"],
            "lon": telem["lon"],
            "alt": telem["alt"],
            "yaw": telem["yaw"],
            "pitch": telem["pitch"],
            "sharpness": round(140.0 + 35.0 * math.sin(i * 0.8), 1)
        })

    # 2. Generate Synthetic Point Cloud with realistic building, ground, roof, trees, and dynamic car
    pts = []
    cols = []
    confs = []

    # A. Ground terrain (50m x 50m)
    gx, gy = np.meshgrid(np.linspace(-25, 25, 60), np.linspace(-25, 25, 60))
    gz = 0.3 * np.sin(gx * 0.15) + 0.2 * np.cos(gy * 0.15)
    g_points = np.column_stack((gx.flatten(), gy.flatten(), gz.flatten()))

    # Terrain colors: asphalt roads and grass
    for p in g_points:
        pts.append(p)
        if abs(p[0]) > 14 or abs(p[1]) > 14:
            # Grass / vegetation
            cols.append([50 + int(np.random.randint(0, 30)), 120 + int(np.random.randint(0, 40)), 45])
            confs.append(float(np.random.uniform(0.68, 0.85)))
        else:
            # Asphalt / courtyard ground
            cols.append([110, 115, 120])
            confs.append(float(np.random.uniform(0.88, 0.98)))

    # B. Main Commercial Building (20m x 14m x 12m height)
    b_width = 18.0
    b_depth = 12.0
    b_height = 10.5

    # Walls
    for wall_z in np.linspace(0, b_height, 22):
        # North & South walls
        for wx in np.linspace(-b_width/2, b_width/2, 35):
            pts.append([wx, -b_depth/2, wall_z])
            cols.append([210, 205, 195])  # Concrete / facade
            confs.append(0.85 + 0.10 * (wall_z / b_height))

            pts.append([wx, b_depth/2, wall_z])
            cols.append([200, 195, 190])
            confs.append(0.82 + 0.12 * (wall_z / b_height))

        # East & West walls
        for wy in np.linspace(-b_depth/2, b_depth/2, 25):
            pts.append([-b_width/2, wy, wall_z])
            cols.append([190, 185, 180])
            confs.append(0.84)

            pts.append([b_width/2, wy, wall_z])
            cols.append([215, 210, 200])
            confs.append(0.86)

    # C. Rooftop and Solar Panel Array
    rx, ry = np.meshgrid(np.linspace(-b_width/2 + 0.5, b_width/2 - 0.5, 36), np.linspace(-b_depth/2 + 0.5, b_depth/2 - 0.5, 24))
    rz = np.full_like(rx, b_height)
    roof_pts = np.column_stack((rx.flatten(), ry.flatten(), rz.flatten()))
    for p in roof_pts:
        pts.append(p)
        # Solar panel area in center of roof
        if -6.0 <= p[0] <= 6.0 and -4.0 <= p[1] <= 4.0:
            cols.append([25, 45, 115])  # Deep solar blue
            confs.append(0.96)  # High photogrammetric confidence on textured panels
        else:
            cols.append([170, 165, 160])  # Roof gravel/concrete
            confs.append(0.91)

    # D. Trees in surrounding perimeter
    for tx, ty in [(-18, -12), (18, -10), (-16, 16), (16, 14)]:
        for _ in range(120):
            r = np.random.uniform(0.5, 3.2)
            theta = np.random.uniform(0, 2 * math.pi)
            phi = np.random.uniform(0, math.pi)
            tree_z = 2.5 + r * math.cos(phi)
            pts.append([tx + r * math.sin(phi) * math.cos(theta), ty + r * math.sin(phi) * math.sin(theta), tree_z])
            cols.append([35, 110 + int(np.random.randint(0, 50)), 30])
            confs.append(float(np.random.uniform(0.52, 0.72)))  # Vegetation has lower multi-view confidence

    points_arr = np.array(pts, dtype=np.float32)
    colors_arr = np.array(cols, dtype=np.uint8)
    confs_arr = np.array(confs, dtype=np.float32)

    # 3. Create Textured 3D Mesh
    # Composite mesh of ground box, building box, and solar panels
    ground_mesh = trimesh.creation.box(extents=[50, 50, 0.4])
    ground_mesh.apply_translation([0, 0, -0.2])
    ground_mesh.visual.vertex_colors = [100, 110, 105, 255]

    building_mesh = trimesh.creation.box(extents=[b_width, b_depth, b_height])
    building_mesh.apply_translation([0, 0, b_height / 2.0])
    building_mesh.visual.vertex_colors = [210, 205, 195, 255]

    solar_mesh = trimesh.creation.box(extents=[12, 8, 0.25])
    solar_mesh.apply_translation([0, 0, b_height + 0.15])
    solar_mesh.visual.vertex_colors = [30, 55, 135, 255]

    combined_mesh = trimesh.util.concatenate([ground_mesh, building_mesh, solar_mesh])

    glb_path = os.path.join(output_dir, "model.glb")
    obj_path = os.path.join(output_dir, "model.obj")
    combined_mesh.export(glb_path, file_type="glb")
    combined_mesh.export(obj_path, file_type="obj")

    mesh_info = {
        "mesh_glb": glb_path,
        "mesh_obj": obj_path,
        "vertex_count": len(combined_mesh.vertices),
        "face_count": len(combined_mesh.faces)
    }

    # 4. Georeferencing
    geo_info = {
        "utm_zone": "WGS 84 / UTM Zone 43N",
        "epsg": 32643,
        "reference_lat": center_lat,
        "reference_lon": center_lon,
        "rmse_meters": 1.42,
        "confidence_level": "High (Sub-2m Single-Pass Accuracy)"
    }

    # 5. Export All Artifacts
    artifacts = export_outputs(
        points=points_arr,
        colors=colors_arr,
        confidences=confs_arr,
        mesh_info=mesh_info,
        geo_info=geo_info,
        camera_poses=camera_poses,
        output_dir=output_dir
    )

    # 6. Save mock camera frames and dynamic masks for demonstration
    for i in range(min(5, num_keyframes)):
        frame_canvas = np.full((720, 1280, 3), 130, dtype=np.uint8)
        # Draw sky, ground, building representation
        cv2.rectangle(frame_canvas, (0, 0), (1280, 320), (220, 180, 140), -1)  # sky
        cv2.rectangle(frame_canvas, (0, 320), (1280, 720), (80, 120, 70), -1)  # ground
        cv2.rectangle(frame_canvas, (380, 240), (900, 560), (200, 195, 190), -1)  # building
        cv2.rectangle(frame_canvas, (460, 250), (820, 380), (120, 60, 30), -1)  # solar roof
        # Moving car
        cv2.rectangle(frame_canvas, (180 + i * 25, 580), (280 + i * 25, 640), (40, 40, 200), -1)
        cv2.putText(frame_canvas, f"OnePass-3D Aerial Keyframe #{i+1} [720p CPU Downscale]", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

        f_path = os.path.join(frames_dir, f"frame_{i:05d}.jpg")
        cv2.imwrite(f_path, frame_canvas)

        # Dynamic mask: car region masked out (0), rest is 255
        mask_canvas = np.full((720, 1280), 255, dtype=np.uint8)
        cv2.rectangle(mask_canvas, (170 + i * 25, 570), (290 + i * 25, 650), 0, -1)
        m_path = os.path.join(masks_dir, f"mask_{i:05d}.png")
        cv2.imwrite(m_path, mask_canvas)

    return {
        "artifacts": artifacts,
        "points_count": len(points_arr),
        "mesh_faces": len(combined_mesh.faces),
        "mean_confidence": round(float(np.mean(confs_arr)), 3),
        "total_frames": num_keyframes,
        "sharp_frames": num_keyframes,
        "dynamic_objects": 1
    }
