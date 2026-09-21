"""Interactive 3x3 Field Grid widget for assigning cube colors, goal stack orders, and obstacle feeder slots."""

try:
    from PyQt6.QtWidgets import (
        QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
        QComboBox, QFrame, QPushButton, QCheckBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
except ImportError:
    from PyQt5.QtWidgets import (
        QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
        QComboBox, QFrame, QPushButton, QCheckBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    ALIGN_CENTER = Qt.AlignCenter

try:
    from ..config import CELL_DEFAULTS, STACKING, STORED_POSITIONS, GRID
    from ..models import OUTER_CELLS, COLORS, COLOR_HEX, calc_robot_coords
except (ImportError, ValueError):
    from Dobot_UI.config import CELL_DEFAULTS, STACKING, STORED_POSITIONS, GRID
    from Dobot_UI.models import OUTER_CELLS, COLORS, COLOR_HEX, calc_robot_coords


class FieldGridWidget(QGroupBox):
    """3x3 Field Grid containing 8 outer cube cells and the center goal.
    Supports assigning up to 4 blocks to the Goal stack and other blocks as Obstacles to Feeders 1..4.
    """
    sequence_changed = pyqtSignal()
    sync_requested   = pyqtSignal()
    bypass_toggled   = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__("FIELD MISSION GRID (3x3)", parent)
        self.cells = {}
        self.stored_positions = dict(STORED_POSITIONS)
        self.use_stored_positions = bool(self.stored_positions.get("use_stored_positions", True))
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 12, 6, 6)
        root.setSpacing(6)

        grid = QGridLayout()
        grid.setSpacing(6)

        max_blocks = int(STACKING.get("max_stack_blocks", 4))
        default_orders = CELL_DEFAULTS.get("orders", [1, 2, 3, 4, 5, 6, 7, 8])
        sample_colors  = CELL_DEFAULTS.get("colors", ["red", "yellow", "green", "blue", "orange", "purple", "cyan", "red"])

        for idx, item in enumerate(OUTER_CELLS):
            card = QFrame()
            card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 6px;")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(4, 4, 4, 4)
            c_layout.setSpacing(2)

            lbl = QLabel(f"[{item['row']},{item['col']}] {item['short']}")
            lbl.setAlignment(ALIGN_CENTER)
            lbl.setStyleSheet("font-weight: bold; color: #94a3b8;")
            c_layout.addWidget(lbl)

            combo_order = QComboBox()
            combo_order.addItem("None", 0)
            # Goal Stacking options (1..4)
            for i in range(1, max_blocks + 1):
                combo_order.addItem(f"#{i} (Goal)", i)
            # Obstacle to Feeder options (5..8 -> Feeders 1..4)
            for f in range(1, 5):
                combo_order.addItem(f"Obs #{f} (Feeder {f})", 4 + f)

            order_idx = default_orders[idx] if idx < len(default_orders) else 0
            if order_idx < combo_order.count():
                combo_order.setCurrentIndex(order_idx)
            else:
                combo_order.setCurrentIndex(0)

            combo_order.currentIndexChanged.connect(self._on_change)
            c_layout.addWidget(combo_order)

            combo_color = QComboBox()
            for c in COLORS:
                combo_color.addItem(c.capitalize(), c)
            col_name = sample_colors[idx] if idx < len(sample_colors) else "none"
            combo_color.setCurrentText(col_name.capitalize())
            combo_color.currentIndexChanged.connect(self._on_change)
            c_layout.addWidget(combo_color)

            grid.addWidget(card, item['row'], item['col'])
            self.cells[item['id']] = {
                'config': item,
                'combo_order': combo_order,
                'combo_color': combo_color,
                'card': card
            }

        # Center goal cell (Locked to 4 blocks max)
        goal_card = QFrame()
        goal_card.setStyleSheet("background-color: #2e2612; border: 2px dashed #eab308; border-radius: 6px;")
        g_layout = QVBoxLayout(goal_card)
        g_layout.setAlignment(ALIGN_CENTER)
        lbl_goal = QLabel(f"🎯\nSTACK GOAL\n(Max {max_blocks} Blocks)\n(1, 1)")
        lbl_goal.setAlignment(ALIGN_CENTER)
        lbl_goal.setStyleSheet("color: #eab308; font-weight: bold;")
        g_layout.addWidget(lbl_goal)
        grid.addWidget(goal_card, 1, 1)

        root.addLayout(grid)

        # Bottom toolbar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(6)

        self.chk_bypass = QCheckBox("⚡ Use Stored Coordinates (Vision Bypass)")
        self.chk_bypass.setChecked(self.use_stored_positions)
        self.chk_bypass.setToolTip("When checked, missions use taught coordinates from the 'Teach Positions' menu")
        self.chk_bypass.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")
        self.chk_bypass.toggled.connect(self._on_bypass_toggled)
        btn_bar.addWidget(self.chk_bypass)

        btn_sync = QPushButton("🔄 Sync Vision")
        btn_sync.setToolTip("Detect cubes from camera stream and update cell colors")
        btn_sync.clicked.connect(self.sync_requested.emit)
        btn_bar.addWidget(btn_sync)

        btn_auto_goal = QPushButton("↻ Auto 1..4 (Goal)")
        btn_auto_goal.setToolTip("Assign orders #1 to #4 clockwise to Goal and clear other cells")
        btn_auto_goal.clicked.connect(self.auto_order_goal_only)
        btn_bar.addWidget(btn_auto_goal)

        btn_auto_all = QPushButton("↻ Auto All (4 Goal + 4 Obs)")
        btn_auto_all.setToolTip("Assign 4 Goal cubes (#1..#4) and 4 Obstacles to Feeders 1..4")
        btn_auto_all.clicked.connect(self.auto_order_all)
        btn_bar.addWidget(btn_auto_all)

        btn_auto_obs = QPushButton("🧹 Auto Obs")
        btn_auto_obs.setToolTip("Assign remaining non-empty cells to available Feeders 1..4")
        btn_auto_obs.clicked.connect(self.auto_assign_obstacles)
        btn_bar.addWidget(btn_auto_obs)

        root.addLayout(btn_bar)

    def _on_change(self):
        for c in self.cells.values():
            hex_col = COLOR_HEX.get(c['combo_color'].currentData(), "#334155")
            order_data = c['combo_order'].currentData()
            if 1 <= order_data <= 4:
                # Goal border: solid bright color
                c['card'].setStyleSheet(f"background-color: #1e293b; border: 2px solid {hex_col}; border-radius: 6px;")
            elif 5 <= order_data <= 8:
                # Obstacle border: dashed orange warning
                c['card'].setStyleSheet(f"background-color: #261e12; border: 2px dashed #f97316; border-radius: 6px;")
            else:
                c['card'].setStyleSheet(f"background-color: #1e293b; border: 1px solid #334155; border-radius: 6px;")
        self.sequence_changed.emit()

    def _on_bypass_toggled(self, checked: bool):
        self.use_stored_positions = checked
        self.stored_positions["use_stored_positions"] = checked
        self.bypass_toggled.emit(checked)
        self.sequence_changed.emit()

    def set_bypass_mode(self, enabled: bool):
        if self.chk_bypass.isChecked() != enabled:
            self.chk_bypass.setChecked(enabled)

    def set_stored_positions(self, positions: dict):
        self.stored_positions.update(positions)
        if "use_stored_positions" in positions:
            self.set_bypass_mode(bool(positions["use_stored_positions"]))
        self.sequence_changed.emit()

    def auto_order_goal_only(self):
        """Sets orders clockwise for 4 Goal blocks only, clearing other cells."""
        cw_ids = [0, 1, 2, 4, 7, 6, 5, 3]
        for cid in self.cells:
            self.cells[cid]['combo_order'].setCurrentIndex(0)
        for order, cid in enumerate(cw_ids[:4], start=1):
            if cid in self.cells:
                self.cells[cid]['combo_order'].setCurrentIndex(order)
        self._on_change()

    def auto_order_all(self):
        """Sets 4 Goal blocks (#1..#4) and 4 Obstacle blocks to Feeders 1..4."""
        cw_ids = [0, 1, 2, 4, 7, 6, 5, 3]
        for cid in self.cells:
            self.cells[cid]['combo_order'].setCurrentIndex(0)
        for order, cid in enumerate(cw_ids, start=1):
            if cid in self.cells:
                self.cells[cid]['combo_order'].setCurrentIndex(order)
        self._on_change()

    def auto_order(self):
        """Default auto-order delegates to auto_order_all."""
        self.auto_order_all()

    def auto_assign_obstacles(self):
        """Assigns any cells with colored cubes that are not in Goal (#1..#4) to available Feeders 1..4."""
        assigned_feeders = set()
        for c in self.cells.values():
            val = c['combo_order'].currentData()
            if 5 <= val <= 8:
                assigned_feeders.add(val - 4)

        next_feeder = 1
        for cid, c in self.cells.items():
            val = c['combo_order'].currentData()
            color = c['combo_color'].currentData()
            if (val == 0 or val is None) and color != "none":
                while next_feeder in assigned_feeders and next_feeder <= 4:
                    next_feeder += 1
                if next_feeder <= 4:
                    idx = c['combo_order'].findData(next_feeder + 4)
                    if idx >= 0:
                        c['combo_order'].setCurrentIndex(idx)
                        assigned_feeders.add(next_feeder)
        self._on_change()

    def get_ordered_tasks(self) -> list[dict]:
        """Returns list of all mission tasks across all 3 phases:
        Phase 1: Clear obstacle cubes to Feeders 1..4
        Phase 2: Stack target cubes (locked to max 4) on Center Goal [1, 1]
        Phase 3: Restore obstacle cubes from Feeders 1..4 back to original grid positions
        """
        max_blocks = int(STACKING.get("max_stack_blocks", 4))
        base_z = float(STACKING.get("base_drop_z_mm", 30.0))
        cube_h = float(STACKING.get("cube_height_mm", 25.0))
        pick_z = float(GRID.get("pick_z_mm", 12.5))

        # Goal position (taught or default)
        goal_pt = self.stored_positions.get("goal", [176.0, 0.0, base_z])
        gx = float(goal_pt[0])
        gy = float(goal_pt[1])
        gz = float(goal_pt[2])

        # Feeder positions (taught or default)
        feeder_pts = {}
        for fid in range(1, 5):
            f_key = f"feeder_{fid}"
            f_def = STORED_POSITIONS.get(f_key, [219.8 - (fid - 1) * 32.0, 79.3, pick_z])
            pt = self.stored_positions.get(f_key, f_def)
            feeder_pts[fid] = (float(pt[0]), float(pt[1]), float(pt[2]))

        goal_cells = []
        obstacle_cells = []

        for cid, cell in self.cells.items():
            order_data = cell['combo_order'].currentData()
            color = cell['combo_color'].currentData()
            if not order_data or order_data == 0:
                continue

            cfg = cell['config']
            if self.use_stored_positions:
                stored_pt = self.stored_positions.get(f"cell_{cid}")
                if stored_pt and len(stored_pt) >= 3:
                    rx, ry, rz = float(stored_pt[0]), float(stored_pt[1]), float(stored_pt[2])
                else:
                    rx, ry, rz = calc_robot_coords(cfg['row'], cfg['col'])
            else:
                rx, ry, rz = calc_robot_coords(cfg['row'], cfg['col'])

            if 1 <= order_data <= 4:
                goal_cells.append({
                    "order": order_data,
                    "cell_id": cid,
                    "row": cfg['row'],
                    "col": cfg['col'],
                    "name": cfg['name'],
                    "color": color,
                    "pos": (rx, ry, rz)
                })
            elif 5 <= order_data <= 8:
                f_id = order_data - 4
                obstacle_cells.append({
                    "order": order_data,
                    "feeder_id": f_id,
                    "cell_id": cid,
                    "row": cfg['row'],
                    "col": cfg['col'],
                    "name": cfg['name'],
                    "color": color,
                    "origin_pos": (rx, ry, rz),
                    "feeder_pos": feeder_pts[f_id]
                })

        # Strictly sort and clamp goal cells to max_blocks (4)
        goal_cells.sort(key=lambda x: x["order"])
        goal_cells = goal_cells[:max_blocks]

        # Sort obstacles by feeder_id
        obstacle_cells.sort(key=lambda x: x["feeder_id"])
        obstacle_cells = obstacle_cells[:4]

        all_tasks = []

        # ── Phase 1: Clear Obstacles to Feeders ──
        for obs in obstacle_cells:
            f_num = obs["feeder_id"]
            fx, fy, fz = obs["feeder_pos"]
            ox, oy, oz = obs["origin_pos"]
            all_tasks.append({
                "phase": 1,
                "phase_name": "Clear Obstacle",
                "action": "clear_to_feeder",
                "order": obs["order"],
                "cell_id": obs["cell_id"],
                "cell_name": f"[{obs['row']},{obs['col']}] {obs['name']}",
                "feeder_id": f_num,
                "feeder_name": f"Feeder {f_num}",
                "color": obs["color"],
                "pick": (ox, oy, oz),
                "drop": (fx, fy, fz),
                "drop_z": fz,
                "origin": (ox, oy, oz),
            })

        # ── Phase 2: Stacking onto Center Goal (Max 4) ──
        for idx, g in enumerate(goal_cells):
            target_z = gz + (idx * cube_h)
            ox, oy, oz = g["pos"]
            all_tasks.append({
                "phase": 2,
                "phase_name": "Stack Goal",
                "action": "stack_goal",
                "order": g["order"],
                "cell_id": g["cell_id"],
                "cell_name": f"[{g['row']},{g['col']}] {g['name']}",
                "color": g["color"],
                "pick": (ox, oy, oz),
                "drop": (gx, gy, gz),
                "drop_z": target_z,
                "stack_level": idx + 1,
            })

        # ── Phase 3: Restore Obstacles from Feeders to Origin ──
        for obs in obstacle_cells:
            f_num = obs["feeder_id"]
            fx, fy, fz = obs["feeder_pos"]
            ox, oy, oz = obs["origin_pos"]
            all_tasks.append({
                "phase": 3,
                "phase_name": "Restore Obstacle",
                "action": "restore_from_feeder",
                "order": obs["order"],
                "cell_id": obs["cell_id"],
                "cell_name": f"[{obs['row']},{obs['col']}] {obs['name']}",
                "feeder_id": f_num,
                "feeder_name": f"Feeder {f_num}",
                "color": obs["color"],
                "pick": (fx, fy, fz),
                "drop": (ox, oy, oz),
                "drop_z": oz,
                "origin": (ox, oy, oz),
            })

        return all_tasks

    def sync_vision(self, detected_objects: list):
        """Auto-updates cube colors from vision detection."""
        for obj in detected_objects:
            cell_info = obj.get("cell")
            if not cell_info:
                continue
            r, c = cell_info.get("row"), cell_info.get("col")
            color = obj.get("color", "none").lower()
            for cell in self.cells.values():
                if cell['config']['row'] == r and cell['config']['col'] == c:
                    idx = cell['combo_color'].findData(color)
                    if idx >= 0:
                        cell['combo_color'].setCurrentIndex(idx)
        self._on_change()
