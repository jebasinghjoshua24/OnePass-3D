import os
import numpy as np
import trimesh
import logging
from typing import Dict, Any
from scipy.spatial import Delaunay

logger = logging.getLogger(__name__)

def generate_mesh(
    points: np.ndarray,
    colors: np.ndarray,
    confidences: np.ndarray,
    output_dir: str,
    max_triangles: int = 40000
) -> Dict[str, Any]:
    """
    Generates a 3D surface mesh from the fused point cloud.
    Reconstructs surface faces, vertex normals, and vertex colors.
    Exports web-optimized .GLB and textured .OBJ formats.
    """
    if len(points) < 4:
        logger.warning("Insufficient points to generate mesh. Creating placeholder mesh.")
        box = trimesh.creation.box(extents=[10, 10, 5])
        glb_path = os.path.join(output_dir, "model.glb")
        obj_path = os.path.join(output_dir, "model.obj")
        box.export(glb_path)
        box.export(obj_path)
        return {
            "mesh_glb": glb_path,
            "mesh_obj": obj_path,
            "vertex_count": len(box.vertices),
            "face_count": len(box.faces)
        }

    # If point count is very high, subsample for fast robust surface reconstruction
    subsample_n = min(len(points), 12000)
    idx = np.random.choice(len(points), subsample_n, replace=False)
    pts_sub = points[idx]
    col_sub = colors[idx]
    conf_sub = confidences[idx] if len(confidences) == len(points) else np.ones(subsample_n)

    # 2.5D Delaunay surface triangulation (ideal for aerial drone terrain / rooftops)
    # Triangulate on XY plane, then filter long edge stretching
    xy = pts_sub[:, :2]
    tri = Delaunay(xy)
    faces = tri.simplices

    # Calculate triangle edge lengths in 3D to filter spurious stretched faces across boundaries
    p0 = pts_sub[faces[:, 0]]
    p1 = pts_sub[faces[:, 1]]
    p2 = pts_sub[faces[:, 2]]

    d01 = np.linalg.norm(p0 - p1, axis=1)
    d12 = np.linalg.norm(p1 - p2, axis=1)
    d20 = np.linalg.norm(p2 - p0, axis=1)

    max_edge = np.maximum(np.maximum(d01, d12), d20)
    valid_faces = faces[max_edge < 3.5]  # prune faces connecting distant points (> 3.5m)

    if len(valid_faces) == 0:
        valid_faces = faces[:max_triangles]
    elif len(valid_faces) > max_triangles:
        valid_faces = valid_faces[:max_triangles]

    # Normalize vertex colors to RGBA
    if col_sub.shape[1] == 3:
        rgba = np.hstack((col_sub, np.full((len(col_sub), 1), 255, dtype=np.uint8)))
    else:
        rgba = col_sub

    mesh = trimesh.Trimesh(
        vertices=pts_sub,
        faces=valid_faces,
        vertex_colors=rgba,
        process=True
    )

    # Smooth normals
    mesh.fix_normals()

    glb_path = os.path.join(output_dir, "model.glb")
    obj_path = os.path.join(output_dir, "model.obj")

    # Export GLB (standard for Three.js web viewer)
    mesh.export(glb_path, file_type="glb")

    # Export OBJ
    mesh.export(obj_path, file_type="obj")

    logger.info(f"Mesh generated: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces. Exported to {glb_path}")

    return {
        "mesh_glb": glb_path,
        "mesh_obj": obj_path,
        "vertex_count": int(len(mesh.vertices)),
        "face_count": int(len(mesh.faces))
    }
