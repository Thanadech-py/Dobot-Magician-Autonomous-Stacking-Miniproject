#!/usr/bin/env python3
"""
ROS 2 Node: Dobot Magician Hardware Controller (dobot_v2)
==========================================================
Coordinates DobotDriver hardware communication, MissionExecutor trajectory planning,
and full bidirectional integration with the Dobot_UI interface.

All configurations are loaded from config/dobot_controller.yaml.
"""

import json
import os
import sys
import threading
import yaml

try:
    import rclpy
    from rclpy.node import Node
    from ament_index_python.packages import get_package_share_directory, PackageNotFoundError
    from std_msgs.msg import String
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False
    Node = object
    String = object

from dobot_v2.dobot_driver import DobotDriver
from dobot_v2.mission_executor import MissionExecutor


def load_controller_yaml(logger=None) -> dict:
    """Loads default configuration from config/dobot_controller.yaml with safe fallbacks."""
    candidates = []
    if HAS_ROS2:
        try:
            share = get_package_share_directory("dobot_v2")
            candidates.append(os.path.join(share, "config", "dobot_controller.yaml"))
        except Exception:
            pass

    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.extend([
        os.path.normpath(os.path.join(current_dir, "..", "config", "dobot_controller.yaml")),
        os.path.expanduser("~/dobot_ws/src/dobot_v2/config/dobot_controller.yaml"),
    ])

    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    # Unpack ros__parameters if nested
                    if "dobot_controller" in data and "ros__parameters" in data["dobot_controller"]:
                        return data["dobot_controller"]["ros__parameters"]
                    elif "ros__parameters" in data:
                        return data["ros__parameters"]
                    return data
            except Exception as e:
                if logger:
                    logger.warn(f"Error reading YAML config at {path}: {e}")

    # Fallback built-in defaults
    return {
        "serial_port": "",
        "baudrate": 115200,
        "auto_connect": True,
        "home_on_start": False,
        "velocity": 150.0,
        "acceleration": 150.0,
        "geometry": {
            "hover_z": 80.0,
            "pick_z": 12.5,
            "dropoff_x": 200.0,
            "dropoff_y": 0.0,
            "dropoff_z": 30.0,
            "cube_height": 25.0,
            "calib_x": 150.0,
            "calib_y": 0.0,
            "calib_z": 80.0,
        },
        "effector": {
            "use_suction": True,
            "dwell_grip_sec": 0.35,
            "dwell_release_sec": 0.25,
        },
        "telemetry": {
            "publish_rate_hz": 10.0,
            "cmd_topic": "dobot_ui_cmd",
            "status_topic": "dobot_status",
            "detections_topic": "detected_objects",
        },
    }


class DobotControllerNode(Node):
    """ROS 2 Node controlling the Dobot Magician robotic arm and interfacing with UI."""

    def __init__(self):
        super().__init__("dobot_controller", automatically_declare_parameters_from_overrides=True)
        self.get_logger().info("Initializing DobotControllerNode (dobot_v2)...")

        # 1. Load configuration from YAML
        self.cfg = load_controller_yaml(logger=self.get_logger())

        # 2. Instantiate Driver & Mission Subsystems
        self.driver = DobotDriver(self.cfg, logger_instance=self.get_logger())
        self.mission = MissionExecutor(self.driver, self.cfg, logger_instance=self.get_logger())

        # State tracking
        self._busy = False
        self._last_state = "idle"
        self._last_message = "Ready"
        self._latest_detections = []
        self._lock = threading.Lock()

        # 3. Setup ROS 2 Interfaces
        telem = self.cfg.get("telemetry", {})
        cmd_topic = telem.get("cmd_topic", "dobot_ui_cmd")
        status_topic = telem.get("status_topic", "dobot_status")
        det_topic = telem.get("detections_topic", "detected_objects")
        rate_hz = float(telem.get("publish_rate_hz", 10.0))

        self.pub_status = self.create_publisher(String, status_topic, 10)
        self.sub_cmd = self.create_subscription(String, cmd_topic, self._on_ui_cmd, 10)
        self.sub_detections = self.create_subscription(String, det_topic, self._on_detections, 10)

        # Periodic telemetry broadcast timer
        timer_period = 1.0 / max(1.0, rate_hz)
        self.timer_telemetry = self.create_timer(timer_period, self._on_timer_telemetry)

        # 4. Optional Auto-Connect & Auto-Home on start
        if self.cfg.get("auto_connect", True):
            port = self.cfg.get("serial_port", "")
            home = self.cfg.get("home_on_start", False)
            threading.Thread(target=self._initial_connect, args=(port, home), daemon=True).start()

        self.get_logger().info("DobotControllerNode ready and listening for UI commands.")

    def _initial_connect(self, port: str, home_on_start: bool):
        """Initial connection worker running in background."""
        ok = self.driver.connect(port)
        if ok:
            self._set_state("connected", "Connected to Dobot Magician.")
            if home_on_start:
                self._execute_home()
        else:
            self._set_state("error", "Failed to connect to Dobot. Check USB connection.")

    # -----------------------------------------------------------------------
    # Telemetry and State Management
    # -----------------------------------------------------------------------

    def _set_state(self, state: str, message: str):
        with self._lock:
            self._last_state = state
            self._last_message = message
        self._publish_status(state, message)

    def _publish_status(self, state: str = None, message: str = None):
        """Publishes live status JSON payload to /dobot_status."""
        with self._lock:
            if state is not None:
                self._last_state = state
            if message is not None:
                self._last_message = message
            cur_state = self._last_state
            cur_msg = self._last_message

        x, y, z, r = self.driver.get_pose()
        payload = {
            "state": cur_state.upper(),
            "message": cur_msg,
            "x": round(x, 1),
            "y": round(y, 1),
            "z": round(z, 1),
            "r": round(r, 1),
            "suction": self.driver.suction_on,
            "gripper": self.driver.gripper_closed,
            "connected": self.driver.is_connected,
        }

        msg = String()
        msg.data = json.dumps(payload)
        self.pub_status.publish(msg)

    def _on_timer_telemetry(self):
        """Timer callback publishing live telemetry at configured rate."""
        # Derive state if mission is running
        if self.mission.is_active:
            state = "moving"
        elif self._busy:
            state = "busy"
        elif self.driver.is_connected:
            state = "idle"
        else:
            state = "disconnected"

        with self._lock:
            self._last_state = state

        self._publish_status()

    # -----------------------------------------------------------------------
    # Command Handling from UI (/dobot_ui_cmd)
    # -----------------------------------------------------------------------

    def _on_ui_cmd(self, msg: String):
        """Dispatches commands sent from Dobot_UI."""
        try:
            data = json.loads(msg.data)
        except Exception as e:
            self.get_logger().error(f"Failed to parse UI command JSON: {e}")
            return

        cmd = data.get("cmd", "").strip().lower()
        self.get_logger().info(f"Received UI Command: '{cmd}'")

        if cmd == "connect":
            port = data.get("port", self.cfg.get("serial_port", ""))
            threading.Thread(target=self._cmd_connect, args=(port,), daemon=True).start()

        elif cmd == "home":
            threading.Thread(target=self._execute_home, daemon=True).start()

        elif cmd == "calibrate":
            threading.Thread(target=self._execute_calibrate, daemon=True).start()

        elif cmd == "mission":
            tasks = data.get("tasks", [])
            self._execute_mission(tasks)

        elif cmd == "stop":
            self._execute_stop()

        elif cmd == "jog":
            axis = data.get("axis", "x")
            direction = int(data.get("direction", 1))
            step = float(data.get("step", 10.0))
            threading.Thread(target=self._execute_jog, args=(axis, direction, step), daemon=True).start()

        elif cmd == "move_to":
            x = float(data.get("x", 200.0))
            y = float(data.get("y", 0.0))
            z = float(data.get("z", self.mission.hover_z))
            r = float(data.get("r", 0.0))
            threading.Thread(target=self._execute_move_to, args=(x, y, z, r), daemon=True).start()

        elif cmd == "suction":
            enable = bool(data.get("enable", False))
            self.driver.set_suction(enable)
            self._set_state("idle", f"Suction set to {'ON' if enable else 'OFF'}")

        elif cmd == "gripper":
            grip = bool(data.get("grip", False))
            self.driver.set_gripper(grip)
            self._set_state("idle", f"Gripper set to {'CLOSED' if grip else 'OPEN'}")

        elif cmd == "preset":
            name = str(data.get("name", "hover")).lower()
            threading.Thread(target=self._execute_preset, args=(name,), daemon=True).start()

        else:
            self.get_logger().warn(f"Unknown UI command received: '{cmd}'")

    # -----------------------------------------------------------------------
    # Command Implementations
    # -----------------------------------------------------------------------

    def _cmd_connect(self, port: str):
        self._set_state("moving", "Connecting to Dobot...")
        if self.driver.connect(port):
            self._set_state("connected", "Connected to Dobot Magician.")
        else:
            self._set_state("error", "Connection failed. Check USB serial cable.")

    def _execute_home(self):
        if not self.driver.is_connected:
            self._set_state("error", "Cannot home: Dobot not connected.")
            return
        try:
            self._busy = True
            self._set_state("moving", "Homing Dobot Magician...")
            self.driver.home()
            self._set_state("idle", "Homing complete. Ready.")
        except Exception as e:
            self.get_logger().error(f"Homing error: {e}")
            self._set_state("error", f"Homing error: {e}")
        finally:
            self._busy = False

    def _execute_calibrate(self):
        if not self.driver.is_connected:
            self._set_state("error", "Cannot calibrate: Dobot not connected.")
            return
        try:
            self._busy = True
            self._set_state("moving", "Moving to calibration position...")
            geom = self.cfg.get("geometry", {})
            cx = float(geom.get("calib_x", 150.0))
            cy = float(geom.get("calib_y", 0.0))
            cz = float(geom.get("calib_z", 80.0))
            self.driver.move_to(cx, cy, cz, r=0.0)
            self._set_state("idle", "Calibration position reached.")
        except Exception as e:
            self._set_state("error", str(e))
        finally:
            self._busy = False

    def _execute_mission(self, tasks: list):
        if not self.driver.is_connected:
            self._set_state("error", "Cannot start mission: Dobot not connected.")
            return
        if not tasks:
            self._set_state("error", "Empty mission task list.")
            return

        def on_mission_status(st: str, msg: str):
            self._set_state(st, msg)

        started = self.mission.start_mission(tasks, on_status=on_mission_status)
        if not started:
            self._set_state("error", "Failed to start mission (already running).")

    def _execute_stop(self):
        self.mission.stop()
        self.driver.set_suction(False)
        self._busy = False
        self._set_state("idle", "Emergency Stop: Operations halted.")
        self.get_logger().info("Emergency stop executed.")

    def _execute_jog(self, axis: str, direction: int, step: float):
        if not self.driver.is_connected:
            self._set_state("error", "Cannot jog: Dobot not connected.")
            return
        try:
            self._busy = True
            sign = "+" if direction >= 0 else "-"
            self._set_state("moving", f"Jogging {axis.upper()} {sign}{step}...")
            self.driver.jog(axis, direction, step)
            self._set_state("idle", f"Jogged {axis.upper()} {sign}{step}.")
        except Exception as e:
            self._set_state("error", f"Jog error: {e}")
        finally:
            self._busy = False

    def _execute_move_to(self, x: float, y: float, z: float, r: float):
        if not self.driver.is_connected:
            self._set_state("error", "Cannot move: Dobot not connected.")
            return
        try:
            self._busy = True
            self._set_state("moving", f"Moving to ({x:.1f}, {y:.1f}, {z:.1f})...")
            self.driver.move_to(x, y, z, r)
            self._set_state("idle", "Target reached.")
        except Exception as e:
            self._set_state("error", f"Move error: {e}")
        finally:
            self._busy = False

    def _execute_preset(self, name: str):
        if not self.driver.is_connected:
            self._set_state("error", "Cannot move preset: Dobot not connected.")
            return
        try:
            self._busy = True
            geom = self.cfg.get("geometry", {})
            if name == "home":
                self._execute_home()
                return
            elif name == "hover":
                hz = float(geom.get("hover_z", 80.0))
                self._set_state("moving", "Moving to Hover...")
                self.driver.move_to(200.0, 0.0, hz, r=0.0)
            elif name == "dropoff":
                dx = float(geom.get("dropoff_x", 200.0))
                dy = float(geom.get("dropoff_y", 0.0))
                dz = float(geom.get("dropoff_z", 30.0))
                self._set_state("moving", "Moving to Drop-off...")
                self.driver.move_to(dx, dy, dz, r=0.0)
            elif name == "zero_r":
                x, y, z, _ = self.driver.get_pose()
                self._set_state("moving", "Zeroing wrist rotation...")
                self.driver.move_to(x, y, z, r=0.0)
            self._set_state("idle", f"Preset '{name}' reached.")
        except Exception as e:
            self._set_state("error", f"Preset error: {e}")
        finally:
            self._busy = False

    # -----------------------------------------------------------------------
    # Object Detections (/detected_objects)
    # -----------------------------------------------------------------------

    def _on_detections(self, msg: String):
        try:
            data = json.loads(msg.data)
            self._latest_detections = data.get("objects", [])
        except Exception:
            pass

    def destroy_node(self):
        self.mission.stop()
        self.driver.disconnect()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DobotControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
