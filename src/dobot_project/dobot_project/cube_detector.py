#!/usr/bin/env python3
"""
ROS 2 Node: Real-time Color Cube Detector & Workspace Coordinate Mapper for Dobot.

Subscribes to:
  - /image_decoded (sensor_msgs/msg/Image)  – decoded from /image_raw/theora via republish node

Publishes:
  - /detected_objects_image (sensor_msgs/msg/Image): Annotated visualization video stream
  - /detected_objects (std_msgs/msg/String): JSON payload of detected cubes with coordinates
  - /detected_objects_poses (geometry_msgs/msg/PoseArray): 3D poses in Dobot robot frame
"""

import json
import math
import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from geometry_msgs.msg import PoseArray, Pose
from std_msgs.msg import String


class CubeDetectorNode(Node):
    def __init__(self):
        super().__init__('cube_detector_node')

        # ----------------- Parameters -----------------
        self.declare_parameter('image_topic', 'image_decoded')
        self.declare_parameter('field_width_mm', 210.0)      # A4 width in mm
        self.declare_parameter('field_height_mm', 297.0)     # A4 height in mm
        self.declare_parameter('robot_base_x_mm', 105.0)     # Center of A4 template width
        self.declare_parameter('robot_base_y_mm', 270.0)     # Offset from top to Dobot base
        self.declare_parameter('cube_height_mm', 12.5)       # Half-height of 25mm cube
        self.declare_parameter('min_contour_area', 300)      # Min area in pixels
        self.declare_parameter('max_contour_area', 18000)    # Max area in pixels
        self.declare_parameter('show_field_overlay', True)

        # 4 corners of the field template in camera pixels: [TL_x, TL_y, TR_x, TR_y, BR_x, BR_y, BL_x, BL_y]
        # Set to all zeros to trigger automatic template corner detection
        self.declare_parameter(
            'field_corners',
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        )

        self.image_topic = self.get_parameter('image_topic').value
        self.field_w = float(self.get_parameter('field_width_mm').value)
        self.field_h = float(self.get_parameter('field_height_mm').value)
        self.robot_base_x = float(self.get_parameter('robot_base_x_mm').value)
        self.robot_base_y = float(self.get_parameter('robot_base_y_mm').value)
        self.cube_z = float(self.get_parameter('cube_height_mm').value)
        self.min_area = int(self.get_parameter('min_contour_area').value)
        self.max_area = int(self.get_parameter('max_contour_area').value)
        self.show_overlay = bool(self.get_parameter('show_field_overlay').value)

        # Target template corners in real-world mm (TL, TR, BR, BL)
        self.dst_field_pts = np.array([
            [0.0, 0.0],
            [self.field_w, 0.0],
            [self.field_w, self.field_h],
            [0.0, self.field_h]
        ], dtype=np.float32)

        raw_corners = self.get_parameter('field_corners').value
        if len(raw_corners) == 8 and any(c != 0.0 for c in raw_corners):
            self.src_cam_pts = np.array([
                [raw_corners[0], raw_corners[1]],
                [raw_corners[2], raw_corners[3]],
                [raw_corners[4], raw_corners[5]],
                [raw_corners[6], raw_corners[7]]
            ], dtype=np.float32)
            self.auto_calibrate = False
            self._update_homography()
            self.get_logger().info('Using manually configured field corners.')
        else:
            self.src_cam_pts = None
            self.auto_calibrate = True
            self.homography = None
            self.inv_homography = None
            self.get_logger().info('Field corners set to AUTO - will detect field template from stream.')

        # ----------------- Color Calibration (HSV Ranges) -----------------
        self.color_ranges = {
            'red': [
                (np.array([0, 110, 70], dtype=np.uint8), np.array([10, 255, 255], dtype=np.uint8)),
                (np.array([170, 110, 70], dtype=np.uint8), np.array([180, 255, 255], dtype=np.uint8))
            ],
            'yellow': [
                (np.array([18, 110, 90], dtype=np.uint8), np.array([35, 255, 255], dtype=np.uint8))
            ],
            'green': [
                (np.array([36, 90, 70], dtype=np.uint8), np.array([85, 255, 255], dtype=np.uint8))
            ],
            'blue': [
                (np.array([95, 110, 70], dtype=np.uint8), np.array([130, 255, 255], dtype=np.uint8))
            ]
        }

        # BGR display colors for visualization
        self.display_colors = {
            'red': (0, 0, 255),
            'yellow': (0, 235, 255),
            'green': (0, 220, 0),
            'blue': (255, 50, 0)
        }

        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

        # ----------------- Publishers & Subscribers -----------------
        # QoS: best-effort, keep-last-1 so we always process the freshest frame
        sub_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        self.sub_image = self.create_subscription(
            Image,
            self.image_topic,
            self._image_callback,
            sub_qos
        )

        # Output visualization video stream
        self.pub_annotated_image = self.create_publisher(
            Image,
            'detected_objects_image',
            qos_profile_sensor_data
        )

        # Structured JSON coordinates for UI / Dashboard
        self.pub_objects_json = self.create_publisher(
            String,
            'detected_objects',
            10
        )

        # Standard ROS 3D Poses for RViz / Dobot controller / MoveIt
        self.pub_poses = self.create_publisher(
            PoseArray,
            'detected_objects_poses',
            10
        )

        # Pre-allocated message for output video stream
        self.out_image_msg = Image()
        self.out_image_msg.encoding = 'bgr8'
        self.out_image_msg.is_bigendian = 0
        self.out_image_msg.header.frame_id = 'camera_frame'

        self.get_logger().info(f'CubeDetectorNode initialized. Subscribed to {self.image_topic}.')

    def _update_homography(self):
        """Calculates forward and inverse homography between camera pixels and field mm."""
        if self.src_cam_pts is not None and len(self.src_cam_pts) == 4:
            self.homography = cv2.getPerspectiveTransform(self.src_cam_pts, self.dst_field_pts)
            self.inv_homography = cv2.getPerspectiveTransform(self.dst_field_pts, self.src_cam_pts)

    def _detect_field_corners(self, gray_frame):
        """Attempts to auto-detect the 4 outer corners of the A4 field template."""
        h, w = gray_frame.shape
        blurred = cv2.GaussianBlur(gray_frame, (5, 5), 0)
        edges = cv2.Canny(blurred, 40, 150)
        edges = cv2.dilate(edges, self.morph_kernel, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_quad = None
        max_area = (h * w) * 0.10  # Must cover at least 10% of frame

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > max_area:
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
                if len(approx) == 4 and cv2.isContourConvex(approx):
                    max_area = area
                    best_quad = approx.reshape(4, 2)

        if best_quad is not None:
            # Order corners: TL, TR, BR, BL
            pts = np.zeros((4, 2), dtype=np.float32)
            s = best_quad.sum(axis=1)
            pts[0] = best_quad[np.argmin(s)]  # Top-left has min sum
            pts[2] = best_quad[np.argmax(s)]  # Bottom-right has max sum
            diff = np.diff(best_quad, axis=1)
            pts[1] = best_quad[np.argmin(diff)]  # Top-right has min diff
            pts[3] = best_quad[np.argmax(diff)]  # Bottom-left has max diff
            return pts

        # Default fallback: 5% inset margin from image edges
        return np.array([
            [w * 0.05, h * 0.05],
            [w * 0.95, h * 0.05],
            [w * 0.95, h * 0.95],
            [w * 0.05, h * 0.95]
        ], dtype=np.float32)

    def _pixel_to_robot(self, u, v):
        """Transforms camera pixel (u, v) to Field mm and Dobot Robot Base frame mm."""
        if self.homography is None:
            return (0.0, 0.0), (0.0, 0.0)

        px_arr = np.array([[[float(u), float(v)]]], dtype=np.float32)
        field_pt = cv2.perspectiveTransform(px_arr, self.homography)[0][0]
        field_x = float(field_pt[0])
        field_y = float(field_pt[1])

        # Robot Base Frame:
        # Dobot origin (0, 0) is at base center (robot_base_x, robot_base_y)
        # +X is forward (upwards along template) = (robot_base_y - field_y)
        # +Y is leftward (towards circles 1-4)   = (robot_base_x - field_x)
        robot_x = self.robot_base_y - field_y
        robot_y = self.robot_base_x - field_x

        return (field_x, field_y), (robot_x, robot_y)

    def _field_to_pixel(self, fx, fy):
        """Projects a point from Field mm back to camera image pixel (u, v)."""
        if self.inv_homography is None:
            return None
        f_arr = np.array([[[float(fx), float(fy)]]], dtype=np.float32)
        px_pt = cv2.perspectiveTransform(f_arr, self.inv_homography)[0][0]
        return int(px_pt[0]), int(px_pt[1])

    def _image_callback(self, msg: Image):
        # 1. Direct unpack from buffer (zero-copy, NumPy 2.x safe)
        try:
            frame = np.frombuffer(msg.data, dtype=np.uint8).reshape((msg.height, msg.width, 3))
            if msg.encoding == 'rgb8':
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        except Exception as e:
            self.get_logger().error(f'Failed to decode image frame: {e}')
            return

        vis_frame = frame.copy()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 2. Field Frame Setup (Auto-calibrate or maintain)
        if self.auto_calibrate or self.homography is None:
            detected_pts = self._detect_field_corners(gray)
            if self.src_cam_pts is None:
                self.src_cam_pts = detected_pts
            else:
                # Smooth filter to prevent corner jitter
                self.src_cam_pts = 0.85 * self.src_cam_pts + 0.15 * detected_pts
            self._update_homography()

        # 3. Detect Cubes by Color
        detected_objects = []
        counts = {'red': 0, 'green': 0, 'blue': 0, 'yellow': 0}

        for color_name, ranges in self.color_ranges.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lower, upper in ranges:
                mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower, upper))

            # Morphological noise removal
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.morph_kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.morph_kernel, iterations=1)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if not (self.min_area <= area <= self.max_area):
                    continue

                # Minimum area bounding box (captures rotation of the cube)
                rect = cv2.minAreaRect(cnt)
                (cx, cy), (rw, rh), angle = rect
                if rw <= 0 or rh <= 0:
                    continue

                # Cube geometry filter: aspect ratio should be reasonably square
                aspect = max(rw, rh) / min(rw, rh)
                if aspect > 2.0:
                    continue

                # Filter out the printed green circles if not covered by a cube
                if color_name == 'green':
                    peri = cv2.arcLength(cnt, True)
                    circularity = 4 * np.pi * area / (peri * peri) if peri > 0 else 0
                    # Circular feeder marks have high circularity (>0.75) and lower solidity
                    rect_area = rw * rh
                    extent = area / rect_area if rect_area > 0 else 0
                    if circularity > 0.85 and extent < 0.82:
                        continue

                # Compute Field & Robot coordinates
                (fx, fy), (rx, ry) = self._pixel_to_robot(cx, cy)

                counts[color_name] += 1
                obj_entry = {
                    'color': color_name,
                    'pixel': {'u': int(cx), 'v': int(cy)},
                    'field_mm': {'x': round(fx, 1), 'y': round(fy, 1)},
                    'robot_mm': {'x': round(rx, 1), 'y': round(ry, 1), 'z': self.cube_z},
                    'angle_deg': round(angle, 1),
                    'size_px': [int(rw), int(rh)],
                    'area': int(area)
                }
                detected_objects.append(obj_entry)

                # --- Draw Cube Overlay on vis_frame ---
                box = cv2.boxPoints(rect)
                box = np.intp(box)
                col = self.display_colors[color_name]

                # Draw rotated cube border and center crosshair
                cv2.drawContours(vis_frame, [box], 0, col, 2)
                cv2.drawMarker(vis_frame, (int(cx), int(cy)), col, cv2.MARKER_CROSS, 12, 2)

                # Draw info tag
                label_line1 = f"{color_name.upper()} CUBE"
                label_line2 = f"X:{rx:+.0f} Y:{ry:+.0f} mm"
                label_line3 = f"Rot:{angle:.0f} deg"

                text_x = int(cx) + 15
                text_y = int(cy) - 10
                # Clamp within frame bounds
                text_x = max(10, min(text_x, vis_frame.shape[1] - 140))
                text_y = max(40, min(text_y, vis_frame.shape[0] - 20))

                # Background badge for legibility
                cv2.rectangle(vis_frame, (text_x - 4, text_y - 14), (text_x + 130, text_y + 32), (20, 20, 20), -1)
                cv2.rectangle(vis_frame, (text_x - 4, text_y - 14), (text_x + 130, text_y + 32), col, 1)

                cv2.putText(vis_frame, label_line1, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1)
                cv2.putText(vis_frame, label_line2, (text_x, text_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1)
                cv2.putText(vis_frame, label_line3, (text_x, text_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1)

        # 4. Draw Field Template Frame & Robot Coordinate System
        if self.show_overlay and self.src_cam_pts is not None:
            # Draw Field Border (Cyan)
            field_box = self.src_cam_pts.astype(np.int32)
            cv2.polylines(vis_frame, [field_box], isClosed=True, color=(255, 255, 0), thickness=2)

            corner_names = ['TL (0,0)', 'TR (210,0)', 'BR (210,297)', 'BL (0,297)']
            for i, (px, py) in enumerate(field_box):
                cv2.circle(vis_frame, (px, py), 4, (255, 255, 0), -1)

            # Draw Dobot Base Origin & Coordinate Axes
            p_base = self._field_to_pixel(self.robot_base_x, self.robot_base_y)
            # +X axis: 50mm Forward (towards top of page: fy = robot_base_y - 50)
            p_x_axis = self._field_to_pixel(self.robot_base_x, self.robot_base_y - 50.0)
            # +Y axis: 50mm Left (towards circles: fx = robot_base_x - 50)
            p_y_axis = self._field_to_pixel(self.robot_base_x - 50.0, self.robot_base_y)

            if p_base and p_x_axis and p_y_axis:
                cv2.circle(vis_frame, p_base, 6, (0, 255, 255), -1)
                # +X (Forward) Arrow in RED
                cv2.arrowedLine(vis_frame, p_base, p_x_axis, (0, 0, 255), 2, tipLength=0.2)
                cv2.putText(vis_frame, '+X (Fwd)', (p_x_axis[0] + 5, p_x_axis[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                # +Y (Left) Arrow in GREEN
                cv2.arrowedLine(vis_frame, p_base, p_y_axis, (0, 255, 0), 2, tipLength=0.2)
                cv2.putText(vis_frame, '+Y (Left)', (p_y_axis[0] - 50, p_y_axis[1] + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

            # Draw 3x3 Pallet Area Outline (approx 45mm to 165mm in X, 40mm to 160mm in Y)
            p_grid_tl = self._field_to_pixel(45.0, 40.0)
            p_grid_br = self._field_to_pixel(165.0, 160.0)
            if p_grid_tl and p_grid_br:
                cv2.rectangle(vis_frame, p_grid_tl, p_grid_br, (180, 180, 180), 1, cv2.LINE_AA)
                cv2.putText(vis_frame, 'Pallet Grid', (p_grid_tl[0] + 4, p_grid_tl[1] + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

        # 5. Top HUD Status Banner for Real-Time UI Streaming
        cv2.rectangle(vis_frame, (0, 0), (vis_frame.shape[1], 32), (15, 15, 15), -1)
        hud_text = (
            f"DOBOT TRACKER | Red: {counts['red']} | Green: {counts['green']} | "
            f"Blue: {counts['blue']} | Yellow: {counts['yellow']} | "
            f"Total: {len(detected_objects)}"
        )
        cv2.putText(vis_frame, hud_text, (10, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1)

        # 6. Publish Annotated Real-Time Video Stream
        self.out_image_msg.header.stamp = msg.header.stamp
        self.out_image_msg.height, self.out_image_msg.width, _ = vis_frame.shape
        self.out_image_msg.step = self.out_image_msg.width * 3
        self.out_image_msg.data = vis_frame.tobytes()
        self.pub_annotated_image.publish(self.out_image_msg)

        # 7. Publish Structured JSON Coordinates for UI
        payload = {
            'timestamp': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            'count': len(detected_objects),
            'field_template': {
                'width_mm': self.field_w,
                'height_mm': self.field_h,
                'dobot_base_origin_mm': [self.robot_base_x, self.robot_base_y]
            },
            'objects': detected_objects
        }
        json_msg = String()
        json_msg.data = json.dumps(payload)
        self.pub_objects_json.publish(json_msg)

        # 8. Publish ROS PoseArray (meters in dobot_base frame for RViz / MoveIt)
        pose_array = PoseArray()
        pose_array.header.stamp = msg.header.stamp
        pose_array.header.frame_id = 'dobot_base'

        for obj in detected_objects:
            p = Pose()
            # Convert mm to meters for standard ROS SI units
            p.position.x = obj['robot_mm']['x'] / 1000.0
            p.position.y = obj['robot_mm']['y'] / 1000.0
            p.position.z = obj['robot_mm']['z'] / 1000.0

            # Orientation quaternion around Z axis
            yaw_rad = math.radians(obj['angle_deg'])
            p.orientation.z = math.sin(yaw_rad / 2.0)
            p.orientation.w = math.cos(yaw_rad / 2.0)
            pose_array.poses.append(p)

        self.pub_poses.publish(pose_array)


def main(args=None):
    rclpy.init(args=args)
    node = CubeDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
