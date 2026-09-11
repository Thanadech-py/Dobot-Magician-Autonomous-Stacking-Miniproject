"""Stacking sequence table showing 1st..8th execution order."""

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

from ..models import COLOR_HEX


class SequenceWidget(QGroupBox):
    """Table showing the 1st to 8th object stacking plan."""

    def __init__(self, parent=None):
        super().__init__("STACKING SEQUENCE (1st to 8th)", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 12, 6, 6)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Stack #", "Grid Cell", "Color", "Drop Z"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.lbl_info = QLabel("Tasks: 0")
        self.lbl_info.setStyleSheet("color: #38bdf8; font-weight: bold;")
        layout.addWidget(self.lbl_info)

    def update_table(self, tasks: list[dict]):
        self.table.setRowCount(len(tasks))
        for row, t in enumerate(tasks):
            # Order tag
            tag = f"#{t['order']} (Base)" if row == 0 else (f"#{t['order']} (Top)" if row == len(tasks) - 1 else f"#{t['order']}")
            self.table.setItem(row, 0, QTableWidgetItem(tag))

            # Cell
            self.table.setItem(row, 1, QTableWidgetItem(f"[{t['row']},{t['col']}] {t['name']}"))

            # Color
            item_col = QTableWidgetItem(t['color'].upper())
            item_col.setForeground(QColor(COLOR_HEX.get(t['color'], "#ffffff")))
            self.table.setItem(row, 2, item_col)

            # Drop Z
            item_z = QTableWidgetItem(f"Z = {t['drop_z']:.1f} mm")
            item_z.setForeground(QColor("#eab308"))
            self.table.setItem(row, 3, item_z)

        self.lbl_info.setText(f"Active Tasks: {len(tasks)} / 8 | Final Stack Z: {tasks[-1]['drop_z'] if tasks else 0:.1f} mm")
