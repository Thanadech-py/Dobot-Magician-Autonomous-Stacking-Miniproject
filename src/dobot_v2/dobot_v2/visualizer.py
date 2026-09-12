"""Visual overlays, HUD status banner, cell highlights, and coordinate axis rendering."""

import cv2
import numpy as np
from dobot_v2.transforms import FieldTransform


class DetectionVisualizer:
    """Renders debug overlays and tracking visual feedback onto camera frames."""

    @staticmethod
    def draw(frame: np.ndarray, transform: FieldTransform, corners: np.ndarray,
             detected_objects: list, counts: dict, is_locked: bool,
             lock_pct: int = 0) -> np.ndarray:
        """Renders grid, detected objects, and HUD onto a copy of the frame."""
        vis = frame.copy()

        # 1. Render 3x3 Grid Overlay & Cutouts
        if corners is not None and transform.inv_homography is not None:
            DetectionVisualizer._draw_grid(vis, transform, corners, detected_objects)

        # 2. Render Cube Bounding Boxes & Tags
        for obj in detected_objects:
            bgr = tuple(int(c) for c in obj['bgr_color'])
            rect_pts = obj.get('rect_points')
            if rect_pts is not None and len(rect_pts) > 0:
                box = np.intp(np.array(rect_pts, dtype=np.float32))
                cv2.drawContours(vis, [box], 0, bgr, 2)

            cx, cy = obj['pixel']['u'], obj['pixel']['v']
            cv2.drawMarker(vis, (cx, cy), bgr, cv2.MARKER_CROSS, 10, 2)

            tag = f"Cell: {obj['cell']['name']}" if obj['in_grid'] else (
                f"Feeder #{obj['feeder_id']}" if obj['feeder_id'] else "Outside Grid"
            )
            lbl1 = f"{obj['color'].upper()} | {tag}"
            lbl2 = f"Grid: ({obj['grid_local_mm']['x']:+.0f}, {obj['grid_local_mm']['y']:+.0f}) mm"
            lbl3 = f"Robot: ({obj['robot_mm']['x']:+.0f}, {obj['robot_mm']['y']:+.0f}) mm"

            tx = max(10, min(cx + 12, vis.shape[1] - 165))
            ty = max(45, min(cy - 8, vis.shape[0] - 25))

            cv2.rectangle(vis, (tx - 3, ty - 13), (tx + 160, ty + 31), (15, 15, 15), -1)
            cv2.rectangle(vis, (tx - 3, ty - 13), (tx + 160, ty + 31), bgr, 1)
            cv2.putText(vis, lbl1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.40, bgr, 1, cv2.LINE_AA)
            cv2.putText(vis, lbl2, (tx, ty + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1, cv2.LINE_AA)
            cv2.putText(vis, lbl3, (tx, ty + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 160, 160), 1, cv2.LINE_AA)

        # 3. Top HUD Status Bar
        DetectionVisualizer._draw_hud(vis, counts, len(detected_objects), corners, is_locked, lock_pct)
        return vis

    @staticmethod
    def _draw_grid(vis: np.ndarray, transform: FieldTransform, corners: np.ndarray, detected_objects: list):
        # Outer Pallet Boundary (Cyan)
        poly = corners.astype(np.int32)
        cv2.polylines(vis, [poly], isClosed=True, color=(255, 255, 0), thickness=2)
        for pt in poly:
            cv2.circle(vis, tuple(pt), 4, (255, 255, 0), -1)

        # 9 Cell Cutouts (Rendered from cached geometry with 0 matrix multiplications)
        cell_occupants = {
            (o['cell']['row'], o['cell']['col']): tuple(int(c) for c in o['bgr_color'])
            for o in detected_objects if o.get('cell')
        }

        cached = getattr(transform, 'cached_cells', None)
        if cached:
            for item in cached:
                r, c = item['row'], item['col']
                is_goal = item['is_goal']
                poly = item['poly']
                p_cell = item['center']
                occupant_bgr = cell_occupants.get((r, c))

                if poly is not None:
                    col = occupant_bgr if occupant_bgr else ((0, 215, 255) if is_goal else (140, 180, 140))
                    thick = 2 if (occupant_bgr or is_goal) else 1
                    cv2.polylines(vis, [poly], isClosed=True, color=col, thickness=thick)

                if p_cell:
                    col = (0, 220, 255) if is_goal else (160, 160, 160)
                    cv2.circle(vis, p_cell, 2, col, -1)
                    cv2.putText(vis, item['label'], (p_cell[0] - 14, p_cell[1] + 4),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.32, col, 1, cv2.LINE_AA)

        # Local Origin Axes (0,0) from cache
        orig = getattr(transform, 'cached_origin', None)
        if orig:
            p_origin = orig.get('p0')
            p_x = orig.get('px')
            p_y = orig.get('py')
            if p_origin and p_x and p_y:
                cv2.circle(vis, p_origin, 5, (0, 255, 255), -1)
                cv2.arrowedLine(vis, p_origin, p_x, (0, 0, 255), 2, tipLength=0.25)
                cv2.putText(vis, "+X", (p_x[0] + 4, p_x[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
                cv2.arrowedLine(vis, p_origin, p_y, (0, 255, 0), 2, tipLength=0.25)
                cv2.putText(vis, "+Y", (p_y[0] - 10, p_y[1] + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)

        # Dobot Base Projection
        bgx = transform.robot_base_x - transform.grid_tl_field_x
        bgy = transform.robot_base_y - transform.grid_tl_field_y
        p_base = transform.grid_to_pixel(bgx, bgy)
        if p_base and 0 <= p_base[0] < vis.shape[1] and 0 <= p_base[1] < vis.shape[0]:
            cv2.circle(vis, p_base, 5, (255, 0, 255), -1)
            cv2.putText(vis, "Dobot Base", (p_base[0] + 8, p_base[1] + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 255), 1)

    @staticmethod
    def _draw_hud(vis: np.ndarray, counts: dict, total: int, corners: np.ndarray,
                  is_locked: bool, lock_pct: int):
        cv2.rectangle(vis, (0, 0), (vis.shape[1], 30), (16, 16, 16), -1)
        if is_locked:
            status, col = "GRID: [LOCKED]", (0, 255, 0)
        elif corners is not None:
            status, col = f"GRID: [LOCKING {lock_pct}%]", (0, 255, 255)
        else:
            status, col = "GRID: [SEARCHING]", (0, 0, 255)

        cv2.putText(vis, f"DOBOT VISION V2 | {status}", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, col, 1, cv2.LINE_AA)

        c_str = (f"Red: {counts['red']} | Yellow: {counts['yellow']} | "
                 f"Green: {counts['green']} | Blue: {counts['blue']} | Total: {total}")
        tw = cv2.getTextSize(c_str, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)[0][0]
        cv2.putText(vis, c_str, (vis.shape[1] - tw - 12, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (230, 230, 230), 1, cv2.LINE_AA)
