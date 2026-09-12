"""Manual Control Widget for Dobot Magician.

Provides Cartesian jogging (X, Y, Z, R), step size selection,
direct coordinate go-to (PTP), end-effector tool control (suction/gripper),
and quick presets for testing and manual operation.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
        QPushButton, QDoubleSpinBox, QSlider, QRadioButton, QButtonGroup,
        QScrollArea, QFrame
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
except ImportError:
    from PyQt5.QtWidgets import (
        QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
        QPushButton, QDoubleSpinBox, QSlider, QRadioButton, QButtonGroup,
        QScrollArea, QFrame
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    ALIGN_CENTER = Qt.AlignCenter


class ManualControlWidget(QWidget):
    """Manual jogging and tool control interface for Dobot Magician."""

    # Signals emitted to main window / ROS bridge
    jog_requested = pyqtSignal(str, int, float)  # (axis: 'x'|'y'|'z'|'r', direction: +1|-1, step: float)
    move_to_requested = pyqtSignal(float, float, float, float)  # (x, y, z, r)
    suction_requested = pyqtSignal(bool)  # True = ON, False = OFF
    gripper_requested = pyqtSignal(bool)  # True = Close/Grip, False = Open/Release
    preset_requested = pyqtSignal(str)    # 'home' | 'hover' | 'dropoff' | 'zero_r'
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Current tracked pose (from telemetry)
        self.cur_x = 200.0
        self.cur_y = 0.0
        self.cur_z = 80.0
        self.cur_r = 0.0
        self.suction_state = False
        self.gripper_state = False

        self._init_ui()

    def _init_ui(self):
        # Top-level scroll area to fit on any screen resolution
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll_off = Qt.ScrollBarPolicy.ScrollBarAlwaysOff if hasattr(Qt, "ScrollBarPolicy") else Qt.ScrollBarAlwaysOff
        scroll.setHorizontalScrollBarPolicy(scroll_off)
        scroll.setFrameShape(QFrame.Shape.NoFrame if hasattr(QFrame, "Shape") else QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # 1. Quick Presets Section
        layout.addWidget(self._build_presets_group())

        # 2. Cartesian Jogging Section (D-Pad + Z + R + Step Selection)
        layout.addWidget(self._build_jog_group())

        # 3. End-Effector Control (Suction & Gripper)
        layout.addWidget(self._build_effector_group())

        # 4. Target Coordinate Move-To (PTP)
        layout.addWidget(self._build_move_to_group())

        layout.addStretch()

        scroll.setWidget(container)

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(scroll)

    # -----------------------------------------------------------------------
    # Section Builders
    # -----------------------------------------------------------------------

    def _build_presets_group(self) -> QGroupBox:
        box = QGroupBox("QUICK PRESETS")
        h_lay = QHBoxLayout(box)
        h_lay.setContentsMargins(8, 12, 8, 8)
        h_lay.setSpacing(6)

        presets = [
            ("🏠 Home", "home", "Home position"),
            ("🛡️ Hover", "hover", "Safe hover height (Z=80 mm)"),
            ("📦 Drop-off", "dropoff", "Drop-off position (Z=30 mm)"),
            ("🔄 Zero R", "zero_r", "Reset wrist rotation to 0°"),
        ]

        for label, cmd_name, tip in presets:
            btn = QPushButton(label)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda checked=False, name=cmd_name: self.preset_requested.emit(name))
            h_lay.addWidget(btn)

        return box

    def _build_jog_group(self) -> QGroupBox:
        box = QGroupBox("CARTESIAN JOG")
        v_lay = QVBoxLayout(box)
        v_lay.setContentsMargins(8, 12, 8, 8)
        v_lay.setSpacing(8)

        # --- Step size selection ---
        step_row = QHBoxLayout()
        step_label = QLabel("Linear Step:")
        step_label.setStyleSheet("color: #94a3b8; font-weight: bold;")
        step_row.addWidget(step_label)

        self.btn_group_step = QButtonGroup(self)
        self.step_sizes = [1.0, 5.0, 10.0, 50.0]
        for idx, s in enumerate(self.step_sizes):
            rbtn = QRadioButton(f"{int(s)} mm")
            if s == 10.0:
                rbtn.setChecked(True)
            self.btn_group_step.addButton(rbtn, idx)
            step_row.addWidget(rbtn)

        step_row.addSpacing(10)
        r_step_label = QLabel("Rot Step:")
        r_step_label.setStyleSheet("color: #94a3b8; font-weight: bold;")
        step_row.addWidget(r_step_label)

        self.spin_rot_step = QDoubleSpinBox()
        self.spin_rot_step.setRange(1.0, 90.0)
        self.spin_rot_step.setValue(5.0)
        self.spin_rot_step.setSuffix("°")
        self.spin_rot_step.setFixedWidth(70)
        step_row.addWidget(self.spin_rot_step)

        step_row.addStretch()
        v_lay.addLayout(step_row)

        # --- Jog Controls Grid (XY Cross, Z column, R column) ---
        ctrl_grid = QGridLayout()
        ctrl_grid.setSpacing(6)

        # XY D-Pad
        lbl_xy = QLabel("XY Plane")
        lbl_xy.setAlignment(ALIGN_CENTER)
        lbl_xy.setStyleSheet("color: #38bdf8; font-weight: bold;")
        ctrl_grid.addWidget(lbl_xy, 0, 0, 1, 3)

        btn_xp = self._create_jog_btn("▲ +X", "#0284c7")
        btn_xp.setToolTip("Move Forward (+X)")
        btn_xp.clicked.connect(lambda: self._emit_jog("x", +1))
        ctrl_grid.addWidget(btn_xp, 1, 1)

        btn_yl = self._create_jog_btn("◀ +Y", "#0284c7")
        btn_yl.setToolTip("Move Left (+Y)")
        btn_yl.clicked.connect(lambda: self._emit_jog("y", +1))
        ctrl_grid.addWidget(btn_yl, 2, 0)

        center_info = QLabel("XY")
        center_info.setAlignment(ALIGN_CENTER)
        center_info.setStyleSheet("color: #64748b; font-weight: bold; background-color: #1e293b; border-radius: 4px; padding: 4px;")
        ctrl_grid.addWidget(center_info, 2, 1)

        btn_yr = self._create_jog_btn("-Y ▶", "#0284c7")
        btn_yr.setToolTip("Move Right (-Y)")
        btn_yr.clicked.connect(lambda: self._emit_jog("y", -1))
        ctrl_grid.addWidget(btn_yr, 2, 2)

        btn_xm = self._create_jog_btn("▼ -X", "#0284c7")
        btn_xm.setToolTip("Move Backward (-X)")
        btn_xm.clicked.connect(lambda: self._emit_jog("x", -1))
        ctrl_grid.addWidget(btn_xm, 3, 1)

        # Separator spacing
        ctrl_grid.setColumnMinimumWidth(3, 10)

        # Z Axis controls
        lbl_z = QLabel("Z Axis")
        lbl_z.setAlignment(ALIGN_CENTER)
        lbl_z.setStyleSheet("color: #38bdf8; font-weight: bold;")
        ctrl_grid.addWidget(lbl_z, 0, 4)

        btn_zp = self._create_jog_btn("▲ +Z", "#059669")
        btn_zp.setToolTip("Move Up (+Z)")
        btn_zp.clicked.connect(lambda: self._emit_jog("z", +1))
        ctrl_grid.addWidget(btn_zp, 1, 4)

        btn_zm = self._create_jog_btn("▼ -Z", "#059669")
        btn_zm.setToolTip("Move Down (-Z)")
        btn_zm.clicked.connect(lambda: self._emit_jog("z", -1))
        ctrl_grid.addWidget(btn_zm, 3, 4)

        # Separator spacing
        ctrl_grid.setColumnMinimumWidth(5, 10)

        # R Wrist rotation controls
        lbl_r = QLabel("R Wrist")
        lbl_r.setAlignment(ALIGN_CENTER)
        lbl_r.setStyleSheet("color: #38bdf8; font-weight: bold;")
        ctrl_grid.addWidget(lbl_r, 0, 6)

        btn_rm = self._create_jog_btn("↺ R-", "#7c3aed")
        btn_rm.setToolTip("Rotate CCW (-R)")
        btn_rm.clicked.connect(lambda: self._emit_jog("r", -1))
        ctrl_grid.addWidget(btn_rm, 1, 6)

        btn_rp = self._create_jog_btn("↻ R+", "#7c3aed")
        btn_rp.setToolTip("Rotate CW (+R)")
        btn_rp.clicked.connect(lambda: self._emit_jog("r", +1))
        ctrl_grid.addWidget(btn_rp, 3, 6)

        v_lay.addLayout(ctrl_grid)
        return box

    def _build_effector_group(self) -> QGroupBox:
        box = QGroupBox("END-EFFECTOR TOOL CONTROL")
        h_lay = QHBoxLayout(box)
        h_lay.setContentsMargins(6, 8, 6, 6)
        h_lay.setSpacing(10)

        # Suction Cup Toggle Button
        self.btn_suction = QPushButton("💨 SUCTION: OFF")
        self.btn_suction.setCheckable(True)
        self.btn_suction.setStyleSheet(
            "background-color: #1e293b; color: #94a3b8; font-weight: bold; padding: 8px 16px; border: 1px solid #334155;"
        )
        self.btn_suction.clicked.connect(self._on_suction_clicked)
        h_lay.addWidget(self.btn_suction, stretch=1)

        # Gripper Toggle Buttons
        self.btn_grip = QPushButton("✊ GRIP")
        self.btn_grip.setToolTip("Close gripper")
        self.btn_grip.setStyleSheet("background-color: #334155; font-weight: bold; padding: 8px 12px;")
        self.btn_grip.clicked.connect(lambda: self.gripper_requested.emit(True))
        h_lay.addWidget(self.btn_grip, stretch=1)

        self.btn_release = QPushButton("🖐️ RELEASE")
        self.btn_release.setToolTip("Open gripper")
        self.btn_release.setStyleSheet("background-color: #334155; font-weight: bold; padding: 8px 12px;")
        self.btn_release.clicked.connect(lambda: self.gripper_requested.emit(False))
        h_lay.addWidget(self.btn_release, stretch=1)

        return box

    def _build_move_to_group(self) -> QGroupBox:
        box = QGroupBox("DIRECT POSITION (MOVE TO)")
        v_lay = QVBoxLayout(box)
        v_lay.setContentsMargins(6, 8, 6, 6)
        v_lay.setSpacing(6)

        # Coordinate inputs
        grid = QGridLayout()
        grid.setSpacing(6)

        self.spins = {}
        axes = [
            ("X (mm)", "x", 100.0, 330.0, 200.0),
            ("Y (mm)", "y", -250.0, 250.0, 0.0),
            ("Z (mm)", "z", -60.0, 160.0, 80.0),
            ("R (°)",  "r", -180.0, 180.0, 0.0),
        ]

        for col, (label, key, min_val, max_val, def_val) in enumerate(axes):
            lbl = QLabel(label)
            lbl.setAlignment(ALIGN_CENTER)
            lbl.setStyleSheet("color: #94a3b8; font-weight: bold;")
            grid.addWidget(lbl, 0, col)

            spin = QDoubleSpinBox()
            spin.setRange(min_val, max_val)
            spin.setSingleStep(1.0 if key != "r" else 5.0)
            spin.setDecimals(1)
            spin.setValue(def_val)
            spin.setAlignment(ALIGN_CENTER)
            grid.addWidget(spin, 1, col)
            self.spins[key] = spin

        v_lay.addLayout(grid)

        # Buttons: Read Current Pose & Go To Target
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_copy = QPushButton("📥 Copy Pose")
        btn_copy.setToolTip("Fill coordinate inputs with current live robot position")
        btn_copy.clicked.connect(self._copy_current_pose)
        btn_row.addWidget(btn_copy)

        btn_goto = QPushButton("🚀 Move To")
        btn_goto.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 6px 14px;")
        btn_goto.clicked.connect(self._on_goto_clicked)
        btn_row.addWidget(btn_goto)

        btn_stop = QPushButton("🛑 Stop")
        btn_stop.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold; padding: 6px 14px;")
        btn_stop.clicked.connect(self.stop_requested.emit)
        btn_row.addWidget(btn_stop)

        v_lay.addLayout(btn_row)
        return box

    # -----------------------------------------------------------------------
    # Internal Helpers & Signal Handlers
    # -----------------------------------------------------------------------

    def _create_jog_btn(self, text: str, border_color: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: #1e293b; border: 1px solid {border_color}; "
            f"border-radius: 4px; padding: 6px 8px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {border_color}; color: white; }}"
        )
        return btn

    def _get_linear_step(self) -> float:
        btn_id = self.btn_group_step.checkedId()
        if 0 <= btn_id < len(self.step_sizes):
            return self.step_sizes[btn_id]
        return 10.0

    def _emit_jog(self, axis: str, direction: int):
        if axis == "r":
            step = float(self.spin_rot_step.value())
        else:
            step = self._get_linear_step()
        self.jog_requested.emit(axis, direction, step)

    def _on_suction_clicked(self):
        new_state = self.btn_suction.isChecked()
        self.suction_state = new_state
        self._update_suction_button_visual(new_state)
        self.suction_requested.emit(new_state)

    def _update_suction_button_visual(self, state: bool):
        if state:
            self.btn_suction.setText("💨 SUCTION: ON")
            self.btn_suction.setChecked(True)
            self.btn_suction.setStyleSheet(
                "background-color: #22c55e; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px;"
            )
        else:
            self.btn_suction.setText("💨 SUCTION: OFF")
            self.btn_suction.setChecked(False)
            self.btn_suction.setStyleSheet(
                "background-color: #1e293b; color: #94a3b8; font-weight: bold; padding: 8px 16px; border: 1px solid #334155; border-radius: 4px;"
            )

    def _copy_current_pose(self):
        self.spins["x"].setValue(self.cur_x)
        self.spins["y"].setValue(self.cur_y)
        self.spins["z"].setValue(self.cur_z)
        self.spins["r"].setValue(self.cur_r)

    def _on_goto_clicked(self):
        x = float(self.spins["x"].value())
        y = float(self.spins["y"].value())
        z = float(self.spins["z"].value())
        r = float(self.spins["r"].value())
        self.move_to_requested.emit(x, y, z, r)

    # -----------------------------------------------------------------------
    # Public Slot: Telemetry Updates
    # -----------------------------------------------------------------------

    def update_telemetry(self, data: dict):
        """Receives live telemetry dict from ROS bridge and updates internal state."""
        if "x" in data:
            try:
                self.cur_x = float(data["x"])
            except (ValueError, TypeError):
                pass
        if "y" in data:
            try:
                self.cur_y = float(data["y"])
            except (ValueError, TypeError):
                pass
        if "z" in data:
            try:
                self.cur_z = float(data["z"])
            except (ValueError, TypeError):
                pass
        if "r" in data:
            try:
                self.cur_r = float(data["r"])
            except (ValueError, TypeError):
                pass

        if "suction" in data:
            is_suction = bool(data["suction"])
            if is_suction != self.suction_state:
                self.suction_state = is_suction
                self._update_suction_button_visual(is_suction)
