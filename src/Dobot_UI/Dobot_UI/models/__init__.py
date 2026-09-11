"""Data models and coordinate helpers for the 3x3 grid stacking mission."""

try:
    from ..config import GRID, COLOR_HEX  # noqa: F401
except (ImportError, ValueError):
    from Dobot_UI.config import GRID, COLOR_HEX  # noqa: F401

# 8 Outer cells surrounding the center goal (1, 1)
OUTER_CELLS = [
    {"id": 0, "row": 0, "col": 0, "name": "Top-Left",     "short": "TL"},
    {"id": 1, "row": 0, "col": 1, "name": "Top",          "short": "T"},
    {"id": 2, "row": 0, "col": 2, "name": "Top-Right",    "short": "TR"},
    {"id": 3, "row": 1, "col": 0, "name": "Left",         "short": "L"},
    {"id": 4, "row": 1, "col": 2, "name": "Right",        "short": "R"},
    {"id": 5, "row": 2, "col": 0, "name": "Bottom-Left",  "short": "BL"},
    {"id": 6, "row": 2, "col": 1, "name": "Bottom",       "short": "B"},
    {"id": 7, "row": 2, "col": 2, "name": "Bottom-Right", "short": "BR"},
]

COLORS = ["red", "yellow", "green", "blue", "orange", "purple", "cyan", "none"]


def calc_robot_coords(row: int, col: int) -> tuple[float, float, float]:
    """Converts 3x3 grid (row, col) to Dobot base frame (rx, ry, rz in mm)."""
    pitch     = float(GRID.get("cell_pitch_mm",   35.0))
    origin_x  = float(GRID.get("origin_offset_x", 22.0))
    origin_y  = float(GRID.get("origin_offset_y", 22.0))
    grid_tl_x = float(GRID.get("grid_tl_x_mm",   48.0))
    grid_tl_y = float(GRID.get("grid_tl_y_mm",   37.0))
    base_x    = float(GRID.get("robot_base_x_mm", 105.0))
    base_y    = float(GRID.get("robot_base_y_mm", 270.0))
    pick_z    = float(GRID.get("pick_z_mm",       12.5))

    gx = origin_x + col * pitch
    gy = origin_y + row * pitch
    field_x = grid_tl_x + gx
    field_y = grid_tl_y + gy
    rx = base_y - field_y
    ry = base_x - field_x
    return round(rx, 1), round(ry, 1), pick_z
