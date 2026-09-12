#!/usr/bin/env python3
"""
ROS 2 Node: Dobot Magician Controller
=======================================
Subscribes to /detected_objects (JSON from cube_detector node) and moves the
Dobot Magician arm to pick up the detected colored cubes using pydobot2.

Pick sequence for each cube:
  1. Move ABOVE the cube at a configurable hover Z height
  2. Enable suction / gripper
  3. Descend to the cube Z (pick Z)
  4. Wait briefly, then rise back to hover Z
  5. Move to the drop-off position and release
  6. Return to home position
  7. Repeat for next cube

Subscribes:
  - /detected_objects  (std_msgs/msg/String)  – JSON from cube_detector node

Publishes:
  - /dobot_status      (std_msgs/msg/String)  – JSON status / feedback

Parameters (all tunable via YAML / launch args):
  - serial_port        (str)   : Dobot serial port, e.g. '/dev/ttyUSB0'. Empty = auto-detect.
  - velocity           (float) : PTP velocity  (mm/s), default 150
  - acceleration       (float) : PTP acceleration (mm/s²), default 150
  - hover_z            (float) : Z height when travelling above objects (mm), default 80.0
  - pick_z             (float) : Z height to descend to for picking (mm), default 12.5
  - dropoff_x          (float) : Drop-off X in robot frame (mm), default 200.0
  - dropoff_y          (float) : Drop-off Y in robot frame (mm), default  0.0
  - dropoff_z          (float) : Drop-off Z in robot frame (mm), default 30.0
  - pick_color         (str)   : Which color cube to pick ('all', 'red', 'green', 'blue', 'yellow')
  - use_suction        (bool)  : True = suction cup, False = gripper
  - min_move_dist      (float) : Minimum XY distance change (mm) to trigger a move
  - home_on_start      (bool)  : Whether to home the robot on startup
  - target_frame_id    (str)   : Expected frame_id in pose array (informational)
"""

import json
import math
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import String

try:
    from pydobot import Dobot, MODE_PTP
    from pydobot.dobot import DobotException
except ImportError:
    raise ImportError(
        "pydobot2 is required. Install it with:\n"
        "  pip install pydobot2"
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _dist2d(x1, y1, x2, y2) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class DobotControllerNode(Node):

    def __init__(self):
        super().__init__('dobot_controller_node')

        # ---- Declare parameters ----
        self.declare_parameter('serial_port',    '')
        self.declare_parameter('velocity',       150.0)
        self.declare_parameter('acceleration',   150.0)
        self.declare_parameter('hover_z',        80.0)
        self.declare_parameter('pick_z',         12.5)
        self.declare_parameter('dropoff_x',      200.0)
        self.declare_parameter('dropoff_y',        0.0)
        self.declare_parameter('dropoff_z',       30.0)
        self.declare_parameter('pick_color',     'all')
        self.declare_parameter('use_suction',    True)
        self.declare_parameter('min_move_dist',   5.0)
        self.declare_parameter('home_on_start',  True)
        self.declare_parameter('target_frame_id','dobot_base')

        # ---- Read parameters ----
        port          = self.get_parameter('serial_port').value.strip()
        self.vel      = float(self.get_parameter('velocity').value)
        self.acc      = float(self.get_parameter('acceleration').value)
        self.hover_z  = float(self.get_parameter('hover_z').value)
        self.pick_z   = float(self.get_parameter('pick_z').value)
        self.drop_x   = float(self.get_parameter('dropoff_x').value)
        self.drop_y   = float(self.get_parameter('dropoff_y').value)
        self.drop_z   = float(self.get_parameter('dropoff_z').value)
        self.pick_col = self.get_parameter('pick_color').value.lower().strip()
        self.suction  = bool(self.get_parameter('use_suction').value)
        self.min_dist = float(self.get_parameter('min_move_dist').value)
        home_on_start = bool(self.get_parameter('home_on_start').value)

        # ---- State ----
        self._last_target = (None, None)   # (x, y) of last sent pick target
        self._busy        = False          # True while executing a pick-place cycle
        self._lock        = threading.Lock()
        self._dobot       = None

        # ---- Publisher: status feedback ----
        self.pub_status = self.create_publisher(String, 'dobot_status', 10)

        # ---- Connect to Dobot ----
        self._connect_dobot(port, home_on_start)

        # ---- Subscriber: detected objects (subscribe after robot is ready) ----
        self.sub_objects = self.create_subscription(
            String,
            'detected_objects',
            self._objects_callback,
            10
        )

        # ---- Subscriber: UI commands from dobot_ui node ----
        self.sub_ui_cmd = self.create_subscription(
            String,
            'dobot_ui_cmd',
            self._ui_cmd_callback,
            10
        )

        # Mission queue from UI (ordered list of tasks)
        self._mission_tasks: list[dict] = []   # [{color, index, row, col}, ...]
        self._mission_active = False
        self._mission_task_idx = 0

        self.get_logger().info(
            f'DobotControllerNode ready. pick_color={self.pick_col!r}, '
            f'suction={self.suction}, hover_z={self.hover_z}, pick_z={self.pick_z}'
        )


    # -----------------------------------------------------------------------
    # Connection
    # -----------------------------------------------------------------------

    def _connect_dobot(self, port: str, home_on_start: bool):
        """Connects to the Dobot arm, retrying up to 3 times."""
        for attempt in range(1, 4):
            try:
                self.get_logger().info(
                    f'Connecting to Dobot (attempt {attempt}/3) ...'
                    + (f' port={port!r}' if port else ' (auto-detect)')
                )
                self._dobot = Dobot(port=port if port else None)
                self._dobot.speed(velocity=self.vel, acceleration=self.acc)
                self.get_logger().info('Dobot connected!')

                if home_on_start:
                    self.get_logger().info('Homing Dobot...')
                    self._dobot.wait_for_cmd(self._dobot.home())
                    self.get_logger().info('Homing complete.')

                self._publish_status('connected', 'Dobot connected and ready.')
                return

            except DobotException as e:
                self.get_logger().error(f'Connection attempt {attempt} failed: {e}')
                time.sleep(2.0)

        self.get_logger().fatal(
            'Could not connect to Dobot after 3 attempts. '
            'Check USB cable and serial port permissions (add user to dialout group).'
        )
        self._publish_status('error', 'Failed to connect to Dobot.')

    # -----------------------------------------------------------------------
    # Subscriber callback
    # -----------------------------------------------------------------------

    def _objects_callback(self, msg: String):
        """Receives the JSON from cube_detector and decides whether to pick."""
        if self._dobot is None:
            return  # No connection yet

        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON decode error: {e}')
            return

        objects = payload.get('objects', [])
        if not objects:
            return

        # ── Mission mode: pick in order defined by the UI ──────────────────
        with self._lock:
            mission_active = self._mission_active
            task_idx       = self._mission_task_idx
            mission_tasks  = self._mission_tasks

        if mission_active:
            if task_idx >= len(mission_tasks):
                # All tasks done
                with self._lock:
                    self._mission_active = False
                self._publish_status('idle', 'Mission complete! All cubes stacked.')
                self.get_logger().info('Mission complete.')
                return

            current_task  = mission_tasks[task_idx]
            wanted_color  = current_task['color']
            stack_number  = task_idx          # 0-based: how many cubes already stacked
            cube_h        = self.cube_z       # half-height used as increment

            # Find a detection matching the wanted color
            candidates = [o for o in objects if o['color'] == wanted_color]
            if not candidates:
                return   # Colour not visible yet — wait for next frame

            target = max(candidates, key=lambda o: o['area'])
            rx = float(target['robot_mm']['x'])
            ry = float(target['robot_mm']['y'])
            rz = float(target['robot_mm']['z'])

            # Stack Z: raise drop point by full cube height per stacked cube
            # (cube_z is half-height, so full height = 2 * cube_z)
            stacked_drop_z = self.drop_z + stack_number * (cube_h * 2.0)

            with self._lock:
                if self._busy:
                    return
                lx, ly = self._last_target
                if lx is not None and _dist2d(rx, ry, lx, ly) < self.min_dist:
                    return
                self._busy = True
                self._last_target = (rx, ry)
                self._mission_task_idx += 1   # advance before thread starts

            self.get_logger().info(
                f'Mission task {task_idx + 1}/{len(mission_tasks)}: '
                f'{wanted_color} → stack Z={stacked_drop_z:.1f} mm'
            )
            t = threading.Thread(
                target=self._pick_and_place,
                args=(rx, ry, rz, wanted_color, stacked_drop_z),
                daemon=True
            )
            t.start()
            return

        # ── Freerun mode: original behaviour ──────────────────────────────
        if self.pick_col != 'all':
            candidates = [o for o in objects if o['color'] == self.pick_col]
        else:
            candidates = objects

        if not candidates:
            return

        target = max(candidates, key=lambda o: o['area'])
        rx = float(target['robot_mm']['x'])
        ry = float(target['robot_mm']['y'])
        rz = float(target['robot_mm']['z'])
        color = target['color']

        with self._lock:
            if self._busy:
                return
            lx, ly = self._last_target
            if lx is not None and _dist2d(rx, ry, lx, ly) < self.min_dist:
                return
            self._busy = True
            self._last_target = (rx, ry)

        t = threading.Thread(
            target=self._pick_and_place,
            args=(rx, ry, rz, color),
            daemon=True
        )
        t.start()

    # -----------------------------------------------------------------------
    # UI Command callback  (from /dobot_ui_cmd)
    # -----------------------------------------------------------------------

    def _ui_cmd_callback(self, msg: String):
        """Handles commands published by the UI node."""
        try:
            cmd_data = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'UI cmd JSON error: {e}')
            return

        cmd = cmd_data.get('cmd', '')
        self.get_logger().info(f'UI command received: {cmd}')

        if cmd == 'home':
            if self._dobot is None:
                self._publish_status('error', 'Not connected')
                return
            with self._lock:
                if self._busy:
                    self._publish_status('error', 'Busy — cannot home now')
                    return
                self._busy = True
            threading.Thread(target=self._do_home, daemon=True).start()

        elif cmd == 'calibrate':
            if self._dobot is None:
                self._publish_status('error', 'Not connected')
                return
            with self._lock:
                if self._busy:
                    self._publish_status('error', 'Busy — cannot calibrate now')
                    return
                self._busy = True
            threading.Thread(target=self._do_calibrate, daemon=True).start()

        elif cmd == 'connect':
            port = self.get_parameter('serial_port').value.strip()
            threading.Thread(
                target=self._connect_dobot, args=(port, False), daemon=True
            ).start()

        elif cmd == 'mission':
            tasks = cmd_data.get('tasks', [])
            if not tasks:
                self._publish_status('error', 'Empty mission received')
                return
            with self._lock:
                if self._busy:
                    self._publish_status('error', 'Busy — cannot start mission now')
                    return
                self._mission_tasks = sorted(tasks, key=lambda t: t['index'])
                self._mission_active = True
                self._mission_task_idx = 0
                # Set pick_color to 'all' so the objects callback can match any
                self.pick_col = 'all'
            self._publish_status('mission', f'Mission started with {len(tasks)} tasks')
            self.get_logger().info(f'Mission loaded: {len(tasks)} tasks')

        elif cmd == 'stop':
            with self._lock:
                self._mission_active = False
                self._busy = False
            self._publish_status('idle', 'Emergency stop: operations halted.')
            self.get_logger().info('Emergency stop triggered.')

        elif cmd == 'jog':
            axis = str(cmd_data.get('axis', 'x')).lower()
            direction = int(cmd_data.get('direction', 1))
            step = float(cmd_data.get('step', 10.0))
            if self._dobot is None:
                self._publish_status('error', 'Not connected')
                return
            with self._lock:
                if self._busy:
                    self._publish_status('error', 'Busy — cannot jog now')
                    return
                self._busy = True
            threading.Thread(target=self._do_jog, args=(axis, direction, step), daemon=True).start()

        elif cmd == 'move_to':
            x = float(cmd_data.get('x', 200.0))
            y = float(cmd_data.get('y', 0.0))
            z = float(cmd_data.get('z', self.hover_z))
            r = float(cmd_data.get('r', 0.0))
            if self._dobot is None:
                self._publish_status('error', 'Not connected')
                return
            with self._lock:
                if self._busy:
                    self._publish_status('error', 'Busy — cannot move now')
                    return
                self._busy = True
            threading.Thread(target=self._do_move_to, args=(x, y, z, r), daemon=True).start()

        elif cmd == 'suction':
            enable = bool(cmd_data.get('enable', False))
            if self._dobot is not None:
                try:
                    if enable:
                        self._effector_on(self._dobot)
                    else:
                        self._effector_off(self._dobot)
                    self._publish_status('idle', f'Suction {"ON" if enable else "OFF"}')
                except Exception as e:
                    self._publish_status('error', str(e))

        elif cmd == 'gripper':
            grip = bool(cmd_data.get('grip', False))
            if self._dobot is not None:
                try:
                    if grip:
                        self._dobot.wait_for_cmd(self._dobot.grip(True))
                    else:
                        self._dobot.wait_for_cmd(self._dobot.grip(False))
                    self._publish_status('idle', f'Gripper {"CLOSED" if grip else "OPEN"}')
                except Exception as e:
                    self._publish_status('error', str(e))

        elif cmd == 'preset':
            preset_name = str(cmd_data.get('name', 'hover'))
            if self._dobot is None:
                self._publish_status('error', 'Not connected')
                return
            with self._lock:
                if self._busy:
                    self._publish_status('error', 'Busy')
                    return
                self._busy = True
            threading.Thread(target=self._do_preset, args=(preset_name,), daemon=True).start()

        else:
            self.get_logger().warn(f'Unknown UI command: {cmd!r}')

    def _do_home(self):
        """Thread: execute home sequence."""
        try:
            self._publish_status('moving', 'Homing...')
            self._dobot.wait_for_cmd(self._dobot.home())
            self._publish_status('idle', 'Homing complete.')
            self.get_logger().info('Homing complete.')
        except DobotException as e:
            self.get_logger().error(f'Home error: {e}')
            self._publish_status('error', str(e))
        finally:
            with self._lock:
                self._busy = False

    def _do_calibrate(self):
        """Thread: move to a known calibration position."""
        try:
            self._publish_status('moving', 'Calibrating — moving to safe position...')
            # Move to a neutral raised position for calibration
            self._dobot.wait_for_cmd(
                self._dobot.move_to(150.0, 0.0, self.hover_z, 0., MODE_PTP.MOVJ_XYZ)
            )
            self._publish_status('idle', 'Calibration position reached. Adjust as needed.')
            self.get_logger().info('Calibration position reached.')
        except DobotException as e:
            self.get_logger().error(f'Calibrate error: {e}')
            self._publish_status('error', str(e))
        finally:
            with self._lock:
                self._busy = False

    def _do_jog(self, axis: str, direction: int, step: float):
        """Thread: execute manual jog step along specified axis."""
        try:
            pose = self._dobot.pose()
            tx, ty, tz, tr = float(pose[0]), float(pose[1]), float(pose[2]), float(pose[3])
            delta = float(direction * step)
            if axis == 'x': tx += delta
            elif axis == 'y': ty += delta
            elif axis == 'z': tz += delta
            elif axis == 'r': tr += delta

            self._publish_status('moving', f'Jogging {axis.upper()} to ({tx:.1f}, {ty:.1f}, {tz:.1f})')
            self._dobot.wait_for_cmd(self._dobot.move_to(tx, ty, tz, tr, MODE_PTP.MOVJ_XYZ))
            self._publish_status('idle', f'Jog {axis.upper()} complete.')
        except Exception as e:
            self.get_logger().error(f'Jog error: {e}')
            self._publish_status('error', str(e))
        finally:
            with self._lock:
                self._busy = False

    def _do_move_to(self, x: float, y: float, z: float, r: float):
        """Thread: execute PTP move to target coordinates."""
        try:
            self._publish_status('moving', f'Moving to ({x:.1f}, {y:.1f}, {z:.1f})')
            self._dobot.wait_for_cmd(self._dobot.move_to(x, y, z, r, MODE_PTP.MOVJ_XYZ))
            self._publish_status('idle', 'Target position reached.')
        except Exception as e:
            self.get_logger().error(f'Move error: {e}')
            self._publish_status('error', str(e))
        finally:
            with self._lock:
                self._busy = False

    def _do_preset(self, name: str):
        """Thread: move to a preset position."""
        try:
            if name == 'home':
                self._publish_status('moving', 'Homing...')
                self._dobot.wait_for_cmd(self._dobot.home())
            elif name == 'hover':
                self._publish_status('moving', 'Moving to hover height...')
                self._dobot.wait_for_cmd(self._dobot.move_to(200.0, 0.0, self.hover_z, 0.0, MODE_PTP.MOVJ_XYZ))
            elif name == 'dropoff':
                self._publish_status('moving', 'Moving to drop-off position...')
                self._dobot.wait_for_cmd(self._dobot.move_to(self.drop_x, self.drop_y, self.drop_z, 0.0, MODE_PTP.MOVJ_XYZ))
            elif name == 'zero_r':
                pose = self._dobot.pose()
                self._publish_status('moving', 'Resetting wrist angle to 0°...')
                self._dobot.wait_for_cmd(self._dobot.move_to(float(pose[0]), float(pose[1]), float(pose[2]), 0.0, MODE_PTP.MOVJ_XYZ))
            self._publish_status('idle', f'Preset {name} reached.')
        except Exception as e:
            self.get_logger().error(f'Preset error: {e}')
            self._publish_status('error', str(e))
        finally:
            with self._lock:
                self._busy = False

    # -----------------------------------------------------------------------
    # Pick-and-place sequence
    # -----------------------------------------------------------------------


    def _pick_and_place(self, x: float, y: float, z: float, color: str,
                        drop_z_override: float | None = None):
        """
        Blocking pick-and-place cycle. Runs in a daemon thread.
        All coordinates are in Dobot robot frame (mm).
        drop_z_override: if set, overrides self.drop_z (used for cube stacking).
        """
        d = self._dobot
        actual_drop_z = drop_z_override if drop_z_override is not None else self.drop_z
        try:
            self.get_logger().info(
                f'Pick START → color={color}, X={x:.1f}, Y={y:.1f}, Z={z:.1f} mm'
                f', drop_z={actual_drop_z:.1f}'
            )
            self._publish_status('moving', f'Moving to {color} cube at ({x:.0f},{y:.0f}) mm')

            # 1. Move ABOVE the cube (hover height)
            self.get_logger().info(f'  → Hover above cube ({x:.1f}, {y:.1f}, {self.hover_z:.1f})')
            d.wait_for_cmd(d.move_to(x, y, self.hover_z, 0., MODE_PTP.MOVJ_XYZ))

            # 2. Activate end-effector BEFORE descending
            self._effector_on(d)

            # 3. Descend to pick height
            self.get_logger().info(f'  → Descend to pick Z={self.pick_z:.1f}')
            d.wait_for_cmd(d.move_to(x, y, self.pick_z, 0., MODE_PTP.MOVL_XYZ))

            # 4. Brief dwell to ensure firm grip
            time.sleep(0.3)

            # 5. Lift back to hover height
            self.get_logger().info(f'  → Lift to hover Z={self.hover_z:.1f}')
            d.wait_for_cmd(d.move_to(x, y, self.hover_z, 0., MODE_PTP.MOVL_XYZ))

            # 6. Carry to drop-off location (hover height)
            self.get_logger().info(
                f'  → Carry to drop-off ({self.drop_x:.1f}, {self.drop_y:.1f}, {self.hover_z:.1f})'
            )
            d.wait_for_cmd(d.move_to(self.drop_x, self.drop_y, self.hover_z, 0., MODE_PTP.MOVJ_XYZ))

            # 7. Lower to drop height (may be stacked)
            self.get_logger().info(f'  → Lower to drop Z={actual_drop_z:.1f}')
            d.wait_for_cmd(d.move_to(self.drop_x, self.drop_y, actual_drop_z, 0., MODE_PTP.MOVL_XYZ))

            # 8. Release end-effector
            self._effector_off(d)
            time.sleep(0.2)

            # 9. Rise clear of the dropped cube
            d.wait_for_cmd(d.move_to(self.drop_x, self.drop_y, self.hover_z, 0., MODE_PTP.MOVL_XYZ))

            self.get_logger().info(f'Pick DONE → {color} cube placed at drop-off.')
            self._publish_status('idle', f'Placed {color} cube at drop-off.')

        except DobotException as e:
            self.get_logger().error(f'DobotException during pick-place: {e}')
            self._publish_status('error', str(e))
            try:
                self._effector_off(d)
            except Exception:
                pass
        except Exception as e:
            self.get_logger().error(f'Unexpected error: {e}')
            self._publish_status('error', str(e))
        finally:
            with self._lock:
                self._busy = False

    # -----------------------------------------------------------------------
    # End-effector helpers
    # -----------------------------------------------------------------------

    def _effector_on(self, d: Dobot):
        self._suction_active = True
        if self.suction:
            d.wait_for_cmd(d.suck(True))
            self.get_logger().info('  → Suction ON')
        else:
            d.wait_for_cmd(d.grip(True))
            self.get_logger().info('  → Gripper CLOSED')

    def _effector_off(self, d: Dobot):
        self._suction_active = False
        if self.suction:
            d.wait_for_cmd(d.suck(False))
            self.get_logger().info('  → Suction OFF')
        else:
            d.wait_for_cmd(d.grip(False))
            self.get_logger().info('  → Gripper OPEN')

    # -----------------------------------------------------------------------
    # Status publisher
    # -----------------------------------------------------------------------

    def _publish_status(self, state: str, message: str):
        data = {'state': state, 'message': message}
        if self._dobot is not None:
            try:
                pose = self._dobot.pose()
                data['x'] = float(pose[0])
                data['y'] = float(pose[1])
                data['z'] = float(pose[2])
                data['r'] = float(pose[3])
                data['suction'] = getattr(self, '_suction_active', False)
            except Exception:
                pass
        s = String()
        s.data = json.dumps(data)
        self.pub_status.publish(s)

    # -----------------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------------

    def destroy_node(self):
        if self._dobot is not None:
            try:
                self._effector_off(self._dobot)
            except Exception:
                pass
            try:
                self._dobot.close()
            except Exception:
                pass
            self.get_logger().info('Dobot connection closed.')
        super().destroy_node()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

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


if __name__ == '__main__':
    main()
