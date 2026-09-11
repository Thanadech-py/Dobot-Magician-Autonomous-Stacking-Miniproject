#!/usr/bin/env python3
"""
ROS 2 Node: Real-Time Field Grid Tracker & Cube Detector for Dobot.

All configuration parameters and defaults are loaded directly from config/detection_node.yaml.

Subsystems:
  - dobot_v2.transforms:     Coordinate transformations & cell math
  - dobot_v2.grid_detector: Pallet contour detection, verification & locking
  - dobot_v2.cube_detector: Multi-color cube detection & geometric filtering
  - dobot_v2.visualizer:    Debug HUD and visual overlays
"""

import os
import time
import json
import yaml
import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from ament_index_python.packages import get_package_share_directory, PackageNotFoundError
from sensor_msgs.msg import Image, CompressedImage, CameraInfo
from geometry_msgs.msg import PoseArray, Pose
from std_msgs.msg import String
from cv_bridge import CvBridge

from dobot_v2.transforms import FieldTransform
from dobot_v2.grid_detector import GridDetector
from dobot_v2.cube_detector import CubeDetector
from dobot_v2.visualizer import DetectionVisualizer


def load_yaml_config(logger=None) -> dict:
    """Loads default configuration directly from config/detection_node.yaml."""
    candidates = []
    try:
        candidates.append(os.path.join(get_package_share_directory('dobot_v2'), 'config', 'detection_node.yaml'))
    except (PackageNotFoundError, Exception):
        pass

    candidates.extend([
        os.path.expanduser('~/dobot_ws/src/dobot_v2/config/detection_node.yaml'),
        os.path.join(os.path.dirname(__file__), '..', 'config', 'detection_node.yaml'),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'dobot_v2', 'config', 'detection_node.yaml'),
    ])

    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(os.path.realpath(path), 'r') as f:
                    raw = yaml.safe_load(f)
                for root in ['/**', 'detection_node']:
                    if root in raw and 'ros__parameters' in raw[root]:
                        if logger:
                            logger.info(f'Loaded parameter configuration from: {path}')
                        return raw[root]['ros__parameters']
                if 'ros__parameters' in raw:
                    return raw['ros__parameters']
                return raw
            except Exception as e:
                if logger:
                    logger.warn(f'Failed to read {path}: {e}')
    return {}


class DetectionNode(Node):
    """Lean ROS 2 Detection Node orchestrating vision pipelines and ROS interfaces."""

    def __init__(self):
        super().__init__(
            'detection_node',
            automatically_declare_parameters_from_overrides=True
        )
        self.bridge = CvBridge()
        self.last_proc_time = 0.0

        # 1. Load Parameters from config/detection_node.yaml
        self.cfg = self._load_all_parameters()
        self.min_frame_interval = 1.0 / max(1.0, float(self.cfg.get('publish_rate', 30.0)))

        # 2. Initialize Subsystems
        self.transform = FieldTransform(self.cfg)
        self.grid_detector = GridDetector(self.cfg, logger=self.get_logger())
        self.cube_detector = CubeDetector(self.cfg)

        if self.grid_detector.grid_corners is not None:
            self.transform.update_corners(self.grid_detector.grid_corners)

        # 3. Setup ROS Interfaces
        self._init_ros_communication()
        self.get_logger().info('DetectionNode initialized cleanly from config/detection_node.yaml.')

    def _load_all_parameters(self) -> dict:
        yaml_defaults = load_yaml_config(logger=self.get_logger())
        cfg = {}

        # Declare any parameter from YAML if not already provided by launch overrides
        for k, v in yaml_defaults.items():
            if not self.has_parameter(k):
                self.declare_parameter(k, v)
            val = self.get_parameter(k).value
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], (int, float)):
                cfg[k] = [float(x) for x in val]
            else:
                cfg[k] = val

        # Format feeders
        cfg['feeder_positions'] = [
            {'id': i, 'x': cfg[f'feeder_{i}'][0], 'y': cfg[f'feeder_{i}'][1], 'radius': cfg[f'feeder_{i}'][2]}
            for i in range(1, 5) if f'feeder_{i}' in cfg
        ]
        return cfg

    def _init_ros_communication(self):
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST, depth=1)

        img_topic = self.cfg.get('image_topic', '/image_raw/compressed')
        if 'compressed' in img_topic.lower():
            self.create_subscription(CompressedImage, img_topic, self._on_compressed_img, qos)
        else:
            self.create_subscription(Image, img_topic, self._on_raw_img, qos)

        self.create_subscription(CameraInfo, self.cfg.get('camera_info_topic', '/camera_info'), lambda _: None, 10)

        # Control topics
        self.create_subscription(String, 'reset_grid', self._on_reset_grid, 10)
        self.create_subscription(String, 'lock_grid', self._on_lock_grid, 10)
        self.create_subscription(String, 'unlock_grid', self._on_unlock_grid, 10)
        self.create_subscription(String, 'set_grid_corners', self._on_set_corners, 10)

        # Output publishers
        self.pub_comp = self.create_publisher(CompressedImage, 'detected_objects_image/compressed', 10)
        self.pub_raw = self.create_publisher(Image, 'detected_objects_image', 10) if self.cfg.get('publish_raw_image', True) else None
        self.pub_json = self.create_publisher(String, 'detected_objects', 10)
        self.pub_poses_robot = self.create_publisher(PoseArray, 'detected_objects_poses', 10)
        self.pub_poses_grid = self.create_publisher(PoseArray, 'grid_local_poses', 10)

    # -------------------------------------------------------------------------
    # Frame Ingestion & Throttling
    # -------------------------------------------------------------------------

    def _on_compressed_img(self, msg: CompressedImage):
        if self._should_throttle():
            return
        frame = cv2.imdecode(np.frombuffer(msg.data, np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
            self._process(frame, msg.header)

    def _on_raw_img(self, msg: Image):
        if self._should_throttle():
            return
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        if frame is not None:
            self._process(frame, msg.header)

    def _should_throttle(self) -> bool:
        now = time.time()
        if (now - self.last_proc_time) < self.min_frame_interval:
            return True
        self.last_proc_time = now
        return False

    # -------------------------------------------------------------------------
    # Main Pipeline & Demand-Driven Publishing
    # -------------------------------------------------------------------------

    def _process(self, frame: np.ndarray, header):
        try:
            # 1. Pallet Grid Detection & Homography Update
            corners = self.grid_detector.detect(frame)
            if corners is not None and not np.array_equal(corners, self.transform.dst_grid_pts):
                self.transform.update_corners(corners)

            # 2. Cube Detection
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            detected_objects, counts = self.cube_detector.detect(hsv, self.transform)

            # 3. Publish Telemetry & Poses
            self._publish_data(header, detected_objects, counts)

            # 4. On-Demand Visual Overlay (Bypass when no client is subscribed -> Saves 50%+ CPU)
            has_subscribers = (
                self.pub_comp.get_subscription_count() > 0 or
                (self.pub_raw is not None and self.pub_raw.get_subscription_count() > 0)
            )
            if self.cfg.get('show_overlay', True) and has_subscribers:
                pct = int(min(100, (self.grid_detector.stable_counter / max(1, self.grid_detector.lock_threshold)) * 100))
                vis = DetectionVisualizer.draw(
                    frame, self.transform, corners, detected_objects, counts,
                    self.grid_detector.is_locked, pct
                )
                self._publish_images(vis, header)
        except Exception as e:
            self.get_logger().error(f'Error in _process: {e}')

    def _publish_data(self, header, detected_objects: list, counts: dict):
        try:
            t_sec = header.stamp.sec + header.stamp.nanosec * 1e-9
            payload = {
                'timestamp': t_sec,
                'grid_locked': bool(self.grid_detector.is_locked),
                'counts': counts,
                'total_objects': len(detected_objects),
                'objects': detected_objects
            }

            def _json_default(obj):
                if hasattr(obj, 'tolist'):
                    return obj.tolist()
                if isinstance(obj, (np.floating, np.float32, np.float64)):
                    return float(obj)
                if isinstance(obj, (np.integer, np.int32, np.int64)):
                    return int(obj)
                return str(obj)

            json_str = json.dumps(payload, default=_json_default)
            self.pub_json.publish(String(data=json_str))

            pr_msg = PoseArray(header=header)
            pr_msg.header.frame_id = 'dobot_base'
            pg_msg = PoseArray(header=header)
            pg_msg.header.frame_id = 'grid_frame'

            for obj in detected_objects:
                pr = Pose()
                pr.position.x = float(obj['robot_mm']['x'])
                pr.position.y = float(obj['robot_mm']['y'])
                pr.position.z = float(obj['robot_mm']['z'])
                pr_msg.poses.append(pr)

                pg = Pose()
                pg.position.x = float(obj['grid_local_mm']['x'])
                pg.position.y = float(obj['grid_local_mm']['y'])
                pg.position.z = float(obj['robot_mm']['z'])
                pg_msg.poses.append(pg)

            self.pub_poses_robot.publish(pr_msg)
            self.pub_poses_grid.publish(pg_msg)
        except Exception as e:
            self.get_logger().error(f'Failed to publish telemetry/poses: {e}')

    def _publish_images(self, vis: np.ndarray, header):
        if self.pub_comp.get_subscription_count() > 0:
            success, enc = cv2.imencode('.jpg', vis, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if success:
                msg = CompressedImage(header=header, format='jpeg', data=enc.tobytes())
                self.pub_comp.publish(msg)

        if self.pub_raw and self.pub_raw.get_subscription_count() > 0:
            msg = self.bridge.cv2_to_imgmsg(vis, encoding='bgr8')
            msg.header = header
            self.pub_raw.publish(msg)

    # -------------------------------------------------------------------------
    # Dynamic Grid Control Callbacks
    # -------------------------------------------------------------------------

    def _on_reset_grid(self, _: String):
        self.grid_detector.reset()
        self.transform.homography = None
        self.get_logger().info('Grid tracking reset.')

    def _on_lock_grid(self, _: String):
        if self.grid_detector.lock():
            self.get_logger().info('Grid tracking manually locked.')
            self.grid_detector.save_corners_to_yaml()

    def _on_unlock_grid(self, _: String):
        self.grid_detector.unlock()
        self.get_logger().info('Grid tracking unlocked.')

    def _on_set_corners(self, msg: String):
        try:
            pts = np.array(json.loads(msg.data), dtype=np.float32).reshape((4, 2))
            self.grid_detector.set_manual_corners(pts)
            self.transform.update_corners(self.grid_detector.grid_corners)
            self.get_logger().info(f'Corners set: {pts.tolist()}')
            self.grid_detector.save_corners_to_yaml()
        except Exception as e:
            self.get_logger().error(f'Failed to set corners: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = DetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()