"""Coordinate transforms between camera pixels, grid frame, field, and robot base."""

import math
import cv2
import numpy as np


class FieldTransform:
    """Manages geometric transformations and cell mappings."""

    def __init__(self, config: dict):
        self.grid_size = float(config.get('grid_size_mm', 114.5))
        self.cell_count = int(config.get('cell_count', 3))
        self.cell_size = float(config.get('cell_size_mm', 25.0))
        self.cell_pitch = float(config.get('cell_pitch_mm', 35.0))
        self.grid_tl_field_x = float(config.get('grid_tl_field_x_mm', 48.0))
        self.grid_tl_field_y = float(config.get('grid_tl_field_y_mm', 37.0))
        self.robot_base_x = float(config.get('robot_base_x_mm', 105.0))
        self.robot_base_y = float(config.get('robot_base_y_mm', 270.0))
        self.cube_z = float(config.get('cube_height_mm', 12.5))
        self.feeder_positions = config.get('feeder_positions', [])

        self.dst_grid_pts = np.array([
            [0.0, 0.0],
            [self.grid_size, 0.0],
            [self.grid_size, self.grid_size],
            [0.0, self.grid_size]
        ], dtype=np.float32)

        self.homography = None
        self.inv_homography = None

    @staticmethod
    def order_corners(pts: np.ndarray) -> np.ndarray:
        """Orders 4 points clockwise: [Top-Left, Top-Right, Bottom-Right, Bottom-Left]."""
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        rect[0] = pts[np.argmin(s)]       # TL
        rect[2] = pts[np.argmax(s)]       # BR
        rect[1] = pts[np.argmin(diff)]    # TR
        rect[3] = pts[np.argmax(diff)]    # BL
        return rect

    def update_corners(self, corners: np.ndarray):
        """Updates homography matrices given 4 camera pixel corners."""
        if corners is None or len(corners) != 4:
            return
        pts_src = corners.astype(np.float32)
        self.homography = cv2.getPerspectiveTransform(pts_src, self.dst_grid_pts)
        self.inv_homography = cv2.getPerspectiveTransform(self.dst_grid_pts, pts_src)

    def pixel_to_grid(self, u: float, v: float):
        """Transforms camera pixel (u, v) into Grid Local Frame coordinates (gx, gy) in mm."""
        if self.homography is None:
            return None
        px_pt = np.array([[[float(u), float(v)]]], dtype=np.float32)
        grid_pt = cv2.perspectiveTransform(px_pt, self.homography)[0][0]
        return float(grid_pt[0]), float(grid_pt[1])

    def grid_to_pixel(self, gx: float, gy: float):
        """Transforms Grid Local coordinates (gx, gy) in mm to camera pixel (u, v)."""
        if self.inv_homography is None:
            return None
        g_pt = np.array([[[float(gx), float(gy)]]], dtype=np.float32)
        px_pt = cv2.perspectiveTransform(g_pt, self.inv_homography)[0][0]
        return int(round(px_pt[0])), int(round(px_pt[1]))

    def grid_to_robot(self, gx: float, gy: float):
        """Transforms Grid Local coordinates (gx, gy) to Field and Dobot Base coordinates (mm)."""
        field_x = self.grid_tl_field_x + gx
        field_y = self.grid_tl_field_y + gy
        robot_x = self.robot_base_y - field_y
        robot_y = self.robot_base_x - field_x
        return (field_x, field_y), (robot_x, robot_y)

    def determine_cell(self, gx: float, gy: float):
        """Determines symmetric 3x3 cell index (row, col) and cell offsets from Grid Local coords."""
        div1 = self.grid_size / 2.0 - self.cell_pitch / 2.0
        div2 = self.grid_size / 2.0 + self.cell_pitch / 2.0
        col = int(np.clip(0 if gx < div1 else (1 if gx < div2 else 2), 0, self.cell_count - 1))
        row = int(np.clip(0 if gy < div1 else (1 if gy < div2 else 2), 0, self.cell_count - 1))

        center_x = self.grid_size / 2.0 + (col - 1) * self.cell_pitch
        center_y = self.grid_size / 2.0 + (row - 1) * self.cell_pitch
        dx = gx - center_x
        dy = gy - center_y

        is_goal = (row == 1 and col == 1)
        name = "GOAL" if is_goal else f"cell_{row}_{col}"

        return {
            'row': row,
            'col': col,
            'name': name,
            'is_goal': is_goal,
            'cell_center_mm': {'x': round(center_x, 1), 'y': round(center_y, 1)},
            'offset_mm': {'dx': round(dx, 1), 'dy': round(dy, 1)}
        }

    def check_feeder_slot(self, fx: float, fy: float):
        """Checks if a point in Field mm matches any defined feeder circle."""
        for feeder in self.feeder_positions:
            dist = math.sqrt((fx - feeder['x']) ** 2 + (fy - feeder['y']) ** 2)
            if dist <= feeder['radius']:
                return feeder['id']
        return None
