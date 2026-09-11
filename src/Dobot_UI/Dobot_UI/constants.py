"""Dark theme QSS stylesheet (visual constants only — all config lives in dobot_ui.yaml)."""

STYLESHEET = """
QWidget {
    background-color: #121824;
    color: #e2e8f0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #2d3748;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: #38bdf8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 5px 12px;
    font-weight: 500;
}
QPushButton:hover { background-color: #334155; border-color: #38bdf8; }
QPushButton:pressed { background-color: #0284c7; color: #ffffff; }
QComboBox, QSpinBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 3px 6px;
}
QTableWidget {
    background-color: #161f2e;
    border: 1px solid #2d3748;
    gridline-color: #2d3748;
}
QHeaderView::section {
    background-color: #1e293b;
    border: 1px solid #2d3748;
    padding: 4px;
    font-weight: bold;
}
"""
