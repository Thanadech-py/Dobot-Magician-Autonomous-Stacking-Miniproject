"""Mission execution plan table displaying multi-phase operations:
Phase 1: Clear Obstacles to Feeders 1..4
Phase 2: Stack Goal Blocks (Locked to Max 4)
Phase 3: Restore Obstacles from Feeders 1..4 to Origin Positions
"""

try:
    from PyQt6.QtWidgets import (
        QGroupBox, QVBoxLayout, QHBoxLayout, QTableWidget,
        QTableWidgetItem, QHeaderView, QPushButton, QLabel,
        QAbstractItemView
    )
    from PyQt6.QtGui import QColor
except ImportError:
    from PyQt5.QtWidgets import (
        QGroupBox, QVBoxLayout, QHBoxLayout, QTableWidget,
        QTableWidgetItem, QHeaderView, QPushButton, QLabel,
        QAbstractItemView
    )
    from PyQt5.QtGui import QColor

try:
    from ..config import STACKING
    from ..models import COLOR_HEX
except (ImportError, ValueError):
    from Dobot_UI.config import STACKING
    from Dobot_UI.models import COLOR_HEX


class SequenceWidget(QGroupBox):
    """Table displaying the multi-phase execution plan: Clear Obs -> Stack Goal -> Restore Obs."""

    def __init__(self, parent=None):
        self.max_blocks = int(STACKING.get("max_stack_blocks", 4))
        super().__init__("MISSION EXECUTION PLAN (Clear ➔ Stack Goal ➔ Restore)", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 12, 6, 6)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Phase", "Step", "Movement / Path", "Color", "Target Z"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.lbl_info = QLabel("Tasks: 0")
        self.lbl_info.setStyleSheet("color: #38bdf8; font-weight: bold;")
        layout.addWidget(self.lbl_info)

    def update_table(self, tasks: list[dict]):
        """Populates table with tasks across Phase 1, Phase 2, and Phase 3."""
        self.table.setRowCount(len(tasks))

        clear_cnt = 0
        stack_cnt = 0
        restore_cnt = 0

        for row, t in enumerate(tasks):
            action = t.get("action", "stack_goal")
            phase = t.get("phase", 2 if action == "stack_goal" else (1 if action == "clear_to_feeder" else 3))
            color_name = t.get("color", "none").lower()
            cell_name = t.get("cell_name", t.get("cell_id", "Cell"))
            feeder_name = t.get("feeder_name", f"Feeder {t.get('feeder_id', 1)}")
            drop_z = float(t.get("drop_z", 0.0))

            if action == "clear_to_feeder":
                clear_cnt += 1
                phase_tag = "1: Clear Obs"
                step_tag = f"Obs #{t.get('feeder_id', clear_cnt)}"
                path_str = f"{cell_name}  ➔  {feeder_name}"
                phase_color = QColor("#f97316")  # Orange warning
            elif action == "restore_from_feeder":
                restore_cnt += 1
                phase_tag = "3: Restore"
                step_tag = f"Restore #{t.get('feeder_id', restore_cnt)}"
                path_str = f"{feeder_name}  ➔  {cell_name} (Origin)"
                phase_color = QColor("#2dd4bf")  # Teal success
            else:  # stack_goal
                stack_cnt += 1
                order = t.get("order", stack_cnt)
                phase_tag = "2: Stack Goal"
                step_tag = f"#{order} (Base)" if stack_cnt == 1 else f"#{order}"
                path_str = f"{cell_name}  ➔  Center Goal [1,1]"
                phase_color = QColor("#38bdf8")  # Sky blue

            # Col 0: Phase
            it_phase = QTableWidgetItem(phase_tag)
            it_phase.setForeground(phase_color)
            self.table.setItem(row, 0, it_phase)

            # Col 1: Step
            it_step = QTableWidgetItem(step_tag)
            self.table.setItem(row, 1, it_step)

            # Col 2: Path
            it_path = QTableWidgetItem(path_str)
            self.table.setItem(row, 2, it_path)

            # Col 3: Color
            it_col = QTableWidgetItem(color_name.upper())
            it_col.setForeground(QColor(COLOR_HEX.get(color_name, "#ffffff")))
            self.table.setItem(row, 3, it_col)

            # Col 4: Drop Z
            it_z = QTableWidgetItem(f"Z = {drop_z:.1f} mm")
            it_z.setForeground(QColor("#eab308"))
            self.table.setItem(row, 4, it_z)

        # Update summary label
        summary_parts = []
        if clear_cnt > 0:
            summary_parts.append(f"Phase 1: {clear_cnt} Obstacles Cleared")
        summary_parts.append(f"Phase 2: {stack_cnt} Goal Stacked (Max 4)")
        if restore_cnt > 0:
            summary_parts.append(f"Phase 3: {restore_cnt} Restored to Origin")

        self.lbl_info.setText(" | ".join(summary_parts))
