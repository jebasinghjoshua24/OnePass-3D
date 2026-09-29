import os
import math
import numpy as np
import cv2

def generate_sample_drone_video(output_path: str, duration_sec: int = 6, fps: int = 24):
    """Generates a synthetic 720p drone flight video with terrain, building, and moving vehicle."""
    width = 1280
    height = 720
    total_frames = duration_sec * fps

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"Generating {duration_sec}s drone flight video ({total_frames} frames)...")

    for i in range(total_frames):
        t = i / total_frames
        frame = np.full((height, width, 3), 110, dtype=np.uint8)

        # Sky with gradient
        sky_h = int(220 + 30 * math.sin(t * math.pi))
        for y in range(sky_h):
            ratio = y / sky_h
            b = int(220 - 40 * ratio)
            g = int(180 - 40 * ratio)
            r = int(120 - 20 * ratio)
            frame[y, :] = (b, g, r)

        # Ground terrain
        for y in range(sky_h, height):
            ratio = (y - sky_h) / (height - sky_h)
            b = int(50 + 20 * ratio)
            g = int(110 + 30 * ratio)
            r = int(60 + 20 * ratio)
            frame[y, :] = (b, g, r)

        # Access road (asphalt)
        road_pts = np.array([
            [int(width * 0.1 - t * 40), height],
            [int(width * 0.35 - t * 20), sky_h + 80],
            [int(width * 0.50 - t * 15), sky_h + 80],
            [int(width * 0.45 - t * 30), height]
        ], np.int32)
        cv2.fillPoly(frame, [road_pts], (80, 85, 90))

        # Main building structure (shifts due to drone camera motion)
        bx = int(500 - t * 120)
        by = int(240 + t * 40)
        bw = int(380 + t * 30)
        bh = int(260 + t * 20)

        # Building facade
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (195, 190, 185), -1)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (120, 115, 110), 3)

        # Windows
        for row in range(3):
            for col in range(5):
                wx = bx + 30 + col * int((bw - 60) / 4)
                wy = by + 30 + row * 65
                cv2.rectangle(frame, (wx, wy), (wx + 35, wy + 45), (140, 90, 40), -1)

        # Solar panel roof
        roof_poly = np.array([
            [bx - 15, by],
            [bx + int(bw * 0.5), by - 60],
            [bx + bw + 15, by]
        ], np.int32)
        cv2.fillPoly(frame, [roof_poly], (90, 45, 25))
        # Solar modules
        cv2.rectangle(frame, (bx + 40, by - 45), (bx + bw - 40, by - 10), (145, 65, 30), -1)

        # Moving Vehicle (dynamic object to be masked by YOLO/motion detection!)
        car_x = int(width * 0.18 + t * 180)
        car_y = int(sky_h + 160 + t * 120)
        car_w = int(75 + t * 25)
        car_h = int(35 + t * 12)
        cv2.rectangle(frame, (car_x, car_y), (car_x + car_w, car_y + car_h), (30, 30, 220), -1)  # Red car
        cv2.rectangle(frame, (car_x + 10, car_y - 12), (car_x + car_w - 15, car_y), (60, 60, 240), -1)

        # Drone HUD Telemetry Overlay
        alt_hud = 120.5 + t * 3.0
        cv2.putText(frame, f"REC [UAV-1] LAT: 28.6139 LON: 77.2090 ALT: {alt_hud:.1f}m GIMBAL: -45 deg", (35, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"FPS: {fps} | RES: 1280x720 | PASS: SINGLE-ORBIT | SINGLE-3D", (35, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 2)

        out.write(frame)

    out.release()
    print(f"Sample drone video created successfully at: {output_path}")

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    vid_path = os.path.join(out_dir, "sample_drone_video.mp4")
    generate_sample_drone_video(vid_path)
