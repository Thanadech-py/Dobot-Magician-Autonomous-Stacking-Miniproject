"""Alias package for dobot_ui (lowercase)."""

from Dobot_UI.app import main
from Dobot_UI.models import OUTER_CELLS, COLORS, COLOR_HEX, calc_robot_coords

__all__ = ["main", "OUTER_CELLS", "COLORS", "COLOR_HEX", "calc_robot_coords"]
