"""Low-level hardware driver interface for Dobot Magician using pydobot / pydobot2."""

import logging
import threading
import time

try:
    from pydobot import Dobot
    from pydobot.dobot import DobotException, MODE_PTP
    HAS_PYDOBOT = True
except ImportError:
    try:
        from pydobot import Dobot, MODE_PTP
        from pydobot.dobot import DobotException
        HAS_PYDOBOT = True
    except ImportError:
        try:
            from pydobot2 import Dobot
            from pydobot2.dobot import DobotException, MODE_PTP
            HAS_PYDOBOT = True
        except ImportError:
            HAS_PYDOBOT = False
            Dobot = None
            MODE_PTP = None

            class DobotException(Exception):
                """Fallback exception when pydobot is not installed."""
                pass

logger = logging.getLogger("dobot_v2.driver")


class DobotDriver:
    """Thread-safe hardware driver wrapper for Dobot Magician."""

    def __init__(self, config: dict, logger_instance=None):
        self.log = logger_instance or logger
        self.cfg = config
        self._lock = threading.Lock()
        self._dobot = None
        self._connected = False

        # Limits & parameters
        limits = self.cfg.get("limits", {})
        self.min_x = float(limits.get("min_x", 100.0))
        self.max_x = float(limits.get("max_x", 330.0))
        self.min_y = float(limits.get("min_y", -250.0))
        self.max_y = float(limits.get("max_y", 250.0))
        self.min_z = float(limits.get("min_z", -60.0))
        self.max_z = float(limits.get("max_z", 160.0))
        self.min_r = float(limits.get("min_r", -180.0))
        self.max_r = float(limits.get("max_r", 180.0))

        self.vel = float(self.cfg.get("velocity", 150.0))
        self.acc = float(self.cfg.get("acceleration", 150.0))

        # Simulated / internal pose tracking
        self.cur_x = 200.0
        self.cur_y = 0.0
        self.cur_z = 80.0
        self.cur_r = 0.0
        self.suction_on = False
        self.gripper_closed = False

    @property
    def is_connected(self) -> bool:
        return self._connected and (self._dobot is not None or not HAS_PYDOBOT)

    def connect(self, port: str = "") -> bool:
        """Connects to the Dobot Magician serial port with retries."""
        with self._lock:
            if not HAS_PYDOBOT:
                self.log.warn("pydobot2 is not installed. Running in simulation / mock driver mode.")
                self._connected = True
                return True

            retries = int(self.cfg.get("reconnect_attempts", 3))
            delay = float(self.cfg.get("reconnect_delay_sec", 2.0))

            for attempt in range(1, retries + 1):
                try:
                    self.log.info(
                        f"Connecting to Dobot Magician (attempt {attempt}/{retries})"
                        f"{f' on port {port}' if port else ' (auto-detect)'}..."
                    )
                    self._dobot = Dobot(port=port if port else None)
                    self._dobot.speed(velocity=self.vel, acceleration=self.acc)
                    self._connected = True
                    self.log.info("Successfully connected to Dobot Magician!")
                    self._refresh_pose_locked()
                    return True
                except DobotException as e:
                    self.log.warn(f"Connection attempt {attempt} failed: {e}")
                    time.sleep(delay)
                except Exception as e:
                    self.log.error(f"Unexpected connection error: {e}")
                    time.sleep(delay)

            self.log.error("Failed to connect to Dobot Magician after all retries.")
            self._connected = False
            return False

    def disconnect(self):
        """Safely disconnects from Dobot."""
        with self._lock:
            if self._dobot is not None:
                try:
                    self.set_suction(False)
                except Exception:
                    pass
                try:
                    self._dobot.close()
                except Exception:
                    pass
                self._dobot = None
            self._connected = False
            self.log.info("Disconnected from Dobot Magician.")

    def home(self) -> bool:
        """Executes homing sequence."""
        with self._lock:
            if not self.is_connected:
                raise RuntimeError("Not connected to Dobot Magician.")
            if self._dobot is not None:
                self.log.info("Starting hardware homing sequence...")
                self._dobot.wait_for_cmd(self._dobot.home())
                self._refresh_pose_locked()
                self.log.info("Homing sequence complete.")
            else:
                self.cur_x, self.cur_y, self.cur_z, self.cur_r = 200.0, 0.0, 80.0, 0.0
            return True

    def clamp_coordinates(self, x: float, y: float, z: float, r: float) -> tuple[float, float, float, float]:
        """Clamps coordinates to safe software limits."""
        cx = max(self.min_x, min(self.max_x, float(x)))
        cy = max(self.min_y, min(self.max_y, float(y)))
        cz = max(self.min_z, min(self.max_z, float(z)))
        cr = max(self.min_r, min(self.max_r, float(r)))
        return cx, cy, cz, cr

    def move_to(self, x: float, y: float, z: float, r: float = 0.0, linear: bool = False) -> bool:
        """Moves end-effector to Cartesian target coordinates (PTP or Linear)."""
        with self._lock:
            if not self.is_connected:
                raise RuntimeError("Not connected to Dobot Magician.")

            cx, cy, cz, cr = self.clamp_coordinates(x, y, z, r)
            if self._dobot is not None:
                mode = MODE_PTP.MOVL_XYZ if linear else MODE_PTP.MOVJ_XYZ
                self._dobot.wait_for_cmd(self._dobot.move_to(cx, cy, cz, cr, mode))
                self.cur_x, self.cur_y, self.cur_z, self.cur_r = cx, cy, cz, cr
            else:
                self.cur_x, self.cur_y, self.cur_z, self.cur_r = cx, cy, cz, cr
                time.sleep(0.05)
            return True

    def jog(self, axis: str, direction: int, step: float) -> tuple[float, float, float, float]:
        """Performs a relative jog movement along the specified axis."""
        axis = axis.lower()
        sign = 1 if direction >= 0 else -1
        delta = sign * abs(float(step))

        cur_x, cur_y, cur_z, cur_r = self.get_pose()
        tx, ty, tz, tr = cur_x, cur_y, cur_z, cur_r

        if axis == "x":
            tx += delta
        elif axis == "y":
            ty += delta
        elif axis == "z":
            tz += delta
        elif axis == "r":
            tr += delta
        else:
            raise ValueError(f"Invalid jog axis '{axis}'. Must be 'x', 'y', 'z', or 'r'.")

        self.move_to(tx, ty, tz, tr, linear=False)
        return self.get_pose()

    def set_suction(self, enable: bool):
        """Controls Dobot air suction pump and valve."""
        with self._lock:
            self.suction_on = bool(enable)
            if self._dobot is not None:
                self._dobot.wait_for_cmd(self._dobot.suck(self.suction_on))
            self.log.info(f"Suction set to {'ON' if self.suction_on else 'OFF'}")

    def set_gripper(self, grip: bool):
        """Controls Dobot pneumatic/servo gripper."""
        with self._lock:
            self.gripper_closed = bool(grip)
            if self._dobot is not None:
                self._dobot.wait_for_cmd(self._dobot.grip(self.gripper_closed))
            self.log.info(f"Gripper set to {'CLOSED' if self.gripper_closed else 'OPEN'}")

    def get_pose(self) -> tuple[float, float, float, float]:
        """Returns the current Cartesian position (X, Y, Z, R) in mm/deg."""
        with self._lock:
            self._refresh_pose_locked()
            return self.cur_x, self.cur_y, self.cur_z, self.cur_r

    def _refresh_pose_locked(self):
        """Reads hardware pose from Dobot Magician."""
        if self._dobot is None:
            return
        try:
            if hasattr(self._dobot, "get_pose"):
                pose = self._dobot.get_pose()
                if hasattr(pose, "position"):
                    self.cur_x = float(pose.position.x)
                    self.cur_y = float(pose.position.y)
                    self.cur_z = float(pose.position.z)
                    self.cur_r = float(pose.position.r)
                elif isinstance(pose, (tuple, list)):
                    self.cur_x = float(pose[0])
                    self.cur_y = float(pose[1])
                    self.cur_z = float(pose[2])
                    self.cur_r = float(pose[3])
            elif hasattr(self._dobot, "pose"):
                pose = self._dobot.pose()
                self.cur_x = float(pose[0])
                self.cur_y = float(pose[1])
                self.cur_z = float(pose[2])
                self.cur_r = float(pose[3])
        except Exception as e:
            self.log.debug(f"Failed to refresh pose: {e}")
