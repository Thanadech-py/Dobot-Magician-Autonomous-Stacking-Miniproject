"""Dedicated Position Teaching & Storage Widget (Vision Bypass Menu).

Allows operators to manually jog and capture live Dobot arm coordinates for each
grid cell, the center drop goal, and feeders. Stored coordinates are saved to
dobot_ui.yaml and used during mission execution when vision is unavailable.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
        QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
        QCheckBox, QFrame, QRadioButton, QButtonGroup, QAbstractItemView
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QColor
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
except ImportError:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
        QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
        QCheckBox, QFrame, QRadioButton, QButtonGroup, QAbstractItemView
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QColor
    ALIGN_CENTER = Qt.AlignCenter

try:
    from ..config import STORED_POSITIONS, TARGET_OPTIONS, save_stored_positions
except (ImportError, ValueError):
    from Dobot_UI.config import STORED_POSITIONS, TARGET_OPTIONS, save_stored_positions


class TeachWidget(QWidget):
    """Dedicated menu for teaching and saving robot goal coordinates."""

    move_to_requested = pyqtSignal(float, float, float, float)  # x, y, z, r
    jog_requested     = pyqtSignal(str, int, float)             # axis, dir, step
    suction_requested = pyqtSignal(bool)                        # True/False
    positions_updated = pyqtSignal(dict)                        # stored_positions dict
    bypass_toggled    = pyqtSignal(bool)                        # True/False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stored_positions = dict(STORED_POSITIONS)
        self.cur_x = 200.0
        self.cur_y = 0.0
        self.cur_z = 80.0
        self.cur_r = 0.0
        self.suction_state = False
        self.use_stored_positions = bool(self.stored_positions.get("use_stored_positions", True))

        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # 1. Top Header Card: Telemetry & Vision Bypass Toggle
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 6px;")
        h_lay = QVBoxLayout(header_card)
        h_lay.setContentsMargins(8, 8, 8, 8)
        h_lay.setSpacing(4)

        row_top = QHBoxLayout()
        lbl_title = QLabel("📍 POSITION TEACHING & STORAGE")
        lbl_title.setStyleSheet("font-weight: bold; color: #38bdf8; font-size: 12px;")
        row_top.addWidget(lbl_title)

        self.chk_bypass = QCheckBox("⚡ Use Stored Positions in Mission (Vision Bypass)")
        self.chk_bypass.setChecked(self.use_stored_positions)
        self.chk_bypass.setToolTip("When enabled, Stacking Mission uses taught coordinates instead of camera vision")
        self.chk_bypass.setStyleSheet("color: #34d399; font-weight: bold; font-size: 11px;")
        self.chk_bypass.toggled.connect(self._on_bypass_toggled)
        row_top.addWidget(self.chk_bypass, alignment=Qt.AlignmentFlag.AlignRight if hasattr(Qt, "AlignmentFlag") else Qt.AlignRight)
        h_lay.addLayout(row_top)

        row_tele = QHBoxLayout()
        self.lbl_telemetry = QLabel(f"Current Arm Pose: X={self.cur_x:.1f} mm | Y={self.cur_y:.1f} mm | Z={self.cur_z:.1f} mm | R={self.cur_r:.1f}°")
        self.lbl_telemetry.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        row_tele.addWidget(self.lbl_telemetry)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #eab308; font-size: 11px; font-weight: bold;")
        row_tele.addWidget(self.lbl_status, alignment=Qt.AlignmentFlag.AlignRight if hasattr(Qt, "AlignmentFlag") else Qt.AlignRight)
        h_lay.addLayout(row_tele)

        root.addWidget(header_card)

        # 2. Table of Targets with One-Click Teach and Test Move
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Target Goal / Cell", "Stored Coordinate (X, Y, Z)", "Teach Pose", "Test Position"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 105)
        self.table.setColumnWidth(3, 95)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #0f172a; gridline-color: #334155; border: 1px solid #334155; border-radius: 4px; }"
            "QHeaderView::section { background-color: #1e293b; color: #94a3b8; font-weight: bold; border: 1px solid #334155; padding: 4px; }"
        )

        self._populate_table()
        root.addWidget(self.table, stretch=3)

        # 3. Quick Nudge / Jog Toolbar (jog without having to switch tabs)
        nudge_box = QFrame()
        nudge_box.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 6px;")
        n_lay = QHBoxLayout(nudge_box)
        n_lay.setContentsMargins(6, 4, 6, 4)
        n_lay.setSpacing(6)

        lbl_jog = QLabel("Jog Nudge:")
        lbl_jog.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 11px;")
        n_lay.addWidget(lbl_jog)

        self.btn_group_step = QButtonGroup(self)
        self.step_sizes = [1.0, 5.0, 10.0]
        for idx, s in enumerate(self.step_sizes):
            rbtn = QRadioButton(f"{int(s)}mm")
            if s == 5.0:
                rbtn.setChecked(True)
            self.btn_group_step.addButton(rbtn, idx)
            n_lay.addWidget(rbtn)

        n_lay.addSpacing(6)

        jog_btns = [
            ("+X", "x", +1), ("-X", "x", -1),
            ("+Y", "y", +1), ("-Y", "y", -1),
            ("+Z", "z", +1), ("-Z", "z", -1),
        ]
        for label, axis, direction in jog_btns:
            btn = QPushButton(label)
            btn.setFixedSize(38, 26)
            color = "#0284c7" if axis in ("x", "y") else "#059669"
            btn.setStyleSheet(
                f"QPushButton {{ background-color: #0f172a; border: 1px solid {color}; border-radius: 4px; font-weight: bold; font-size: 11px; color: white; }}"
                f"QPushButton:hover {{ background-color: {color}; }}"
            )
            btn.clicked.connect(lambda checked=False, a=axis, d=direction: self._emit_jog(a, d))
            n_lay.addWidget(btn)

        n_lay.addSpacing(6)
        self.btn_suction = QPushButton("💨 Suction")
        self.btn_suction.setCheckable(True)
        self.btn_suction.setFixedHeight(26)
        self.btn_suction.setStyleSheet("background-color: #334155; font-weight: bold; font-size: 10px; padding: 0 8px;")
        self.btn_suction.clicked.connect(self._toggle_suction)
        n_lay.addWidget(self.btn_suction)

        btn_hover = QPushButton("🛡️ Hover")
        btn_hover.setToolTip("Move arm up to safe hover height (Z=80 mm)")
        btn_hover.setFixedHeight(26)
        btn_hover.setStyleSheet("background-color: #334155; font-weight: bold; font-size: 10px; padding: 0 8px;")
        btn_hover.clicked.connect(lambda: self.move_to_requested.emit(self.cur_x, self.cur_y, 80.0, self.cur_r))
        n_lay.addWidget(btn_hover)

        n_lay.addStretch()
        root.addWidget(nudge_box)

        # 4. Bottom Action Bar: Save to YAML & Reset
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        btn_save = QPushButton("💾 Save All Positions to YAML")
        btn_save.setToolTip("Permanently save all taught coordinates into dobot_ui.yaml")
        btn_save.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 8px 16px; font-size: 12px;")
        btn_save.clicked.connect(self._save_to_yaml)
        action_bar.addWidget(btn_save, stretch=2)

        btn_reset = QPushButton("🔄 Reset Defaults")
        btn_reset.setToolTip("Reset coordinates back to config defaults")
        btn_reset.setStyleSheet("background-color: #334155; color: #94a3b8; font-weight: bold; padding: 8px 12px; font-size: 11px;")
        btn_reset.clicked.connect(self._reset_defaults)
        action_bar.addWidget(btn_reset, stretch=1)

        root.addLayout(action_bar)

    # -----------------------------------------------------------------------
    # Table Population & Helpers
    # -----------------------------------------------------------------------

    def _populate_table(self):
        """Populates the target table with buttons for each goal/cell."""
        self.table.setRowCount(len(TARGET_OPTIONS))
        for row_idx, (name, key) in enumerate(TARGET_OPTIONS):
            # Column 0: Target Name
            item_name = QTableWidgetItem(name)
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable if hasattr(Qt, "ItemFlag") else ~Qt.ItemIsEditable)
            if key == "goal":
                item_name.setForeground(QColor("#eab308"))
            else:
                item_name.setForeground(QColor("#f1f5f9"))
            self.table.setItem(row_idx, 0, item_name)

            # Column 1: Coordinate readout
            pos = self.stored_positions.get(key, [200.0, 0.0, 30.0])
            coord_str = f"X: {pos[0]:.1f} | Y: {pos[1]:.1f} | Z: {pos[2]:.1f}"
            item_coord = QTableWidgetItem(coord_str)
            item_coord.setTextAlignment(ALIGN_CENTER)
            item_coord.setForeground(QColor("#38bdf8"))
            self.table.setItem(row_idx, 1, item_coord)

            # Column 2: Teach Button
            btn_teach = QPushButton("📍 Teach")
            btn_teach.setToolTip(f"Store live arm pose into {name}")
            btn_teach.setStyleSheet(
                "QPushButton { background-color: #0284c7; color: white; font-weight: bold; padding: 3px 6px; border-radius: 3px; font-size: 11px; }"
                "QPushButton:hover { background-color: #0369a1; }"
            )
            btn_teach.clicked.connect(lambda checked=False, k=key, r=row_idx, n=name: self._teach_target(k, r, n))
            self.table.setCellWidget(row_idx, 2, btn_teach)

            # Column 3: Test Move Button
            btn_test = QPushButton("🚀 Go To")
            btn_test.setToolTip(f"Move arm to stored coordinate of {name}")
            btn_test.setStyleSheet(
                "QPushButton { background-color: #334155; color: white; font-weight: bold; padding: 3px 6px; border-radius: 3px; font-size: 11px; }"
                "QPushButton:hover { background-color: #475569; }"
            )
            btn_test.clicked.connect(lambda checked=False, k=key: self._test_target(k))
            self.table.setCellWidget(row_idx, 3, btn_test)

    def _teach_target(self, key: str, row_idx: int, name: str):
        """Stores current live arm coordinates to the target."""
        x = round(float(self.cur_x), 1)
        y = round(float(self.cur_y), 1)
        z = round(float(self.cur_z), 1)
        self.stored_positions[key] = [x, y, z]

        coord_str = f"X: {x:.1f} | Y: {y:.1f} | Z: {z:.1f}"
        item = self.table.item(row_idx, 1)
        if item:
            item.setText(coord_str)
            item.setForeground(QColor("#4ade80"))  # flash green

        self.lbl_status.setText(f"✓ Taught {name}: ({x:.1f}, {y:.1f}, {z:.1f})")
        self.lbl_status.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: bold;")
        self.positions_updated.emit(self.stored_positions)

    def _test_target(self, key: str):
        """Moves robot arm to stored target coordinate."""
        pos = self.stored_positions.get(key)
        if pos and len(pos) >= 3:
            self.move_to_requested.emit(float(pos[0]), float(pos[1]), float(pos[2]), 0.0)
            self.lbl_status.setText(f"🚀 Moving to {key}: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})")
            self.lbl_status.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold;")

    def _save_to_yaml(self):
        """Saves current stored positions permanently to dobot_ui.yaml."""
        saved = save_stored_positions(self.stored_positions)
        if saved:
            self.lbl_status.setText("✓ All positions saved to dobot_ui.yaml successfully!")
            self.lbl_status.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: bold;")
        else:
            self.lbl_status.setText("⚠️ Failed to write to dobot_ui.yaml")
            self.lbl_status.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: bold;")

    def _reset_defaults(self):
        """Resets positions to default config values."""
        from Dobot_UI.config import DEFAULT_CONFIG
        defaults = DEFAULT_CONFIG.get("stored_positions", {})
        self.stored_positions.update(defaults)
        for row_idx, (name, key) in enumerate(TARGET_OPTIONS):
            pos = self.stored_positions.get(key, [200.0, 0.0, 30.0])
            item = self.table.item(row_idx, 1)
            if item:
                item.setText(f"X: {pos[0]:.1f} | Y: {pos[1]:.1f} | Z: {pos[2]:.1f}")
                item.setForeground(QColor("#38bdf8"))
        self.lbl_status.setText("Defaults restored. Click 'Save All' to persist.")
        self.lbl_status.setStyleSheet("color: #eab308; font-size: 11px; font-weight: bold;")
        self.positions_updated.emit(self.stored_positions)

    def _emit_jog(self, axis: str, direction: int):
        btn_id = self.btn_group_step.checkedId()
        step = self.step_sizes[btn_id] if 0 <= btn_id < len(self.step_sizes) else 5.0
        self.jog_requested.emit(axis, direction, step)

    def _toggle_suction(self):
        new_state = self.btn_suction.isChecked()
        self.suction_state = new_state
        if new_state:
            self.btn_suction.setText("💨 Suction: ON")
            self.btn_suction.setStyleSheet("background-color: #22c55e; color: white; font-weight: bold; font-size: 10px; padding: 0 8px;")
        else:
            self.btn_suction.setText("💨 Suction: OFF")
            self.btn_suction.setStyleSheet("background-color: #334155; font-weight: bold; font-size: 10px; padding: 0 8px;")
        self.suction_requested.emit(new_state)

    def _on_bypass_toggled(self, checked: bool):
        self.use_stored_positions = checked
        self.stored_positions["use_stored_positions"] = checked
        self.bypass_toggled.emit(checked)
        self.positions_updated.emit(self.stored_positions)

    # -----------------------------------------------------------------------
    # Public Slots
    # -----------------------------------------------------------------------

    def update_telemetry(self, data: dict):
        """Updates internal live telemetry state and display."""
        if "x" in data:
            try: self.cur_x = float(data["x"])
            except (ValueError, TypeError): pass
        if "y" in data:
            try: self.cur_y = float(data["y"])
            except (ValueError, TypeError): pass
        if "z" in data:
            try: self.cur_z = float(data["z"])
            except (ValueError, TypeError): pass
        if "r" in data:
            try: self.cur_r = float(data["r"])
            except (ValueError, TypeError): pass

        self.lbl_telemetry.setText(
            f"Current Arm Pose: X={self.cur_x:.1f} mm | Y={self.cur_y:.1f} mm | Z={self.cur_z:.1f} mm | R={self.cur_r:.1f}°"
        )

    def set_stored_positions(self, positions: dict):
        """Synchronizes stored positions from another source."""
        self.stored_positions.update(positions)
        for row_idx, (name, key) in enumerate(TARGET_OPTIONS):
            pos = self.stored_positions.get(key)
            if pos and len(pos) >= 3:
                item = self.table.item(row_idx, 1)
                if item:
                    item.setText(f"X: {pos[0]:.1f} | Y: {pos[1]:.1f} | Z: {pos[2]:.1f}")
        if "use_stored_positions" in positions:
            b = bool(positions["use_stored_positions"])
            self.use_stored_positions = b
            self.chk_bypass.setChecked(b)

    def set_bypass_mode(self, enabled: bool):
        """Updates bypass checkbox state."""
        if self.chk_bypass.isChecked() != enabled:
            self.chk_bypass.setChecked(enabled)
