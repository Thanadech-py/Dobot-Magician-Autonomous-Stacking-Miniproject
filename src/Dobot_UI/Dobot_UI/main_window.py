"""Main Window combining video feed, 3x3 grid, sequence table, and telemetry."""

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QMessageBox,
        QTabWidget
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QMessageBox,
        QTabWidget
    )
    from PyQt5.QtCore import Qt

try:
    from .constants import STYLESHEET
    from .config import WINDOW
    from .ros_bridge import RosBridge
    from .widgets.control_bar_widget import ControlBarWidget
    from .widgets.video_widget import VideoWidget
    from .widgets.grid_widget import FieldGridWidget
    from .widgets.sequence_widget import SequenceWidget
    from .widgets.robot_telemetry_widget import RobotTelemetryWidget
    from .widgets.log_widget import LogWidget
    from .widgets.manual_control_widget import ManualControlWidget
    from .widgets.teach_widget import TeachWidget
except (ImportError, ValueError):
    from Dobot_UI.constants import STYLESHEET
    from Dobot_UI.config import WINDOW
    from Dobot_UI.ros_bridge import RosBridge
    from Dobot_UI.widgets.control_bar_widget import ControlBarWidget
    from Dobot_UI.widgets.video_widget import VideoWidget
    from Dobot_UI.widgets.grid_widget import FieldGridWidget
    from Dobot_UI.widgets.sequence_widget import SequenceWidget
    from Dobot_UI.widgets.robot_telemetry_widget import RobotTelemetryWidget
    from Dobot_UI.widgets.log_widget import LogWidget
    from Dobot_UI.widgets.manual_control_widget import ManualControlWidget
    from Dobot_UI.widgets.teach_widget import TeachWidget


class DobotMainWindow(QMainWindow):
    """Main application window for Dobot Magician 8-Cube Stacking UI."""

    def __init__(self, ros_bridge: RosBridge, parent=None):
        super().__init__(parent)
        self.bridge = ros_bridge
        self.last_detections = []

        self.setWindowTitle(WINDOW.get("title", "Dobot Magician - Stacking Mission UI"))
        self.resize(WINDOW.get("width", 1100), WINDOW.get("height", 750))
        self.setStyleSheet(STYLESHEET)
        self._init_ui()
        self._connect_signals()
        self._sync_sequence()

    def _init_ui(self):
        center = QWidget()
        self.setCentralWidget(center)
        root = QVBoxLayout(center)
        root.setContentsMargins(6, 6, 6, 6)

        # 1. Action Toolbar
        self.toolbar = ControlBarWidget(self)
        root.addWidget(self.toolbar)

        # 2. Main Splitter: Left (Video + Telemetry) | Right (Tabs: Mission vs Manual)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(0, 0, 0, 0)
        self.video = VideoWidget(self)
        l_lay.addWidget(self.video, stretch=3)
        self.telemetry = RobotTelemetryWidget(self)
        l_lay.addWidget(self.telemetry, stretch=1)
        splitter.addWidget(left)

        # Right Tabbed Panel
        self.right_tabs = QTabWidget()

        # Tab 1: Stacking Mission Planner
        tab_mission = QWidget()
        r_lay = QVBoxLayout(tab_mission)
        r_lay.setContentsMargins(4, 6, 4, 4)
        self.grid = FieldGridWidget(self)
        r_lay.addWidget(self.grid, stretch=2)
        self.seq = SequenceWidget(self)
        r_lay.addWidget(self.seq, stretch=2)
        self.right_tabs.addTab(tab_mission, "🎯 Stacking Mission")

        # Tab 2: Manual Control
        self.manual_ctrl = ManualControlWidget(self)
        self.right_tabs.addTab(self.manual_ctrl, "🎮 Manual Control")

        # Tab 3: Goal & Cell Teaching Menu (Vision Bypass)
        self.teach_widget = TeachWidget(self)
        self.right_tabs.addTab(self.teach_widget, "📍 Teach Positions")

        splitter.addWidget(self.right_tabs)
        splitter.setSizes([480, 600])

        root.addWidget(splitter, stretch=1)

        # 3. Log console
        self.log = LogWidget(self)
        root.addWidget(self.log)

    def _connect_signals(self):
        # ROS bridge signals
        self.bridge.image_received.connect(self.video.set_frame)
        self.bridge.status_received.connect(self.telemetry.update_status)
        self.bridge.status_received.connect(self.manual_ctrl.update_telemetry)
        self.bridge.status_received.connect(self.teach_widget.update_telemetry)
        self.bridge.detections_received.connect(self._on_detections)
        self.bridge.log_message.connect(self.log.append_log)

        # Grid and sequence updates
        self.grid.sequence_changed.connect(self._sync_sequence)
        self.grid.sync_requested.connect(self._on_sync_vision)
        self.grid.bypass_toggled.connect(self.teach_widget.set_bypass_mode)

        # Mode toggle & Tab changed
        self.toolbar.toggle_manual_mode_requested.connect(self._toggle_mode)
        self.right_tabs.currentChanged.connect(self._on_tab_changed)

        # Manual Control signals
        self.manual_ctrl.jog_requested.connect(self._on_manual_jog)
        self.manual_ctrl.move_to_requested.connect(self._on_manual_move_to)
        self.manual_ctrl.suction_requested.connect(self._on_manual_suction)
        self.manual_ctrl.gripper_requested.connect(self._on_manual_gripper)
        self.manual_ctrl.preset_requested.connect(self._on_manual_preset)
        self.manual_ctrl.stop_requested.connect(lambda: self.bridge.send_cmd({"cmd": "stop"}))

        # Teach Widget signals
        self.teach_widget.jog_requested.connect(self._on_manual_jog)
        self.teach_widget.move_to_requested.connect(self._on_manual_move_to)
        self.teach_widget.suction_requested.connect(self._on_manual_suction)
        self.teach_widget.positions_updated.connect(self.grid.set_stored_positions)
        self.teach_widget.bypass_toggled.connect(self.grid.set_bypass_mode)

        # Commands
        self.toolbar.connect_requested.connect(lambda: self.bridge.send_cmd({"cmd": "connect"}))
        self.toolbar.home_requested.connect(lambda: self.bridge.send_cmd({"cmd": "home"}))
        self.toolbar.restart_detection_requested.connect(self.bridge.restart_detection_node)
        self.video.reset_node_requested.connect(self.bridge.restart_detection_node)
        self.toolbar.stop_requested.connect(lambda: self.bridge.send_cmd({"cmd": "stop"}))
        self.toolbar.start_mission_requested.connect(self._start_mission)

    def _sync_sequence(self):
        tasks = self.grid.get_ordered_tasks()
        self.seq.update_table(tasks)

    def _on_detections(self, data: dict):
        self.last_detections = data.get("objects", [])

    def _on_sync_vision(self):
        if self.last_detections:
            self.grid.sync_vision(self.last_detections)
            self.log.append_log("INFO", f"Synced {len(self.last_detections)} detected cubes into grid.")
        else:
            self.log.append_log("WARN", "No detected cubes available yet from detection_node.")

    def _start_mission(self):
        tasks = self.grid.get_ordered_tasks()
        if not tasks:
            QMessageBox.warning(self, "No Tasks", "Please assign cubes to Goal (#1..#4) or Feeders (Obs #1..#4).")
            return

        clear_cnt = sum(1 for t in tasks if t.get("action") == "clear_to_feeder")
        stack_cnt = sum(1 for t in tasks if t.get("action") == "stack_goal")
        restore_cnt = sum(1 for t in tasks if t.get("action") == "restore_from_feeder")

        formatted_tasks = []
        for t in tasks:
            formatted_tasks.append({
                "action": t.get("action", "stack_goal"),
                "phase": t.get("phase", 2),
                "order": t.get("order", 1),
                "cell_id": str(t.get("cell_id", "")),
                "cell_name": t.get("cell_name", ""),
                "feeder_id": t.get("feeder_id"),
                "feeder_name": t.get("feeder_name", ""),
                "color": t.get("color", "none"),
                "pick": {"x": t["pick"][0], "y": t["pick"][1], "z": t["pick"][2]},
                "drop": {"x": t["drop"][0], "y": t["drop"][1], "z": t["drop"][2]},
                "drop_z": float(t.get("drop_z", 12.5)),
            })

        payload = {
            "cmd": "mission",
            "task_count": len(formatted_tasks),
            "tasks": formatted_tasks,
        }
        self.bridge.send_cmd(payload)
        self.log.append_log(
            "INFO",
            f"Dispatched mission: {clear_cnt} obstacles cleared, {stack_cnt} goal stacked (max 4), {restore_cnt} restored."
        )

    def _toggle_mode(self):
        cur = self.right_tabs.currentIndex()
        next_idx = (cur + 1) % self.right_tabs.count()
        self.right_tabs.setCurrentIndex(next_idx)

    def _on_tab_changed(self, index: int):
        titles = {0: "🎮 Manual Mode", 1: "📍 Teach Mode", 2: "🎯 Mission Mode"}
        modes  = {0: "Stacking Mission", 1: "Manual Control", 2: "Teach Positions"}
        self.toolbar.btn_mode.setText(titles.get(index, "🎮 Manual Mode"))
        self.log.append_log("INFO", f"Switched to {modes.get(index, 'tab')} mode.")

    def _on_manual_jog(self, axis: str, direction: int, step: float):
        payload = {
            "cmd": "jog",
            "axis": axis.lower(),
            "direction": direction,
            "step": step,
        }
        self.bridge.send_cmd(payload)
        sign = "+" if direction > 0 else "-"
        unit = "°" if axis.lower() == "r" else "mm"
        self.log.append_log("INFO", f"Manual Jog: {axis.upper()} {sign}{step:.1f}{unit}")

    def _on_manual_move_to(self, x: float, y: float, z: float, r: float):
        payload = {
            "cmd": "move_to",
            "x": x,
            "y": y,
            "z": z,
            "r": r,
        }
        self.bridge.send_cmd(payload)
        self.log.append_log("INFO", f"Manual Move: X={x:.1f}, Y={y:.1f}, Z={z:.1f}, R={r:.1f}")

    def _on_manual_suction(self, enable: bool):
        payload = {
            "cmd": "suction",
            "enable": enable,
        }
        self.bridge.send_cmd(payload)
        self.log.append_log("INFO", f"Manual Suction: {'ON' if enable else 'OFF'}")

    def _on_manual_gripper(self, grip: bool):
        payload = {
            "cmd": "gripper",
            "grip": grip,
        }
        self.bridge.send_cmd(payload)
        self.log.append_log("INFO", f"Manual Gripper: {'GRIP (CLOSE)' if grip else 'RELEASE (OPEN)'}")

    def _on_manual_preset(self, preset_name: str):
        payload = {
            "cmd": "preset",
            "name": preset_name,
        }
        self.bridge.send_cmd(payload)
        self.log.append_log("INFO", f"Manual Preset: {preset_name}")

    def closeEvent(self, event):
        self.bridge.stop()
        event.accept()
