#!/usr/bin/env python3
"""
Interactive Field Grid Calibration Tool for Dobot Vision.

Allows clicking the 4 corners of the 3x3 Grid on the camera stream to achieve
exact pixel alignment. Automatically calculates Homography, previews the 3x3
grid lines and 9 cell boxes in real-time, and saves the corner coordinates into detection_node.yaml.
Also publishes directly to /set_grid_corners if detection_node is running.

Supports both:
  1. ROS 2 subscription (when dobot_vision.launch.py / usb_cam is running)
  2. Standalone OpenCV VideoCapture (when no ROS node is using the camera)

Usage:
  ros2 run dobot_v2 calibrate_grid
Or:
  python3 src/dobot_v2/dobot_v2/calibrate_grid.py
"""

import os
import sys
import cv2
import json
import time
import numpy as np

try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import CompressedImage, Image
    from std_msgs.msg import String
    from cv_bridge import CvBridge
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


class GridCalibrator:
    def __init__(self, yaml_path=None):
        self.points = []
        self.current_frame = None
        self.yaml_path = yaml_path
        self.running = True
        self.grid_size_mm = 114.5
        self.cell_size_mm = 25.0
        self.cell_pitch_mm = 35.0
        self.ros_publisher = None

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.points) < 4:
                self.points.append([float(x), float(y)])
                names = ["Top-Left (TL)", "Top-Right (TR)", "Bottom-Right (BR)", "Bottom-Left (BL)"]
                print(f"[{len(self.points)}/4] Recorded {names[len(self.points)-1]}: ({x:.1f}, {y:.1f})")

    def save_to_yaml(self, corners):
        flat_corners = [round(float(c), 1) for pt in corners for c in pt]
        print("\n" + "="*60)
        print("EXACT CORNERS FOR detection_node.yaml:")
        print(f"grid_corners: {flat_corners}")
        print("="*60 + "\n")

        # Save to YAML files
        yaml_candidates = [
            os.path.expanduser("~/dobot_ws/src/dobot_v2/config/detection_node.yaml"),
            os.path.expanduser("~/dobot_ws/install/dobot_v2/share/dobot_v2/config/detection_node.yaml")
        ]
        if self.yaml_path and self.yaml_path not in yaml_candidates:
            yaml_candidates.insert(0, self.yaml_path)

        for path in yaml_candidates:
            real_path = os.path.realpath(path)
            if os.path.exists(real_path):
                try:
                    with open(real_path, 'r') as f:
                        content = f.read()

                    import re
                    new_line = f"    grid_corners: {flat_corners}"
                    updated = re.sub(r"^\s*grid_corners:\s*\[.*?\]", new_line, content, flags=re.MULTILINE)

                    with open(real_path, 'w') as f:
                        f.write(updated)
                    print(f"SUCCESS: Saved grid_corners to: {real_path}")
                except Exception as e:
                    print(f"Error saving to {path}: {e}")

        # Publish live to detection_node if publisher is available
        if self.ros_publisher:
            try:
                msg = String()
                msg.data = json.dumps(corners)
                self.ros_publisher.publish(msg)
                print("SUCCESS: Published new corners to /set_grid_corners (detection_node updated live!)")
            except Exception as e:
                print(f"Could not publish corners: {e}")

    def draw_grid_preview(self, vis):
        n_pts = len(self.points)

        # Draw recorded points
        colors = [(0, 255, 0), (255, 255, 0), (0, 165, 255), (0, 0, 255)]
        labels = ["TL", "TR", "BR", "BL"]
        for i, pt in enumerate(self.points):
            px, py = int(round(pt[0])), int(round(pt[1]))
            cv2.circle(vis, (px, py), 6, colors[i], -1)
            cv2.putText(vis, f"P{i+1}: {labels[i]}", (px + 8, py - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, colors[i], 1, cv2.LINE_AA)

        # Connect points with lines
        if n_pts >= 2:
            for i in range(n_pts - 1):
                p1 = (int(round(self.points[i][0])), int(round(self.points[i][1])))
                p2 = (int(round(self.points[i+1][0])), int(round(self.points[i+1][1])))
                cv2.line(vis, p1, p2, (0, 255, 255), 2)

        if n_pts == 4:
            # Close polygon
            p1 = (int(round(self.points[3][0])), int(round(self.points[3][1])))
            p2 = (int(round(self.points[0][0])), int(round(self.points[0][1])))
            cv2.line(vis, p1, p2, (0, 255, 255), 2)

            # Compute Homography: Grid Local mm -> Camera Pixels
            pts_src = np.array(self.points, dtype=np.float32)
            pts_dst = np.array([
                [0.0, 0.0],
                [self.grid_size_mm, 0.0],
                [self.grid_size_mm, self.grid_size_mm],
                [0.0, self.grid_size_mm]
            ], dtype=np.float32)
            H_inv = cv2.getPerspectiveTransform(pts_dst, pts_src)

            def g2p(gx, gy):
                pt = np.array([[[float(gx), float(gy)]]], dtype=np.float32)
                res = cv2.perspectiveTransform(pt, H_inv)[0][0]
                return int(round(res[0])), int(round(res[1]))

            # Draw outer grey frame boundary in cyan
            poly = np.array([g2p(0, 0), g2p(self.grid_size_mm, 0),
                             g2p(self.grid_size_mm, self.grid_size_mm), g2p(0, self.grid_size_mm)])
            cv2.polylines(vis, [poly], isClosed=True, color=(255, 255, 0), thickness=2)

            # Draw 9 individual cell boxes (25x25mm)
            half = self.cell_size_mm / 2.0
            for r in range(3):
                for c in range(3):
                    cx = self.grid_size_mm / 2.0 + (c - 1) * self.cell_pitch_mm
                    cy = self.grid_size_mm / 2.0 + (r - 1) * self.cell_pitch_mm

                    cp1 = g2p(cx - half, cy - half)
                    cp2 = g2p(cx + half, cy - half)
                    cp3 = g2p(cx + half, cy + half)
                    cp4 = g2p(cx - half, cy + half)

                    cell_poly = np.array([cp1, cp2, cp3, cp4])
                    is_goal = (r == 1 and c == 1)
                    box_col = (0, 215, 255) if is_goal else (0, 220, 0)
                    cv2.polylines(vis, [cell_poly], isClosed=True, color=box_col, thickness=2)

                    center_p = g2p(cx, cy)
                    lbl = "GOAL" if is_goal else f"({r},{c})"
                    lbl_col = (0, 215, 255) if is_goal else (200, 200, 200)
                    cv2.circle(vis, center_p, 3, lbl_col, -1)
                    cv2.putText(vis, lbl, (center_p[0] - 14, center_p[1] + 4),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.35, lbl_col, 1, cv2.LINE_AA)

            # Coordinate Axes at Origin
            p0 = g2p(0, 0)
            px = g2p(30.0, 0)
            py = g2p(0, 30.0)
            cv2.arrowedLine(vis, p0, px, (0, 0, 255), 2, tipLength=0.25)
            cv2.arrowedLine(vis, p0, py, (0, 255, 0), 2, tipLength=0.25)
            cv2.putText(vis, "+X", (px[0] + 4, px[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            cv2.putText(vis, "+Y", (py[0] - 10, py[1] + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

            cv2.putText(vis, "CALIBRATION READY! Press [s] to SAVE or [r] to reset",
                        (10, vis.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 0), 2, cv2.LINE_AA)
        else:
            labels = ["1. Click Top-Left (TL)", "2. Click Top-Right (TR)", "3. Click Bottom-Right (BR)", "4. Click Bottom-Left (BL)"]
            cv2.putText(vis, labels[n_pts],
                        (10, vis.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2, cv2.LINE_AA)


def run_standalone():
    """Fallback OpenCV VideoCapture mode when ROS 2 is not streaming."""
    calibrator = GridCalibrator()
    window_name = "Field Grid Corner Calibration - Standalone"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(window_name, calibrator.mouse_callback)

    cap = None
    for dev in [0, 2]:
        test_cap = cv2.VideoCapture(dev)
        if test_cap.isOpened():
            ret, _ = test_cap.read()
            if ret:
                cap = test_cap
                print(f"Connected to camera /dev/video{dev}")
                break
            test_cap.release()

    if cap is None:
        print("ERROR: Could not open /dev/video0 or /dev/video2.")
        return

    _print_instructions()

    while calibrator.running:
        ret, frame = cap.read()
        if not ret:
            continue

        vis = frame.copy()
        calibrator.draw_grid_preview(vis)
        cv2.imshow(window_name, vis)
        key = cv2.waitKey(20) & 0xFF

        if key in [ord('q'), 27]:
            break
        elif key == ord('r'):
            calibrator.points = []
            print("Points reset. Click the 4 corners again.")
        elif key == ord('s') and len(calibrator.points) == 4:
            calibrator.save_to_yaml(calibrator.points)
            print("To apply in ROS 2, restart dobot_vision or check YAML.")
            break

    cap.release()
    cv2.destroyAllWindows()


def run_ros_node():
    """ROS 2 Node mode: subscribes to /image_raw/compressed and publishes to /set_grid_corners."""
    rclpy.init()
    node = rclpy.create_node('calibrate_grid_node')
    calibrator = GridCalibrator()
    bridge = CvBridge()
    window_name = "Field Grid Corner Calibration [ROS 2]"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(window_name, calibrator.mouse_callback)

    # Publisher to notify running detection_node immediately
    pub_corners = node.create_publisher(String, 'set_grid_corners', 10)
    calibrator.ros_publisher = pub_corners

    frame_holder = [None]

    def compressed_cb(msg: CompressedImage):
        try:
            np_arr = np.frombuffer(msg.data, np.uint8)
            frame_holder[0] = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception:
            pass

    def raw_cb(msg: Image):
        try:
            frame_holder[0] = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception:
            pass

    node.create_subscription(CompressedImage, '/image_raw/compressed', compressed_cb, 10)
    node.create_subscription(Image, '/image_raw', raw_cb, 10)

    _print_instructions()
    print("Waiting for camera frames on /image_raw/compressed or /image_raw...")

    try:
        while rclpy.ok() and calibrator.running:
            rclpy.spin_once(node, timeout_sec=0.03)

            if frame_holder[0] is not None:
                vis = frame_holder[0].copy()
                calibrator.draw_grid_preview(vis)
                cv2.imshow(window_name, vis)

            key = cv2.waitKey(20) & 0xFF
            if key in [ord('q'), 27]:
                break
            elif key == ord('r'):
                calibrator.points = []
                print("Points reset. Click the 4 corners again.")
            elif key == ord('s') and len(calibrator.points) == 4:
                calibrator.save_to_yaml(calibrator.points)
                break
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


def _print_instructions():
    print("\n" + "#"*60)
    print("  DOBOT V2 FIELD GRID CALIBRATION TOOL")
    print("#"*60)
    print("Instructions:")
    print("  1. Position your camera pointing down at the Field Template.")
    print("  2. Click the 4 OUTER corners of the 3x3 grey grid in order:")
    print("       Corner 1: Top-Left (TL)")
    print("       Corner 2: Top-Right (TR)")
    print("       Corner 3: Bottom-Right (BR)")
    print("       Corner 4: Bottom-Left (BL)")
    print("  3. Verify the 9 green/yellow cell boxes align with the paper.")
    print("  4. Keys:")
    print("       [s]: Save corners to YAML and update detection_node")
    print("       [r]: Reset points to re-click")
    print("       [q] or [ESC]: Quit")
    print("#"*60 + "\n")


def main():
    if HAS_ROS2:
        try:
            run_ros_node()
            return
        except Exception as e:
            print(f"ROS 2 mode error: {e}. Falling back to standalone OpenCV.")
    run_standalone()


if __name__ == '__main__':
    main()
