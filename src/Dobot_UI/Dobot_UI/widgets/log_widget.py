"""Event log viewer widget."""

from datetime import datetime

try:
    from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton
except ImportError:
    from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton


class LogWidget(QGroupBox):
    """Console log viewer."""

    def __init__(self, parent=None):
        super().__init__("SYSTEM EVENT LOG", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 12, 6, 6)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumHeight(90)
        layout.addWidget(self.text)

        btn_clear = QPushButton("Clear Log")
        btn_clear.setFixedHeight(22)
        btn_clear.clicked.connect(self.text.clear)
        layout.addWidget(btn_clear)

    def append_log(self, level: str, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        color = "#22c55e" if level == "INFO" else ("#ef4444" if level == "ERROR" else "#f59e0b")
        html = f"<span style='color:#64748b;'>[{ts}]</span> <b style='color:{color};'>[{level}]</b> {msg}<br>"
        self.text.insertHtml(html)
        self.text.ensureCursorVisible()
