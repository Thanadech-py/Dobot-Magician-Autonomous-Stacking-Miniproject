"""Color cube detection and classification using HSV segmentation and geometry filtering."""

import cv2
import numpy as np
from dobot_v2.transforms import FieldTransform


class CubeDetector:
    """Detects colored cubes in the workspace and maps them to grid and robot coordinates."""

    def __init__(self, config: dict):
        self.min_area = int(config.get('min_cube_area', 250))
        self.max_area = int(config.get('max_cube_area', 30000))
        self.max_aspect_ratio = float(config.get('max_cube_aspect_ratio', 2.2))
        self.min_solidity = float(config.get('min_cube_solidity', 0.78))
        self.min_extent = float(config.get('min_cube_extent', 0.65))
        self.green_max_circ = float(config.get('green_circle_max_circularity', 0.84))

        self.ws_min_x = float(config.get('workspace_min_x_mm', -35.0))
        self.ws_max_x = float(config.get('workspace_max_x_mm', 130.0))
        self.ws_min_y = float(config.get('workspace_min_y_mm', -2.0))
        self.ws_max_y = float(config.get('workspace_max_y_mm', 155.0))

        self.kernel_3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

        # Build color ranges
        def make_range(key, default):
            v = config.get(key, default)
            return (np.array([v[0], v[1], v[2]], dtype=np.uint8),
                    np.array([v[3], v[4], v[5]], dtype=np.uint8))

        self.color_ranges = {
            'red': [
                make_range('color_red_1', [0, 110, 70, 10, 255, 255]),
                make_range('color_red_2', [170, 110, 70, 180, 255, 255])
            ],
            'yellow': [make_range('color_yellow', [16, 110, 80, 35, 255, 255])],
            'green':  [make_range('color_green',  [36, 85, 70, 85, 255, 255])],
            'blue':   [make_range('color_blue',   [95, 105, 70, 135, 255, 255])]
        }

        self.display_colors = {
            'red': (0, 0, 255),
            'yellow': (0, 225, 255),
            'green': (0, 220, 0),
            'blue': (255, 60, 0)
        }

    def detect(self, hsv: np.ndarray, transform: FieldTransform):
        """Detects cubes in the frame given precomputed HSV image and transform."""
        detected = []
        counts = {'red': 0, 'yellow': 0, 'green': 0, 'blue': 0}

        if transform.homography is None:
            return detected, counts

        for color_name, ranges in self.color_ranges.items():
            if len(ranges) == 1:
                mask = cv2.inRange(hsv, ranges[0][0], ranges[0][1])
            else:
                m1 = cv2.inRange(hsv, ranges[0][0], ranges[0][1])
                m2 = cv2.inRange(hsv, ranges[1][0], ranges[1][1])
                mask = cv2.bitwise_or(m1, m2)

            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel_3, iterations=1)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if not (self.min_area <= area <= self.max_area):
                    continue

                rect = cv2.minAreaRect(cnt)
                (cx, cy), (rw, rh), angle = rect
                if rw <= 0 or rh <= 0:
                    continue

                if (max(rw, rh) / min(rw, rh)) > self.max_aspect_ratio:
                    continue

                hull_area = cv2.contourArea(cv2.convexHull(cnt))
                if hull_area <= 0:
                    continue
                if (area / hull_area) < self.min_solidity or (area / (rw * rh)) < self.min_extent:
                    continue

                # Filter out printed green feeder circles
                if color_name == 'green':
                    peri = cv2.arcLength(cnt, True)
                    circ = 4 * np.pi * area / (peri * peri) if peri > 0 else 0
                    if circ > self.green_max_circ and (area / (rw * rh)) < 0.82:
                        continue

                # Coordinate transforms
                grid_coord = transform.pixel_to_grid(cx, cy)
                if grid_coord is None:
                    continue
                gx, gy = grid_coord

                if not (self.ws_min_x <= gx <= self.ws_max_x and self.ws_min_y <= gy <= self.ws_max_y):
                    continue

                (fx, fy), (rx, ry) = transform.grid_to_robot(gx, gy)
                is_inside = (0.0 <= gx <= transform.grid_size and 0.0 <= gy <= transform.grid_size)
                cell_info = transform.determine_cell(gx, gy) if is_inside else None
                feeder_id = transform.check_feeder_slot(fx, fy) if not is_inside else None

                counts[color_name] += 1
                box_pts = cv2.boxPoints(rect)
                detected.append({
                    'color': color_name,
                    'bgr_color': [int(c) for c in self.display_colors[color_name]],
                    'pixel': {'u': int(cx), 'v': int(cy)},
                    'grid_local_mm': {'x': round(gx, 1), 'y': round(gy, 1)},
                    'in_grid': is_inside,
                    'cell': cell_info,
                    'grid_cell': cell_info,
                    'feeder_id': feeder_id,
                    'field_mm': {'x': round(fx, 1), 'y': round(fy, 1)},
                    'robot_mm': {'x': round(rx, 1), 'y': round(ry, 1), 'z': transform.cube_z},
                    'angle_deg': round(angle, 1),
                    'size_px': [int(rw), int(rh)],
                    'rect_points': [[round(float(p[0]), 1), round(float(p[1]), 1)] for p in box_pts],
                    'area': int(area)
                })

        return detected, counts
