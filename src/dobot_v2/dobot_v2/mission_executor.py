"""Stacking mission sequencer and trajectory generator for Dobot Magician."""

import logging
import threading
import time

from .dobot_driver import DobotDriver

logger = logging.getLogger("dobot_v2.mission")


class MissionExecutor:
    """Manages pick-and-place trajectories and cube stacking sequences."""

    def __init__(self, driver: DobotDriver, config: dict, logger_instance=None):
        self.driver = driver
        self.log = logger_instance or logger
        self.cfg = config

        geom = self.cfg.get("geometry", {})
        self.hover_z = float(geom.get("hover_z", 80.0))
        self.pick_z = float(geom.get("pick_z", 12.5))
        self.drop_x = float(geom.get("dropoff_x", 200.0))
        self.drop_y = float(geom.get("dropoff_y", 0.0))
        self.base_drop_z = float(geom.get("dropoff_z", 30.0))
        self.cube_height = float(geom.get("cube_height", 25.0))

        eff = self.cfg.get("effector", {})
        self.dwell_grip = float(eff.get("dwell_grip_sec", 0.35))
        self.dwell_release = float(eff.get("dwell_release_sec", 0.25))

        self._active = False
        self._stop_requested = False
        self._thread = None
        self._lock = threading.Lock()
        self.status_callback = None  # Callable[[str, str], None]

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

    def _run_mission_thread(self, tasks: list[dict]):
        """Background execution worker for stacking tasks."""
        try:
            self.log.info(f"Starting stacking mission with {len(tasks)} tasks.")
            self._emit_status("moving", f"Mission started: 0/{len(tasks)} stacked.")

            # Sort tasks by sequential order
            sorted_tasks = sorted(tasks, key=lambda t: t.get("order", t.get("index", 0)))

            for step_idx, task in enumerate(sorted_tasks):
                if self._stop_requested:
                    self.log.info("Mission aborted between steps.")
                    break

                color = task.get("color", "cube").upper()
                cell_id = task.get("cell_id", "")
                order = task.get("order", step_idx + 1)

                # Extract pick coordinates
                pick_data = task.get("pick", {})
                px = float(pick_data.get("x", self.drop_x))
                py = float(pick_data.get("y", self.drop_y))
                pz = float(pick_data.get("z", self.pick_z))

                # Drop Z: either explicit override or calculated by layer stack level
                target_drop_z = float(task.get("drop_z", self.base_drop_z + (step_idx * self.cube_height)))

                self.log.info(
                    f"Executing step {step_idx + 1}/{len(sorted_tasks)}: "
                    f"Pick {color} from cell {cell_id} ({px:.1f}, {py:.1f}, {pz:.1f}) "
                    f"-> Drop at Z={target_drop_z:.1f} mm"
                )
                self._emit_status(
                    "moving",
                    f"Step {step_idx + 1}/{len(sorted_tasks)}: Picking {color} cube ({cell_id})"
                )

                success = self._execute_pick_place(px, py, pz, target_drop_z, color)
                if not success or self._stop_requested:
                    self.log.warn(f"Step {step_idx + 1} incomplete or halted.")
                    break

                self._emit_status(
                    "moving",
                    f"Step {step_idx + 1}/{len(sorted_tasks)}: Placed {color} on stack."
                )

            if not self._stop_requested:
                self.log.info("All stacking mission tasks completed successfully!")
                self._emit_status("idle", "Mission complete! All cubes stacked.")
            else:
                self._emit_status("idle", "Mission halted.")

        except Exception as e:
            self.log.error(f"Mission execution error: {e}")
            self._emit_status("error", f"Mission error: {e}")
        finally:
            with self._lock:
                self._active = False

    def _execute_pick_place(self, px: float, py: float, pz: float, drop_z: float, color: str) -> bool:
        """Executes a single pick-and-place cycle with smooth vertical clearances."""
        d = self.driver
        try:
            # 1. Hover above pick location
            if self._stop_requested: return False
            d.move_to(px, py, self.hover_z, r=0.0, linear=False)

            # 2. Activate suction tool before descending
            if self._stop_requested: return False
            d.set_suction(True)

            # 3. Descend vertically to pick height
            if self._stop_requested: return False
            d.move_to(px, py, pz, r=0.0, linear=True)
            time.sleep(self.dwell_grip)

            # 4. Lift vertically back to transit hover height
            if self._stop_requested: return False
            d.move_to(px, py, self.hover_z, r=0.0, linear=True)

            # 5. Carry over to drop-off center location (at hover height)
            if self._stop_requested: return False
            d.move_to(self.drop_x, self.drop_y, self.hover_z, r=0.0, linear=False)

            # 6. Lower vertically to stack height
            if self._stop_requested: return False
            d.move_to(self.drop_x, self.drop_y, drop_z, r=0.0, linear=True)

            # 7. Release cube
            if self._stop_requested: return False
            d.set_suction(False)
            time.sleep(self.dwell_release)

            # 8. Rise vertically clear of stack
            if self._stop_requested: return False
            d.move_to(self.drop_x, self.drop_y, self.hover_z, r=0.0, linear=True)

            return True
        except Exception as e:
            self.log.error(f"Pick-and-place movement failed: {e}")
            try:
                d.set_suction(False)
            except Exception:
                pass
            return False
