"""Main Window combining video feed, 3x3 grid, sequence table, and telemetry."""

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QMessageBox
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QMessageBox
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

        # 2. Main Splitter: Left (Video + Telemetry) | Right (3x3 Grid + Sequence)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(0, 0, 0, 0)
        self.video = VideoWidget(self)
        l_lay.addWidget(self.video, stretch=3)
        self.telemetry = RobotTelemetryWidget(self)
        l_lay.addWidget(self.telemetry, stretch=1)
        splitter.addWidget(left)

        right = QWidget()
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(0, 0, 0, 0)
        self.grid = FieldGridWidget(self)
        r_lay.addWidget(self.grid, stretch=2)
        self.seq = SequenceWidget(self)
        r_lay.addWidget(self.seq, stretch=2)
        splitter.addWidget(right)

        root.addWidget(splitter, stretch=1)

        # 3. Log console
        self.log = LogWidget(self)
        root.addWidget(self.log)

    def _connect_signals(self):
        # ROS bridge signals
        self.bridge.image_received.connect(self.video.set_frame)
        self.bridge.status_received.connect(self.telemetry.update_status)
        self.bridge.detections_received.connect(self._on_detections)
        self.bridge.log_message.connect(self.log.append_log)

        # Grid and sequence updates
        self.grid.sequence_changed.connect(self._sync_sequence)
        self.grid.sync_requested.connect(self._on_sync_vision)

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
            QMessageBox.warning(self, "No Tasks", "Please assign stack order (1..8) to grid cubes.")
            return

        payload = {
            "cmd": "mission",
            "task_count": len(tasks),
            "tasks": [
                {
                    "order": t["order"],
                    "index": t["order"],
                    "cell_id": t["cell_id"],
                    "color": t["color"],
                    "pick": {"x": t["pick"][0], "y": t["pick"][1], "z": t["pick"][2]},
                    "drop_z": t["drop_z"]
                }
                for t in tasks
            ]
        }
        self.bridge.send_cmd(payload)
        self.log.append_log("INFO", f"Dispatched mission with {len(tasks)} stacking steps.")

    def closeEvent(self, event):
        self.bridge.stop()
        event.accept()
