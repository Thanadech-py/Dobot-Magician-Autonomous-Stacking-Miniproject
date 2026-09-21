"""Stacking mission sequencer and trajectory generator for Dobot Magician.

Supports 3-phase complex missions:
  Phase 1: Clear obstacle cubes from field to Feeders 1..4
  Phase 2: Stack target cubes (locked to max 4) on Center Goal [1, 1]
  Phase 3: Restore obstacle cubes from Feeders 1..4 back to original grid positions
Includes collision avoidance:
  - Horizontal keepout around Center Goal tower with North/South bypass waypoints
  - Safe vertical clearance Z (> 140 mm) above the growing goal tower
"""

import logging
import math
import threading
import time

from .dobot_driver import DobotDriver

logger = logging.getLogger("dobot_v2.mission")


class MissionExecutor:
    """Manages pick-and-place trajectories, obstacle clearance, and cube stacking sequences."""

    def __init__(self, driver: DobotDriver, config: dict, logger_instance=None):
        self.driver = driver
        self.log = logger_instance or logger
        self.cfg = config

        geom = self.cfg.get("geometry", {})
        self.hover_z = float(geom.get("hover_z", 80.0))
        self.pick_z = float(geom.get("pick_z", 12.5))
        self.drop_x = float(geom.get("dropoff_x", 176.0))
        self.drop_y = float(geom.get("dropoff_y", 0.0))
        self.base_drop_z = float(geom.get("dropoff_z", 30.0))
        self.cube_height = float(geom.get("cube_height", 25.0))
        self.max_stack_blocks = int(geom.get("max_stack_blocks", 4))
        self.safe_goal_clear_z = float(geom.get("safe_goal_clear_z", 142.0))
        self.goal_keepout_radius = float(geom.get("goal_keepout_radius", 38.0))

        eff = self.cfg.get("effector", {})
        self.dwell_grip = float(eff.get("dwell_grip_sec", 0.35))
        self.dwell_release = float(eff.get("dwell_release_sec", 0.25))

        self._active = False
        self._stop_requested = False
        self._thread = None
        self._lock = threading.Lock()
        self.status_callback = None  # Callable[[str, str], None]
        self._current_goal_stack = 0

    @property
    def is_active(self) -> bool:
        return self._active

    def start_mission(self, tasks: list[dict], on_status=None) -> bool:
        """Starts a multi-step cube stacking mission in a background thread."""
        with self._lock:
            if self._active:
                self.log.warn("A stacking mission is already in progress.")
                return False
            if not tasks:
                self.log.warn("Cannot start mission with empty task list.")
                return False

            self.status_callback = on_status
            self._active = True
            self._stop_requested = False
            self._thread = threading.Thread(
                target=self._run_mission_thread,
                args=(tasks,),
                daemon=True,
                name="DobotMissionThread"
            )
            self._thread.start()
            return True

    def stop(self):
        """Immediately halts any running mission."""
        with self._lock:
            self._stop_requested = True
            self._active = False
        try:
            self.driver.set_suction(False)
        except Exception:
            pass
        self._emit_status("idle", "Mission stopped.")
        self.log.info("Mission execution stopped by operator.")

    def _emit_status(self, state: str, message: str):
        if self.status_callback:
            try:
                self.status_callback(state, message)
            except Exception:
                pass

    @staticmethod
    def _extract_coords(data, default_x: float, default_y: float, default_z: float) -> tuple[float, float, float]:
        if isinstance(data, (list, tuple)) and len(data) >= 3:
            return float(data[0]), float(data[1]), float(data[2])
        elif isinstance(data, dict):
            return float(data.get("x", default_x)), float(data.get("y", default_y)), float(data.get("z", default_z))
        return float(default_x), float(default_y), float(default_z)

    def _point_to_segment_dist(self, px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> tuple[float, float, float]:
        """Calculates closest distance from (px, py) to line segment (x1, y1)-(x2, y2)."""
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy
        if length_sq < 1e-6:
            return math.hypot(px - x1, py - y1), x1, y1
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y), proj_x, proj_y

    def _plan_safe_transit(self, x1: float, y1: float, x2: float, y2: float, transit_z: float) -> list[tuple[float, float, float]]:
        """Returns waypoints avoiding the center goal keepout cylinder."""
        dist, _, _ = self._point_to_segment_dist(self.drop_x, self.drop_y, x1, y1, x2, y2)
        # If path stays outside keepout zone, fly direct
        if dist >= self.goal_keepout_radius:
            return [(x2, y2, transit_z)]

        # Path penetrates the goal keepout area! Generate detour waypoint
        self.log.info(
            f"Goal collision avoidance: Path ({x1:.1f}, {y1:.1f}) -> ({x2:.1f}, {y2:.1f}) "
            f"within {dist:.1f} mm of goal ({self.drop_x:.1f}, {self.drop_y:.1f}). Routing around..."
        )
        mid_y = (y1 + y2) / 2.0
        # Choose detour corridor: North corridor (X ~ 222) if near top, South corridor (X ~ 132) otherwise
        if max(x1, x2) >= self.drop_x:
            detour_x = 222.0
            detour_y = 35.0 if mid_y >= 0.0 else -35.0
        else:
            detour_x = 132.0
            detour_y = 35.0 if mid_y >= 0.0 else -35.0

        return [(detour_x, detour_y, transit_z), (x2, y2, transit_z)]

    def _execute_pick_place(self, px: float, py: float, pz: float, drop_x: float, drop_y: float, drop_z: float,
                            color: str, action: str = "stack_goal") -> bool:
        """Executes a single pick-and-place cycle with intelligent goal collision avoidance."""
        d = self.driver
        try:
            # Determine safe transit height: if cubes are on the goal, transit must clear the tower
            if self._current_goal_stack > 0:
                transit_z = max(self.hover_z, self.safe_goal_clear_z)
            else:
                transit_z = self.hover_z

            # 1. Hover above pick location at safe transit height
            if self._stop_requested: return False
            d.move_to(px, py, transit_z, r=0.0, linear=False)

            # 2. Activate suction before descending
            if self._stop_requested: return False
            d.set_suction(True)

            # 3. Descend vertically to pick height
            if self._stop_requested: return False
            d.move_to(px, py, pz, r=0.0, linear=True)
            time.sleep(self.dwell_grip)

            # 4. Lift vertically back to safe transit height
            if self._stop_requested: return False
            d.move_to(px, py, transit_z, r=0.0, linear=True)

            # 5. Safe horizontal transit to drop-off location
            is_goal_drop = (action == "stack_goal") or (abs(drop_x - self.drop_x) < 5.0 and abs(drop_y - self.drop_y) < 5.0)

            if is_goal_drop:
                # Approach goal strictly from above at safe_goal_clear_z
                approach_z = max(transit_z, self.safe_goal_clear_z)
                # Waypoint check if approaching from an angled start
                waypoints = self._plan_safe_transit(px, py, drop_x, drop_y, approach_z)
                for wx, wy, wz in waypoints:
                    if self._stop_requested: return False
                    d.move_to(wx, wy, wz, r=0.0, linear=False)
            else:
                # Feeder transfer or restore: route waypoints around goal keepout
                waypoints = self._plan_safe_transit(px, py, drop_x, drop_y, transit_z)
                for wx, wy, wz in waypoints:
                    if self._stop_requested: return False
                    d.move_to(wx, wy, wz, r=0.0, linear=False)

            # 6. Lower vertically to drop height
            if self._stop_requested: return False
            d.move_to(drop_x, drop_y, drop_z, r=0.0, linear=True)

            # 7. Release cube
            if self._stop_requested: return False
            d.set_suction(False)
            time.sleep(self.dwell_release)

            # Increment goal stack count if dropped at center goal
            if is_goal_drop:
                self._current_goal_stack += 1

            # 8. Rise vertically clear of drop
            if self._stop_requested: return False
            retract_z = max(transit_z, self.safe_goal_clear_z if self._current_goal_stack > 0 else self.hover_z)
            d.move_to(drop_x, drop_y, retract_z, r=0.0, linear=True)

            return True
        except Exception as e:
            self.log.error(f"Pick-and-place movement failed: {e}")
            try:
                d.set_suction(False)
            except Exception:
                pass
            return False

    def _run_mission_thread(self, tasks: list[dict]):
        """Background execution worker for 3-phase mission: Clear Obstacles -> Stack Goal -> Restore Obstacles."""
        try:
            self.log.info(f"Starting mission with {len(tasks)} total tasks.")
            self._current_goal_stack = 0

            # Partition tasks into Phase 1 (Clear), Phase 2 (Stack), Phase 3 (Restore)
            clear_tasks = [t for t in tasks if t.get("action") == "clear_to_feeder"]
            stack_tasks = [t for t in tasks if t.get("action") in ("stack_goal", "stack", None) and t.get("action") != "clear_to_feeder" and t.get("action") != "restore_from_feeder"]
            restore_tasks = [t for t in tasks if t.get("action") == "restore_from_feeder"]

            # Clamp stack tasks strictly to max_stack_blocks (4)
            if len(stack_tasks) > self.max_stack_blocks:
                self.log.warn(f"Clamping {len(stack_tasks)} stack tasks to locked max {self.max_stack_blocks} blocks.")
                stack_tasks = stack_tasks[:self.max_stack_blocks]

            # If tasks were not explicitly partitioned by action, use tasks directly as stacking tasks
            if not clear_tasks and not restore_tasks and not stack_tasks:
                stack_tasks = tasks[:self.max_stack_blocks]

            # Total execution phases
            phases = []
            if clear_tasks:
                phases.append((1, "Clear Obstacles to Feeders", clear_tasks))
            phases.append((2, "Stack Blocks on Goal (Max 4)", stack_tasks))
            if restore_tasks:
                phases.append((3, "Restore Obstacles from Feeders to Origin", restore_tasks))

            total_steps = len(clear_tasks) + len(stack_tasks) + len(restore_tasks)
            current_step = 0

            self._emit_status("moving", f"Mission started: 3-Phase Plan ({total_steps} total steps).")

            for phase_num, phase_title, p_tasks in phases:
                if self._stop_requested:
                    break

                self.log.info(f"─── Starting Phase {phase_num}: {phase_title} ({len(p_tasks)} tasks) ───")

                for idx, task in enumerate(p_tasks):
                    if self._stop_requested:
                        self.log.info("Mission aborted between steps.")
                        break

                    current_step += 1
                    action = task.get("action", "stack_goal" if phase_num == 2 else "clear_to_feeder")
                    color = task.get("color", "cube").upper()
                    cell_name = task.get("cell_name", task.get("cell_id", "cell"))
                    feeder_name = task.get("feeder_name", f"Feeder {task.get('feeder_id', 1)}")

                    px, py, pz = self._extract_coords(task.get("pick"), self.drop_x, self.drop_y, self.pick_z)
                    drop_x, drop_y, drop_z = self._extract_coords(task.get("drop"), self.drop_x, self.drop_y, self.base_drop_z)

                    if action == "stack_goal":
                        target_drop_z = float(task.get("drop_z", self.base_drop_z + (self._current_goal_stack * self.cube_height)))
                        step_desc = f"[Phase 2/3] Stack Goal #{idx + 1}/{len(p_tasks)}: {color} ({cell_name} -> Goal Z={target_drop_z:.1f}mm)"
                    elif action == "clear_to_feeder":
                        target_drop_z = drop_z
                        step_desc = f"[Phase 1/3] Clear Obs #{idx + 1}/{len(p_tasks)}: {color} ({cell_name} -> {feeder_name})"
                    else:  # restore_from_feeder
                        target_drop_z = drop_z
                        step_desc = f"[Phase 3/3] Restore Obs #{idx + 1}/{len(p_tasks)}: {color} ({feeder_name} -> Origin {cell_name})"

                    self.log.info(f"Step {current_step}/{total_steps}: {step_desc}")
                    self._emit_status("moving", f"Step {current_step}/{total_steps}: {step_desc}")

                    success = self._execute_pick_place(
                        px, py, pz, drop_x, drop_y, target_drop_z, color, action=action
                    )
                    if not success or self._stop_requested:
                        self.log.warn(f"Step {current_step} ({step_desc}) halted or failed.")
                        break

            if not self._stop_requested:
                summary_msg = f"Mission Complete! {len(stack_tasks)} blocks stacked on goal"
                if clear_tasks:
                    summary_msg += f", {len(clear_tasks)} obstacles cleared & restored."
                else:
                    summary_msg += "."
                self.log.info(summary_msg)
                self._emit_status("idle", summary_msg)
            else:
                self._emit_status("idle", "Mission halted by operator.")

        except Exception as e:
            self.log.error(f"Mission execution error: {e}")
            self._emit_status("error", f"Mission error: {e}")
        finally:
            with self._lock:
                self._active = False
