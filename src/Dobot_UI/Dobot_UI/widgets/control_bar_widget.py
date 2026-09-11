"""Top action toolbar for robot connection, homing, and starting mission."""

try:
    from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
    from PyQt6.QtCore import pyqtSignal
except ImportError:
    from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
    from PyQt5.QtCore import pyqtSignal


class ControlBarWidget(QFrame):
    """Toolbar for primary Dobot commands."""
    connect_requested = pyqtSignal()
    home_requested = pyqtSignal()
    restart_detection_requested = pyqtSignal()
    start_mission_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Title
        title = QLabel("🤖 DOBOT MISSION UI")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(title)
        layout.addSpacing(12)

        # Utility Buttons
        btn_connect = QPushButton("⚡ Connect")
        btn_connect.clicked.connect(self.connect_requested.emit)
        layout.addWidget(btn_connect)

        btn_home = QPushButton("🏠 Home")
        btn_home.clicked.connect(self.home_requested.emit)
        layout.addWidget(btn_home)

        # Reset Detection Node button (close and open detection node again)
        btn_restart = QPushButton("🔄 Reset Detection Node")
        btn_restart.setToolTip("Close and open the detection node again")
        btn_restart.setStyleSheet("background-color: #334155; border: 1px solid #475569; font-weight: bold;")
        btn_restart.clicked.connect(self.restart_detection_requested.emit)
        layout.addWidget(btn_restart)

        layout.addStretch()

        # Mission Action Buttons
        btn_start = QPushButton("▶ START STACKING (1st..8th)")
        btn_start.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        btn_start.clicked.connect(self.start_mission_requested.emit)
        layout.addWidget(btn_start)

        btn_stop = QPushButton("🛑 EMERGENCY STOP")
        btn_stop.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold;")
        btn_stop.clicked.connect(self.stop_requested.emit)
        layout.addWidget(btn_stop)
