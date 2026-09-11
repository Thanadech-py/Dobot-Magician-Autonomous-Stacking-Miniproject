"""Pallet grid contour detection, validation, temporal tracking, and auto-locking."""

import os
import re
import cv2
import numpy as np
from dobot_v2.transforms import FieldTransform


class GridDetector:
    """Detects and stabilizes the 3x3 pallet grid on the Dobot workspace field."""

    def __init__(self, config: dict, logger=None):
        self.logger = logger
        self.auto_detect = bool(config.get('auto_detect_grid', True))
        self.lock_enabled = bool(config.get('lock_grid_after_detect', True))
        self.lock_threshold = int(config.get('lock_stable_frame_count', 10))
        self.alpha = float(config.get('grid_smoothing_alpha', 0.25))
        self.max_drift = float(config.get('max_corner_drift_px', 14.0))
        self.mean_drift = float(config.get('mean_corner_drift_px', 8.0))
        self.max_aspect_ratio = float(config.get('grid_max_aspect_ratio', 1.22))
        self.auto_save = bool(config.get('auto_save_grid_to_yaml', False))

        self.gray_min_v = int(config.get('gray_min_v', 105))
        self.gray_max_v = int(config.get('gray_max_v', 170))
        self.gray_max_s = int(config.get('gray_max_s', 50))

        self.kernel_3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        self.ellipse_9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))

        self.grid_corners = None
        self.is_locked = False
        self.stable_counter = 0

        # Load initial manual corners if provided
        raw_corners = config.get('grid_corners', [0.0] * 8)
        if len(raw_corners) == 8 and any(c > 0 for c in raw_corners):
            self.grid_corners = np.array([
                [raw_corners[0], raw_corners[1]],
                [raw_corners[2], raw_corners[3]],
                [raw_corners[4], raw_corners[5]],
                [raw_corners[6], raw_corners[7]]
            ], dtype=np.float32)
            self.is_locked = True
            if self.logger:
                self.logger.info('Using manually configured grid corners from YAML.')

    def detect(self, frame: np.ndarray) -> np.ndarray:
        """Finds or tracks the pallet grid. Returns 4 corners (TL, TR, BR, BL) or None."""
        # Instant bypass when locked: 0 CPU overhead during production
        if self.is_locked and self.grid_corners is not None:
            return self.grid_corners

        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. Mask out green feeder circles to prevent any bridging with the pallet
        mask_green = cv2.inRange(hsv, np.array([35, 50, 40], dtype=np.uint8),
                                 np.array([85, 255, 255], dtype=np.uint8))
        mask_green_dil = cv2.dilate(mask_green, self.ellipse_9, iterations=2)

        # 2. Strategy 1: Grey color segmentation of the pallet frame
        mask_gray = cv2.inRange(hsv,
                                np.array([0, 0, self.gray_min_v], dtype=np.uint8),
                                np.array([180, self.gray_max_s, self.gray_max_v], dtype=np.uint8))
        mask_gray_clean = cv2.bitwise_and(mask_gray, cv2.bitwise_not(mask_green_dil))
        closed = cv2.morphologyEx(mask_gray_clean, cv2.MORPH_CLOSE, self.kernel_3, iterations=1)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_quad, best_score = self._find_best_quad(contours, w, h)

        # 3. Strategy 2: Adaptive thresholding fallback
        if best_quad is None:
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 5
            )
            thresh_clean = cv2.bitwise_and(thresh, cv2.bitwise_not(mask_green_dil))
            cnts, _ = cv2.findContours(thresh_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            best_quad, best_score = self._find_best_quad(cnts, w, h)

        if best_quad is not None:
            ordered = FieldTransform.order_corners(best_quad)

            # Verification gate: Reject candidate if it contains feeder circles
            if not self._validate_pattern(frame, ordered):
                return self.grid_corners

            # Sub-pixel corner refinement
            try:
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.01)
                cv2.cornerSubPix(gray, ordered, (5, 5), (-1, -1), criteria)
            except Exception:
                pass

            # Temporal filter and stability accumulation
            if self.grid_corners is None:
                self.grid_corners = ordered
                self.stable_counter = 1
            else:
                drifts = np.linalg.norm(self.grid_corners - ordered, axis=1)
                if float(np.max(drifts)) < self.max_drift or float(np.mean(drifts)) < self.mean_drift:
                    self.stable_counter += 1
                else:
                    self.stable_counter = max(0, self.stable_counter - 2)

                self.grid_corners = (1.0 - self.alpha) * self.grid_corners + self.alpha * ordered

            # Auto-lock check
            if self.lock_enabled and not self.is_locked and self.stable_counter >= self.lock_threshold:
                self.is_locked = True
                if self.logger:
                    self.logger.info(f'*** Grid Local Frame LOCKED! (Stable for {self.stable_counter} frames) ***')
                if self.auto_save:
                    self.save_corners_to_yaml()

            return self.grid_corners

        return self.grid_corners

    def _find_best_quad(self, contours, w: int, h: int):
        best_quad, best_score = None, 0.0
        min_area, max_area = w * h * 0.025, w * h * 0.650

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area < area < max_area:
                rect = cv2.minAreaRect(cnt)
                (_, _), (rw, rh), _ = rect
                if min(rw, rh) > 0:
                    aspect = max(rw, rh) / min(rw, rh)
                    if aspect < self.max_aspect_ratio:
                        score = area * (1.0 - 2.0 * abs(aspect - 1.0))
                        if score > best_score:
                            peri = cv2.arcLength(cnt, True)
                            approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
                            if len(approx) == 4 and cv2.isContourConvex(approx):
                                best_quad = approx.reshape(4, 2).astype(np.float32)
                            else:
                                best_quad = cv2.boxPoints(rect).astype(np.float32)
                            best_score = score
        return best_quad, best_score

    def _validate_pattern(self, frame: np.ndarray, corners: np.ndarray) -> bool:
        """Validates candidate corners enclose the 3x3 pattern and NOT the green feeder circles."""
        try:
            dst = np.array([[0, 0], [150, 0], [150, 150], [0, 150]], dtype=np.float32)
            H = cv2.getPerspectiveTransform(corners, dst)
            patch = cv2.warpPerspective(frame, H, (150, 150))
            hsv_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
            gray_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)

            # Left 25% strip check: Must not contain green feeder circles
            left_strip = hsv_patch[:, :38]
            mask_left = cv2.inRange(left_strip, np.array([35, 50, 40]), np.array([85, 255, 255]))
            if (np.count_nonzero(mask_left) / (150 * 38)) > 0.08:
                return False

            # Cell center contrast check
            cell_vals = [
                gray_patch[max(0, r-6):min(150, r+6), max(0, c-6):min(150, c+6)].mean()
                for r in [29, 75, 121] for c in [29, 75, 121]
            ]
            div_vals = [
                gray_patch[48:56, 20:130].mean(), gray_patch[92:100, 20:130].mean(),
                gray_patch[20:130, 48:56].mean(), gray_patch[20:130, 92:100].mean()
            ]
            return abs(float(np.mean(cell_vals)) - float(np.mean(div_vals))) > 12.0
        except Exception:
            return False

    def reset(self):
        """Resets tracking state to start a fresh search."""
        self.grid_corners = None
        self.is_locked = False
        self.stable_counter = 0

    def lock(self):
        """Manually locks grid at current corners."""
        if self.grid_corners is not None:
            self.is_locked = True
            return True
        return False

    def unlock(self):
        """Unlocks grid and resumes live tracking."""
        self.is_locked = False
        self.stable_counter = 0

    def set_manual_corners(self, corners: np.ndarray):
        """Sets fixed corners manually and locks tracking."""
        self.grid_corners = FieldTransform.order_corners(corners)
        self.is_locked = True

    def save_corners_to_yaml(self):
        """Persists locked corners to detection_node.yaml."""
        if self.grid_corners is None:
            return
        flat = [round(float(c), 1) for pt in self.grid_corners for c in pt]
        paths = [
            os.path.expanduser("~/dobot_ws/src/dobot_v2/config/detection_node.yaml"),
            os.path.expanduser("~/dobot_ws/install/dobot_v2/share/dobot_v2/config/detection_node.yaml")
        ]
        for p in paths:
            try:
                rp = os.path.realpath(p)
                if os.path.exists(rp):
                    with open(rp, 'r') as f:
                        content = f.read()
                    new_line = f"    grid_corners: {flat}"
                    updated = re.sub(r"^\s*grid_corners:\s*\[.*?\]", new_line, content, flags=re.MULTILINE)
                    with open(rp, 'w') as f:
                        f.write(updated)
                    if self.logger:
                        self.logger.info(f'Auto-saved locked corners to {rp}')
            except Exception as e:
                if self.logger:
                    self.logger.warn(f'Could not write corners to {p}: {e}')
