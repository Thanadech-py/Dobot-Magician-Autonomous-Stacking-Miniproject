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
QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 3px 6px;
    color: #e2e8f0;
}
QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #38bdf8;
}
QRadioButton {
    color: #cbd5e1;
    spacing: 5px;
}
QRadioButton::indicator {
    width: 13px;
    height: 13px;
}
QTabWidget::pane {
    border: 1px solid #2d3748;
    background-color: #121824;
    border-radius: 6px;
    top: -1px;
}
QTabBar::tab {
    background-color: #1e293b;
    color: #94a3b8;
    padding: 6px 14px;
    min-width: 140px;
    border: 1px solid #334155;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background-color: #121824;
    color: #38bdf8;
    border-color: #2d3748;
    border-bottom: 2px solid #38bdf8;
}
QTabBar::tab:hover:!selected {
    background-color: #26354a;
    color: #e2e8f0;
}
QScrollArea {
    border: none;
    background-color: transparent;
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
