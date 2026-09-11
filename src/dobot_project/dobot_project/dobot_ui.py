#!/usr/bin/env python3
"""
ROS 2 + PyQt6 UI for Dobot Magician Vision Control System.

Layout:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  [●] CAM   [●] DOBOT   [Connect]  [Home]  [Calibrate]    Status:●  │  ← Header toolbar
  ├──────────────────────────────┬──────────────────────────────────────┤
  │                              │  FIELD TEMPLATE GRID                 │
  │   Live Camera Feed           │  ┌──────┬──────┬──────┐             │
  │   (annotated stream)         │  │ C1 ▼ │ C2 ▼ │ C3 ▼ │  ← outer   │
  │                              │  ├──────┼──────┼──────┤             │
  │                              │  │ C4 ▼ │ GOAL │ C5 ▼ │  ← outer   │
  │                              │  ├──────┼──────┼──────┤             │
  │                              │  │ C6 ▼ │ C7 ▼ │ C8 ▼ │  ← outer   │
  │                              │  └──────┴──────┴──────┘             │
  │                              │  Feeder slots  [Send Mission]        │
  ├──────────────────────────────┴──────────────────────────────────────┤
  │  LOG  [INFO|WARN|ERR]  timestamp  message ...                       │
  └─────────────────────────────────────────────────────────────────────┘
"""

import sys
import json
import threading
import time
from datetime import datetime

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QComboBox, QGridLayout, QHBoxLayout, QVBoxLayout, QSplitter,
    QTextEdit, QFrame, QSizePolicy, QSpacerItem, QGroupBox,
    QSpinBox, QScrollArea
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QObject
)
from PyQt6.QtGui import (
    QImage, QPixmap, QFont, QColor, QPainter, QPen, QBrush,
    QTextCursor, QPalette
)


# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE  (dark theme)
# ─────────────────────────────────────────────────────────────────────────────
BG_DARK      = "#1a1a2e"
BG_PANEL     = "#16213e"
BG_CARD      = "#0f3460"
BG_WIDGET    = "#1e2a4a"
ACCENT       = "#e94560"
ACCENT2      = "#0f9b8e"
TEXT_PRI     = "#e0e0e0"
TEXT_SEC     = "#a0a0b0"
TEXT_DIM     = "#606070"
BORDER       = "#2a3a5e"
SUCCESS      = "#00d97e"
WARNING      = "#ffc107"
ERROR        = "#e94560"
INFO         = "#3ea6ff"

CUBE_COLORS = {
    "red":    "#e53935",
    "green":  "#43a047",
    "blue":   "#1e88e5",
    "yellow": "#fdd835",
    "none":   "#2a3a5e",
}

CUBE_TEXT_COLORS = {
    "red":    "#ffffff",
    "green":  "#ffffff",
    "blue":   "#ffffff",
    "yellow": "#1a1a1a",
    "none":   TEXT_DIM,
}


DARK_STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRI};
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    font-size: 13px;
}}

QGroupBox {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
    font-size: 12px;
    color: {TEXT_SEC};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px 0 6px;
    color: {ACCENT2};
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 18px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {BG_WIDGET};
    border-color: {ACCENT2};
}}
QPushButton:pressed {{
    background-color: {ACCENT2};
    color: #ffffff;
}}
QPushButton:disabled {{
    color: {TEXT_DIM};
    border-color: {TEXT_DIM};
}}

QPushButton#btn_connect {{
    background-color: {BG_CARD};
    border-color: {ACCENT2};
    color: {ACCENT2};
    font-weight: bold;
}}
QPushButton#btn_connect:hover {{
    background-color: {ACCENT2};
    color: #ffffff;
}}

QPushButton#btn_home {{
    border-color: {WARNING};
    color: {WARNING};
}}
QPushButton#btn_home:hover {{
    background-color: {WARNING};
    color: #000000;
}}

QPushButton#btn_calibrate {{
    border-color: {INFO};
    color: {INFO};
}}
QPushButton#btn_calibrate:hover {{
    background-color: {INFO};
    color: #ffffff;
}}

QPushButton#btn_send {{
    background-color: {ACCENT};
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    border-color: {ACCENT};
    padding: 8px 28px;
}}
QPushButton#btn_send:hover {{
    background-color: #ff6680;
}}
QPushButton#btn_send:disabled {{
    background-color: {TEXT_DIM};
    border-color: {TEXT_DIM};
    color: {BG_DARK};
}}

QComboBox {{
    background-color: {BG_WIDGET};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 3px 8px;
    min-width: 80px;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    color: {TEXT_PRI};
    selection-background-color: {ACCENT2};
    border: 1px solid {BORDER};
}}

QSpinBox {{
    background-color: {BG_WIDGET};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 3px 8px;
}}

QTextEdit {{
    background-color: #0d0d1a;
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 4px;
}}

QScrollBar:vertical {{
    background: {BG_DARK};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QLabel {{
    color: {TEXT_PRI};
}}
QSplitter::handle {{
    background: {BORDER};
}}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {BORDER};
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# ROS2 bridge: runs rclpy in a background thread, emits Qt signals
# ─────────────────────────────────────────────────────────────────────────────

class RosWorker(QObject):
    """Background thread that spins ROS 2 and bridges topics to Qt signals."""

    sig_image      = pyqtSignal(np.ndarray)          # annotated camera frame
    sig_objects    = pyqtSignal(list)                 # list of detected object dicts
    sig_status     = pyqtSignal(str)                  # JSON from dobot_controller
    sig_log        = pyqtSignal(str, str, str)        # (level, source, message)
    sig_ros_ready  = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._running = False
        self._node: Node | None = None
        self._pub_cmd: object = None   # publisher for sending commands

    def start(self):
        self._running = True
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    # ---- internal ----

    def _run(self):
        try:
            if not rclpy.ok():
                rclpy.init()
            self._node = BridgeNode(self)
            self.sig_ros_ready.emit(True)
            while self._running and rclpy.ok():
                rclpy.spin_once(self._node, timeout_sec=0.05)
        except Exception as e:
            self.sig_log.emit("ERROR", "ROS", str(e))
            self.sig_ros_ready.emit(False)
        finally:
            if self._node:
                self._node.destroy_node()

    def publish_command(self, payload: dict):
        """Thread-safe command publish to /dobot_cmd topic."""
        if self._node:
            self._node.publish_cmd(payload)


class BridgeNode(Node):
    """Lightweight ROS 2 node that routes topics to Qt via the worker's signals."""

    def __init__(self, worker: RosWorker):
        super().__init__('dobot_ui_node')
        self._w = worker

        best_effort_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # Subscriptions
        self.create_subscription(Image,  'detected_objects_image',
                                 self._cb_image,   best_effort_qos)
        self.create_subscription(String, 'detected_objects',
                                 self._cb_objects,  10)
        self.create_subscription(String, 'dobot_status',
                                 self._cb_status,   10)

        # Command publisher (UI → controller)
        self._pub_cmd = self.create_publisher(String, 'dobot_ui_cmd', 10)

        self.get_logger().info('Dobot UI ROS node started.')
        worker.sig_log.emit("INFO", "ROS", "UI node connected to topics.")

    def _cb_image(self, msg: Image):
        try:
            frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(
                (msg.height, msg.width, 3))
            if msg.encoding == 'rgb8':
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self._w.sig_image.emit(frame.copy())
        except Exception as e:
            self._w.sig_log.emit("WARN", "Image", str(e))

    def _cb_objects(self, msg: String):
        try:
            data = json.loads(msg.data)
            self._w.sig_objects.emit(data.get('objects', []))
        except Exception as e:
            self._w.sig_log.emit("WARN", "Objects", str(e))

    def _cb_status(self, msg: String):
        try:
            data = json.loads(msg.data)
            state = data.get('state', '')
            message = data.get('message', '')
            level = "ERROR" if state == "error" else "INFO"
            self._w.sig_log.emit(level, "Dobot", f"[{state.upper()}] {message}")
            self._w.sig_status.emit(msg.data)
        except Exception as e:
            self._w.sig_log.emit("WARN", "Status", str(e))

    def publish_cmd(self, payload: dict):
        msg = String()
        msg.data = json.dumps(payload)
        self._pub_cmd.publish(msg)


# ─────────────────────────────────────────────────────────────────────────────
# Field Grid Cell Widget
# ─────────────────────────────────────────────────────────────────────────────

class GridCell(QFrame):
    """
    A single cell in the 3×3 field grid.
    - Outer 8 cells: source/placement cells — user can assign a color + index.
    - Center cell:   GOAL (stacking target) — shows stack info.
    """

    def __init__(self, row: int, col: int, is_goal: bool = False, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.is_goal = is_goal
        self._color = "none"
        self._index = 0
        self._detected = False

        self.setMinimumSize(110, 110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFrameShape(QFrame.Shape.Box)
        self._build_ui()
        self._refresh_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        if self.is_goal:
            # GOAL cell
            self.lbl_title = QLabel("GOAL")
            self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.lbl_title.setStyleSheet(f"color: {ACCENT2}; background: transparent;")

            self.lbl_stack = QLabel("Stack: 0")
            self.lbl_stack.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_stack.setStyleSheet(f"color: {TEXT_SEC}; background: transparent; font-size: 11px;")

            self.lbl_order = QLabel("")
            self.lbl_order.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_order.setStyleSheet(f"color: {TEXT_DIM}; background: transparent; font-size: 10px;")
            self.lbl_order.setWordWrap(True)

            layout.addStretch()
            layout.addWidget(self.lbl_title)
            layout.addWidget(self.lbl_stack)
            layout.addWidget(self.lbl_order)
            layout.addStretch()

        else:
            # Outer source cell
            # Row 1: index spinbox
            top_row = QHBoxLayout()
            top_row.setContentsMargins(0, 0, 0, 0)
            self.lbl_pos = QLabel(f"({self.row},{self.col})")
            self.lbl_pos.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; background: transparent;")
            self.spin_idx = QSpinBox()
            self.spin_idx.setRange(0, 99)
            self.spin_idx.setFixedWidth(48)
            self.spin_idx.setPrefix("# ")
            self.spin_idx.setToolTip("Pick order index (0 = skip)")
            self.spin_idx.setStyleSheet(
                f"background: {BG_DARK}; color: {TEXT_PRI}; border: 1px solid {BORDER}; "
                f"border-radius: 3px; font-size: 11px;"
            )
            top_row.addWidget(self.lbl_pos)
            top_row.addStretch()
            top_row.addWidget(self.spin_idx)

            # Row 2: color selector
            self.combo_color = QComboBox()
            for c in ["none", "red", "green", "blue", "yellow"]:
                self.combo_color.addItem(c.capitalize(), c)
            self.combo_color.setStyleSheet(
                f"background: {BG_DARK}; color: {TEXT_PRI}; border: 1px solid {BORDER}; "
                f"border-radius: 3px; font-size: 11px;"
            )
            self.combo_color.currentIndexChanged.connect(self._on_color_change)

            # Row 3: detection indicator
            self.lbl_detected = QLabel("⬤ Not detected")
            self.lbl_detected.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_detected.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; background: transparent;")

            layout.addLayout(top_row)
            layout.addWidget(self.combo_color)
            layout.addWidget(self.lbl_detected)

    def _on_color_change(self):
        self._color = self.combo_color.currentData()
        self._refresh_style()

    def _refresh_style(self):
        if self.is_goal:
            self.setStyleSheet(
                f"GridCell {{ background-color: {BG_CARD}; border: 2px solid {ACCENT2}; "
                f"border-radius: 8px; }}"
            )
        else:
            c = self._color
            bg = CUBE_COLORS.get(c, CUBE_COLORS["none"])
            if c == "none":
                border = BORDER
                bg_inner = BG_WIDGET
            else:
                border = bg
                bg_inner = bg + "33"  # semi-transparent
            self.setStyleSheet(
                f"GridCell {{ background-color: {bg_inner}; border: 2px solid {border}; "
                f"border-radius: 8px; }}"
            )

    def set_detected(self, detected: bool, color: str = "none"):
        if self.is_goal:
            return
        self._detected = detected
        if detected:
            c = CUBE_COLORS.get(color, CUBE_COLORS["none"])
            self.lbl_detected.setText(f"⬤ Detected")
            self.lbl_detected.setStyleSheet(f"color: {c}; font-size: 10px; background: transparent;")
        else:
            self.lbl_detected.setText("⬤ Not detected")
            self.lbl_detected.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; background: transparent;")

    def update_goal(self, stack_count: int, order_str: str):
        if self.is_goal:
            self.lbl_stack.setText(f"Stack: {stack_count}")
            self.lbl_order.setText(order_str)

    def get_config(self) -> dict | None:
        """Returns cell config if active (index > 0), else None."""
        if self.is_goal:
            return None
        idx = self.spin_idx.value()
        color = self.combo_color.currentData()
        if idx == 0 or color == "none":
            return None
        return {"row": self.row, "col": self.col, "index": idx, "color": color}


# ─────────────────────────────────────────────────────────────────────────────
# Field Grid Widget  (3 × 3)
# ─────────────────────────────────────────────────────────────────────────────

class FieldGrid(QGroupBox):
    """
    3×3 grid mimicking the A4 field template:
    - 8 outer cells → cube source slots
    - 1 center cell → GOAL stacking zone
    """

    sig_mission = pyqtSignal(list)   # emits sorted list of cell configs

    def __init__(self, parent=None):
        super().__init__("Field Template", parent)
        self.cells: list[list[GridCell]] = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)

        # 3×3 Grid
        grid_frame = QWidget()
        grid_frame.setStyleSheet(f"background: {BG_DARK}; border-radius: 8px;")
        grid = QGridLayout(grid_frame)
        grid.setSpacing(6)
        grid.setContentsMargins(8, 8, 8, 8)

        for r in range(3):
            row_cells = []
            for c in range(3):
                is_goal = (r == 1 and c == 1)
                cell = GridCell(r, c, is_goal=is_goal)
                grid.addWidget(cell, r, c)
                row_cells.append(cell)
            self.cells.append(row_cells)

        root.addWidget(grid_frame)

        # Legend row
        legend = QHBoxLayout()
        for color_name, hex_val in CUBE_COLORS.items():
            if color_name == "none":
                continue
            dot = QLabel(f"⬤ {color_name.capitalize()}")
            dot.setStyleSheet(f"color: {hex_val}; font-size: 11px;")
            legend.addWidget(dot)
        legend.addStretch()
        root.addLayout(legend)

        # Bottom controls
        ctrl = QHBoxLayout()

        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.setFixedHeight(32)
        self.btn_clear.clicked.connect(self._clear_all)

        self.btn_send = QPushButton("▶  Send Mission")
        self.btn_send.setObjectName("btn_send")
        self.btn_send.setFixedHeight(36)
        self.btn_send.clicked.connect(self._emit_mission)

        ctrl.addWidget(self.btn_clear)
        ctrl.addStretch()
        ctrl.addWidget(self.btn_send)
        root.addLayout(ctrl)

    def _clear_all(self):
        for row in self.cells:
            for cell in row:
                if not cell.is_goal:
                    cell.spin_idx.setValue(0)
                    cell.combo_color.setCurrentIndex(0)

    def _emit_mission(self):
        configs = []
        for row in self.cells:
            for cell in row:
                cfg = cell.get_config()
                if cfg:
                    configs.append(cfg)
        configs.sort(key=lambda x: x["index"])
        self.sig_mission.emit(configs)

    def update_detections(self, objects: list):
        """Cross-check detected colors against cell assignments."""
        detected_colors = {o["color"] for o in objects}
        for row in self.cells:
            for cell in row:
                if cell.is_goal:
                    continue
                c = cell.combo_color.currentData()
                if c != "none" and c in detected_colors:
                    cell.set_detected(True, c)
                else:
                    cell.set_detected(False)

    def update_goal(self, stack: int, order: str):
        self.cells[1][1].update_goal(stack, order)


# ─────────────────────────────────────────────────────────────────────────────
# Camera viewer
# ─────────────────────────────────────────────────────────────────────────────

class CameraView(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Live Camera Feed", parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 12, 4, 4)

        self.lbl = QLabel()
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setMinimumSize(480, 360)
        self.lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl.setStyleSheet(
            f"background: #000010; border: 1px solid {BORDER}; border-radius: 6px;"
        )
        self._show_placeholder()
        lay.addWidget(self.lbl)

        self.lbl_info = QLabel("No signal")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        lay.addWidget(self.lbl_info)

    def _show_placeholder(self):
        pm = QPixmap(640, 480)
        pm.fill(QColor("#000010"))
        p = QPainter(pm)
        p.setPen(QPen(QColor(BORDER), 2))
        p.setFont(QFont("Segoe UI", 14))
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "No Camera Signal")
        p.end()
        self.lbl.setPixmap(pm)

    def update_frame(self, frame: np.ndarray):
        h, w, ch = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qi = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pm = QPixmap.fromImage(qi)
        # Scale to fit label while keeping aspect ratio
        pm = pm.scaled(self.lbl.size(), Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
        self.lbl.setPixmap(pm)
        self.lbl_info.setText(f"{w}×{h} | {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")


# ─────────────────────────────────────────────────────────────────────────────
# Log widget
# ─────────────────────────────────────────────────────────────────────────────

class LogWidget(QGroupBox):
    MAX_LINES = 500

    def __init__(self, parent=None):
        super().__init__("System Log", parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 12, 6, 6)
        lay.setSpacing(4)

        # Filter buttons
        btn_row = QHBoxLayout()
        self._filters = {"INFO": True, "WARN": True, "ERROR": True}
        self._filter_btns = {}
        for lvl, color in [("INFO", INFO), ("WARN", WARNING), ("ERROR", ERROR)]:
            b = QPushButton(lvl)
            b.setCheckable(True)
            b.setChecked(True)
            b.setFixedHeight(24)
            b.setFixedWidth(60)
            b.setStyleSheet(
                f"QPushButton {{ background: {BG_DARK}; border: 1px solid {color}; "
                f"color: {color}; border-radius: 4px; font-size: 11px; }}"
                f"QPushButton:checked {{ background: {color}; color: #000; }}"
            )
            b.toggled.connect(lambda checked, l=lvl: self._toggle_filter(l, checked))
            btn_row.addWidget(b)
            self._filter_btns[lvl] = b

        btn_row.addStretch()
        btn_clear = QPushButton("Clear")
        btn_clear.setFixedHeight(24)
        btn_clear.setFixedWidth(60)
        btn_clear.clicked.connect(self._clear)
        btn_row.addWidget(btn_clear)
        lay.addLayout(btn_row)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setMinimumHeight(120)
        lay.addWidget(self.text)

        self._all_entries: list[tuple[str, str, str, str]] = []   # (ts, level, source, msg)

    def _toggle_filter(self, level: str, checked: bool):
        self._filters[level] = checked
        self._redraw()

    def _clear(self):
        self._all_entries.clear()
        self.text.clear()

    def _redraw(self):
        self.text.clear()
        for ts, lvl, src, msg in self._all_entries:
            if self._filters.get(lvl, True):
                self._append_html(ts, lvl, src, msg)

    def append(self, level: str, source: str, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._all_entries.append((ts, level, source, message))
        if len(self._all_entries) > self.MAX_LINES:
            self._all_entries.pop(0)
        if self._filters.get(level, True):
            self._append_html(ts, level, source, message)

    def _append_html(self, ts: str, level: str, source: str, message: str):
        colors = {"INFO": INFO, "WARN": WARNING, "ERROR": ERROR}
        c = colors.get(level, TEXT_PRI)
        html = (
            f'<span style="color:{TEXT_DIM};">[{ts}]</span> '
            f'<span style="color:{c}; font-weight:bold;">[{level}]</span> '
            f'<span style="color:{ACCENT2};">[{source}]</span> '
            f'<span style="color:{TEXT_PRI};">{message}</span>'
        )
        self.text.append(html)
        self.text.moveCursor(QTextCursor.MoveOperation.End)


# ─────────────────────────────────────────────────────────────────────────────
# Connection status indicator
# ─────────────────────────────────────────────────────────────────────────────

class StatusDot(QLabel):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._ok = False
        self._refresh()

    def set_status(self, ok: bool):
        self._ok = ok
        self._refresh()

    def _refresh(self):
        c = SUCCESS if self._ok else ERROR
        self.setText(f'<span style="color:{c}; font-size:16px;">⬤</span>'
                     f'<span style="color:{TEXT_SEC}; font-size:12px;"> {self._label}</span>')
        self.setTextFormat(Qt.TextFormat.RichText)


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────

class DobotMainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dobot Magician — Vision Control System")
        self.setMinimumSize(1280, 820)

        self._ros_worker = RosWorker()
        self._mission: list[dict] = []
        self._stack_count = 0
        self._detected_objects: list[dict] = []
        self._ros_connected = False

        self._build_ui()
        self._connect_signals()
        self.setStyleSheet(DARK_STYLESHEET)

        # Start ROS bridge
        self._ros_worker.start()
        self._log("INFO", "System", "UI started. Connecting to ROS 2...")

    # ── Build UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── Header toolbar ──
        root.addWidget(self._make_toolbar())

        # ── Main body ──
        splitter_h = QSplitter(Qt.Orientation.Horizontal)
        splitter_h.setHandleWidth(4)

        # Left: camera
        self.camera_view = CameraView()
        splitter_h.addWidget(self.camera_view)

        # Right: field grid
        right_panel = QWidget()
        right_lay = QVBoxLayout(right_panel)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(6)

        self.field_grid = FieldGrid()
        right_lay.addWidget(self.field_grid)

        # Detected objects summary
        self.detected_group = QGroupBox("Detected Objects")
        det_lay = QHBoxLayout(self.detected_group)
        self._det_labels: dict[str, QLabel] = {}
        for color, hex_c in CUBE_COLORS.items():
            if color == "none":
                continue
            lbl = QLabel(f"⬤ {color.capitalize()}: 0")
            lbl.setStyleSheet(f"color: {hex_c}; font-size: 12px;")
            det_lay.addWidget(lbl)
            self._det_labels[color] = lbl
        det_lay.addStretch()
        right_lay.addWidget(self.detected_group)

        splitter_h.addWidget(right_panel)
        splitter_h.setSizes([680, 560])

        # ── Vertical splitter (main body / log) ──
        splitter_v = QSplitter(Qt.Orientation.Vertical)
        splitter_v.setHandleWidth(4)
        splitter_v.addWidget(splitter_h)

        self.log_widget = LogWidget()
        splitter_v.addWidget(self.log_widget)
        splitter_v.setSizes([620, 200])

        root.addWidget(splitter_v)

    def _make_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            f"background: {BG_PANEL}; border-radius: 8px; border: 1px solid {BORDER};"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 6, 14, 6)
        lay.setSpacing(12)

        # Title
        title = QLabel("DOBOT VISION CONTROL")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ACCENT2}; background: transparent; border: none;")
        lay.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {BORDER};")
        lay.addWidget(sep)

        # Status dots
        self.dot_cam   = StatusDot("CAM")
        self.dot_dobot = StatusDot("DOBOT")
        self.dot_ros   = StatusDot("ROS")
        lay.addWidget(self.dot_cam)
        lay.addWidget(self.dot_dobot)
        lay.addWidget(self.dot_ros)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet(f"color: {BORDER};")
        lay.addWidget(sep2)

        # Buttons
        self.btn_connect = QPushButton("⚡ Connect")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.setFixedHeight(36)

        self.btn_home = QPushButton("⌂  Home")
        self.btn_home.setObjectName("btn_home")
        self.btn_home.setFixedHeight(36)

        self.btn_calibrate = QPushButton("✛  Calibrate")
        self.btn_calibrate.setObjectName("btn_calibrate")
        self.btn_calibrate.setFixedHeight(36)

        lay.addWidget(self.btn_connect)
        lay.addWidget(self.btn_home)
        lay.addWidget(self.btn_calibrate)

        lay.addStretch()

        # Dobot state label
        self.lbl_state = QLabel("Idle")
        self.lbl_state.setStyleSheet(
            f"color: {TEXT_SEC}; font-size: 12px; background: transparent; border: none;"
        )
        lay.addWidget(self.lbl_state)

        return bar

    # ── Connect signals ────────────────────────────────────────────────────

    def _connect_signals(self):
        # ROS worker signals
        self._ros_worker.sig_image.connect(self._on_image)
        self._ros_worker.sig_objects.connect(self._on_objects)
        self._ros_worker.sig_status.connect(self._on_dobot_status)
        self._ros_worker.sig_log.connect(self._log)
        self._ros_worker.sig_ros_ready.connect(self._on_ros_ready)

        # Toolbar buttons
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_home.clicked.connect(self._on_home)
        self.btn_calibrate.clicked.connect(self._on_calibrate)

        # Field grid mission
        self.field_grid.sig_mission.connect(self._on_mission)

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_ros_ready(self, ok: bool):
        self.dot_ros.set_status(ok)
        self._ros_connected = ok
        level = "INFO" if ok else "ERROR"
        self._log(level, "ROS", "ROS 2 bridge ready." if ok else "ROS 2 bridge failed.")

    def _on_image(self, frame: np.ndarray):
        self.dot_cam.set_status(True)
        self.camera_view.update_frame(frame)

    def _on_objects(self, objects: list):
        self._detected_objects = objects
        # Update count labels
        counts = {"red": 0, "green": 0, "blue": 0, "yellow": 0}
        for o in objects:
            c = o.get("color", "")
            if c in counts:
                counts[c] += 1
        for color, lbl in self._det_labels.items():
            n = counts.get(color, 0)
            hex_c = CUBE_COLORS[color]
            lbl.setText(f"⬤ {color.capitalize()}: {n}")
            lbl.setStyleSheet(
                f"color: {'#ffffff' if n == 0 else hex_c}; font-size: 12px;"
            )
        # Update grid detection indicators
        self.field_grid.update_detections(objects)

    def _on_dobot_status(self, json_str: str):
        try:
            data = json.loads(json_str)
            state = data.get("state", "")
            msg   = data.get("message", "")
            self.lbl_state.setText(f"{state.capitalize()}: {msg[:40]}")
            self.dot_dobot.set_status(state not in ("error", "disconnected"))
            if state == "idle":
                self._stack_count += 1
                order_str = "  →  ".join(
                    f"#{c['index']} {c['color']}" for c in self._mission
                )
                self.field_grid.update_goal(self._stack_count, order_str)
        except Exception:
            pass

    def _on_connect(self):
        self._log("INFO", "UI", "Sending CONNECT command...")
        self._ros_worker.publish_command({"cmd": "connect"})
        self.dot_dobot.set_status(False)
        self.lbl_state.setText("Connecting...")

    def _on_home(self):
        self._log("INFO", "UI", "Sending HOME command to Dobot...")
        self._ros_worker.publish_command({"cmd": "home"})
        self.lbl_state.setText("Homing...")

    def _on_calibrate(self):
        self._log("INFO", "UI", "Sending CALIBRATE command...")
        self._ros_worker.publish_command({"cmd": "calibrate"})
        self.lbl_state.setText("Calibrating...")

    def _on_mission(self, configs: list):
        if not configs:
            self._log("WARN", "Mission", "No cells configured — add colors and indices first.")
            return
        self._mission = configs
        self._stack_count = 0
        summary = ", ".join(f"#{c['index']} {c['color']} ({c['row']},{c['col']})" for c in configs)
        self._log("INFO", "Mission", f"Sending mission: {summary}")
        self._ros_worker.publish_command({"cmd": "mission", "tasks": configs})
        self.lbl_state.setText(f"Mission: {len(configs)} tasks")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _log(self, level: str, source: str, message: str):
        self.log_widget.append(level, source, message)

    def closeEvent(self, event):
        self._ros_worker.stop()
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass
        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main(args=None):
    # Qt must be created before rclpy.init() in some configurations
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Apply dark palette as base so native widgets inherit it
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(BG_DARK))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT_PRI))
    palette.setColor(QPalette.ColorRole.Base,            QColor(BG_PANEL))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(BG_CARD))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(BG_WIDGET))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(TEXT_PRI))
    palette.setColor(QPalette.ColorRole.Text,            QColor(TEXT_PRI))
    palette.setColor(QPalette.ColorRole.Button,          QColor(BG_CARD))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT_PRI))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(ACCENT2))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    win = DobotMainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
