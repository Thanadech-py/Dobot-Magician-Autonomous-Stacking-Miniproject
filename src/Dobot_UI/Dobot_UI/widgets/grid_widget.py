"""Interactive 3x3 Field Grid widget for assigning cube colors and 1st..8th stack orders."""

try:
    from PyQt6.QtWidgets import (
        QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
        QComboBox, QFrame, QPushButton
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
except ImportError:
    from PyQt5.QtWidgets import (
        QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
        QComboBox, QFrame, QPushButton
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    ALIGN_CENTER = Qt.AlignCenter

try:
    from ..config import CELL_DEFAULTS, STACKING
    from ..models import OUTER_CELLS, COLORS, COLOR_HEX, calc_robot_coords
except (ImportError, ValueError):
    from Dobot_UI.config import CELL_DEFAULTS, STACKING
    from Dobot_UI.models import OUTER_CELLS, COLORS, COLOR_HEX, calc_robot_coords


class FieldGridWidget(QGroupBox):
    """3x3 Field Grid containing 8 outer cube cells and the center goal."""
    sequence_changed = pyqtSignal()
    sync_requested   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("FIELD MISSION GRID (3x3)", parent)
        self.cells = {}
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 12, 6, 6)

        grid = QGridLayout()
        grid.setSpacing(6)

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
            for i in range(1, 9):
                combo_order.addItem(f"#{i}", i)
            order_idx = default_orders[idx] if idx < len(default_orders) else 0
            combo_order.setCurrentIndex(order_idx)
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

        # Center goal cell
        goal_card = QFrame()
        goal_card.setStyleSheet("background-color: #2e2612; border: 2px dashed #eab308; border-radius: 6px;")
        g_layout = QVBoxLayout(goal_card)
        g_layout.setAlignment(ALIGN_CENTER)
        lbl_goal = QLabel("🎯\nSTACK GOAL\n(1, 1)")
        lbl_goal.setAlignment(ALIGN_CENTER)
        lbl_goal.setStyleSheet("color: #eab308; font-weight: bold;")
        g_layout.addWidget(lbl_goal)
        grid.addWidget(goal_card, 1, 1)

        root.addLayout(grid)

        btn_bar = QHBoxLayout()
        btn_sync = QPushButton("🔄 Sync from Vision")
        btn_sync.clicked.connect(self.sync_requested.emit)
        btn_bar.addWidget(btn_sync)
        btn_auto = QPushButton("↻ Auto 1..8")
        btn_auto.clicked.connect(self.auto_order)
        btn_bar.addWidget(btn_auto)
        root.addLayout(btn_bar)

    def _on_change(self):
        for c in self.cells.values():
            hex_col = COLOR_HEX.get(c['combo_color'].currentData(), "#334155")
            c['card'].setStyleSheet(f"background-color: #1e293b; border: 2px solid {hex_col}; border-radius: 6px;")
        self.sequence_changed.emit()

    def auto_order(self):
        """Sets orders clockwise starting from Top-Left."""
        for order, cid in enumerate([0, 1, 2, 4, 7, 6, 5, 3], start=1):
            self.cells[cid]['combo_order'].setCurrentIndex(order)
        self._on_change()

    def get_ordered_tasks(self) -> list[dict]:
        """Returns list of tasks sorted by stack order (1..8)."""
        base_z  = float(STACKING.get("base_drop_z_mm", 30.0))
        cube_h  = float(STACKING.get("cube_height_mm", 25.0))
        tasks = []
        for cid, cell in self.cells.items():
            order = cell['combo_order'].currentData()
            if order > 0:
                cfg = cell['config']
                rx, ry, rz = calc_robot_coords(cfg['row'], cfg['col'])
                tasks.append({
                    "order":   order,
                    "cell_id": cid,
                    "row":     cfg['row'],
                    "col":     cfg['col'],
                    "name":    cfg['name'],
                    "color":   cell['combo_color'].currentData(),
                    "pick":    (rx, ry, rz),
                    "drop_z":  base_z + (order - 1) * cube_h,
                })
        tasks.sort(key=lambda t: t['order'])
        return tasks

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
