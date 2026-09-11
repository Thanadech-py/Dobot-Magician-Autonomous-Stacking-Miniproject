"""Dobot Magician telemetry widget displaying coordinates and robot state."""

try:
    from PyQt6.QtWidgets import (
        QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame
    )
    from PyQt6.QtCore import Qt
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
except ImportError:
    from PyQt5.QtWidgets import (
        QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame
    )
    from PyQt5.QtCore import Qt
    ALIGN_CENTER = Qt.AlignCenter


class RobotTelemetryWidget(QGroupBox):
    """Visualizes Dobot state, Cartesian coordinates, and suction status."""

    def __init__(self, parent=None):
        super().__init__("DOBOT MAGICIAN STATUS", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 6)

        # State banner
        top_bar = QHBoxLayout()
        self.lbl_state = QLabel("IDLE")
        self.lbl_state.setStyleSheet("background-color: #1e293b; color: #22c55e; border: 1px solid #22c55e; border-radius: 4px; padding: 2px 8px; font-weight: bold;")
        top_bar.addWidget(self.lbl_state)

        self.lbl_msg = QLabel("Ready")
        self.lbl_msg.setStyleSheet("color: #94a3b8;")
        top_bar.addWidget(self.lbl_msg, stretch=1)

        self.lbl_suction = QLabel("SUCTION: OFF")
        self.lbl_suction.setStyleSheet("background-color: #1e293b; color: #64748b; padding: 2px 6px; border-radius: 4px;")
        top_bar.addWidget(self.lbl_suction)
        layout.addLayout(top_bar)

        # Coordinates grid (X, Y, Z, R)
        grid = QGridLayout()
        self.labels = {}
        for idx, (axis, unit) in enumerate([("X", "mm"), ("Y", "mm"), ("Z", "mm"), ("R", "deg")]):
            box = QFrame()
            box.setStyleSheet("background-color: #1e293b; border-radius: 4px; padding: 2px;")
            b_lay = QVBoxLayout(box)
            b_lay.setAlignment(ALIGN_CENTER)
            b_lay.addWidget(QLabel(f"{axis} ({unit})"))
            val_lbl = QLabel("0.0")
            val_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
            val_lbl.setAlignment(ALIGN_CENTER)
            b_lay.addWidget(val_lbl)
            self.labels[axis.lower()] = val_lbl
            grid.addWidget(box, 0, idx)

        layout.addLayout(grid)

    def update_status(self, data: dict):
        state = data.get("state", "IDLE").upper()
        self.lbl_state.setText(state)
        self.lbl_msg.setText(data.get("message", ""))

        for axis in ["x", "y", "z", "r"]:
            if axis in data:
                self.labels[axis].setText(f"{float(data[axis]):+.1f}")

        suction = data.get("suction", False)
        if suction:
            self.lbl_suction.setText("SUCTION: ON")
            self.lbl_suction.setStyleSheet("background-color: #22c55e; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: bold;")
        else:
            self.lbl_suction.setText("SUCTION: OFF")
            self.lbl_suction.setStyleSheet("background-color: #1e293b; color: #64748b; padding: 2px 6px; border-radius: 4px;")
