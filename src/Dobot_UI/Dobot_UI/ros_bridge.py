"""ROS 2 Node and PyQt Thread bridge."""

import json
import os
import shutil
import subprocess
import sys
import time
import cv2
import numpy as np

try:
    from PyQt6.QtCore import QThread, pyqtSignal
    from PyQt6.QtGui import QImage
except ImportError:
    from PyQt5.QtCore import QThread, pyqtSignal
    from PyQt5.QtGui import QImage

try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import CompressedImage
    from std_msgs.msg import String
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False
    Node = object

try:
    from .config import TOPICS, DETECTION
except (ImportError, ValueError):
    from Dobot_UI.config import TOPICS, DETECTION


class RosBridge(QThread):
    """Bridges ROS 2 subscriptions and publishers with Qt signals."""
    image_received      = pyqtSignal(QImage, float)
    status_received     = pyqtSignal(dict)
    detections_received = pyqtSignal(dict)
    log_message         = pyqtSignal(str, str)

    def __init__(self, mock_mode=False, parent=None):
        super().__init__(parent)
        self.mock_mode = mock_mode or not HAS_ROS2
        self._running = True
        self.node = None
        self.pub_cmd = None
        self._fps_count = 0
        self._last_time = time.time()
        self.fps = 0.0

    def run(self):
        if not self.mock_mode and HAS_ROS2:
            try:
                if not rclpy.ok():
                    rclpy.init()
                self.node = Node("dobot_ui_node")

                # Declare parameters so launch file or ROS parameter overrides work
                self.node.declare_parameter("image_compressed_topic", TOPICS.get("image_comp", "detected_objects_image/compressed"))
                self.node.declare_parameter("image_topic",            TOPICS.get("image_raw",  "detected_objects_image"))
                self.node.declare_parameter("status_topic",           TOPICS.get("status",     "dobot_status"))
                self.node.declare_parameter("detections_topic",       TOPICS.get("detections", "detected_objects"))
                self.node.declare_parameter("command_topic",          TOPICS.get("command",    "dobot_ui_cmd"))
                self.node.declare_parameter("mock_mode",              False)

                mock_param = self.node.get_parameter("mock_mode").get_parameter_value().bool_value
                if mock_param:
                    self.mock_mode = True
                    self.log_message.emit("WARN", "Running in Simulation / Mock Mode (via ROS parameter).")
                    self._run_mock()
                    return

                comp_topic = self.node.get_parameter("image_compressed_topic").get_parameter_value().string_value or TOPICS["image_comp"]
                status_topic = self.node.get_parameter("status_topic").get_parameter_value().string_value or TOPICS["status"]
                det_topic = self.node.get_parameter("detections_topic").get_parameter_value().string_value or TOPICS["detections"]
                cmd_topic = self.node.get_parameter("command_topic").get_parameter_value().string_value or TOPICS["command"]

                self.node.create_subscription(CompressedImage, comp_topic, self._on_comp_img, 1)
                self.node.create_subscription(String, status_topic, self._on_status, 10)
                self.node.create_subscription(String, det_topic, self._on_detections, 10)
                self.pub_cmd = self.node.create_publisher(String, cmd_topic, 10)
                self.log_message.emit("INFO", "Connected to ROS 2 topics.")

                while self._running and rclpy.ok():
                    rclpy.spin_once(self.node, timeout_sec=0.05)
            except Exception as e:
                self.log_message.emit("ERROR", f"ROS 2 error: {e}")
            finally:
                if self.node:
                    self.node.destroy_node()
        else:
            self.log_message.emit("WARN", "Running in Simulation / Mock Mode.")
            self._run_mock()

    def _on_comp_img(self, msg):
        try:
            arr = np.frombuffer(msg.data, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                self._emit_qimage(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        except Exception:
            pass

    def _emit_qimage(self, rgb):
        self._fps_count += 1
        now = time.time()
        if now - self._last_time >= 1.0:
            self.fps = self._fps_count / (now - self._last_time)
            self._fps_count = 0
            self._last_time = now
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        self.image_received.emit(qimg, self.fps)

    def _on_status(self, msg):
        try:
            self.status_received.emit(json.loads(msg.data))
        except Exception:
            pass

    def _on_detections(self, msg):
        try:
            self.detections_received.emit(json.loads(msg.data))
        except Exception:
            pass

    def send_cmd(self, payload: dict):
        """Sends command dictionary as JSON string to the command topic."""
        cmd_str = json.dumps(payload)
        if not self.mock_mode and self.pub_cmd:
            msg = String()
            msg.data = cmd_str
            self.pub_cmd.publish(msg)
            self.log_message.emit("INFO", f"Sent command: {payload.get('cmd')}")
        else:
            self.log_message.emit("INFO", f"[MOCK] Sent command: {payload.get('cmd')}")

    def restart_detection_node(self):
        """Closes any running detection node process and opens it again."""
        self.log_message.emit("WARN", "Closing detection node process...")
        node_name = DETECTION.get("ros2_node", "detection_node")
        pkg_name = DETECTION.get("ros2_package", "dobot_v2")
        exe_path = DETECTION.get("installed_exe", "/home/thxncdzch/dobot_ws/install/dobot_v2/lib/dobot_v2/detection_node")
        src_script = DETECTION.get("src_script", "/home/thxncdzch/dobot_ws/src/dobot_v2/dobot_v2/detection_node.py")
        delay = float(DETECTION.get("restart_delay_sec", 0.5))

        try:
            subprocess.run(["pkill", "-f", node_name], check=False)
        except Exception as e:
            self.log_message.emit("WARN", f"Process kill error: {e}")

        time.sleep(delay)

        # Select launch command (ros2 run > installed exe > raw python script)
        if shutil.which("ros2"):
            cmd = ["ros2", "run", pkg_name, node_name]
        elif os.path.isfile(exe_path) and os.access(exe_path, os.X_OK):
            cmd = [exe_path]
        else:
            cmd = [sys.executable, src_script]

        try:
            proc = subprocess.Popen(
                cmd,
                env=os.environ.copy(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.log_message.emit("SUCCESS", f"Started detection node (PID: {proc.pid})")
        except Exception as e:
            self.log_message.emit("ERROR", f"Failed to start detection node: {e}")

        # Publish reset_grid if ROS node is live
        try:
            if self.node:
                reset_topic = TOPICS.get("reset_grid", "reset_grid")
                pub = self.node.create_publisher(String, reset_topic, 10)
                msg = String()
                msg.data = "reset"
                pub.publish(msg)
        except Exception:
            pass

    def stop(self):
        self._running = False
        self.wait(500)

    def _run_mock(self):
        """Placeholder frame generator for headless/mock testing."""
        w, h = 640, 480
        while self._running:
            frame = np.full((h, w, 3), 30, dtype=np.uint8)
            cv2.rectangle(frame, (170, 90), (470, 390), (160, 160, 160), 2)
            cv2.putText(frame, "SIMULATED VISION FEED", (180, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (56, 189, 248), 2)
            self._emit_qimage(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            time.sleep(0.1)
