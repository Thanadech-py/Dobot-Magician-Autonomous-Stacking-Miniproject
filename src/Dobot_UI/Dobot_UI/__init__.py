"""
Dobot_UI: ROS 2 PyQt6 User Interface for Dobot Magician Mission Control.
Provides video visualization from detection_node in dobot_v2,
Dobot robot status telemetry, and interactive 8-cube stacking sequence mission planner.
"""

import sys

__version__ = "1.0.0"
__author__ = "thxncdzch"

# Alias lowercase module name for convenient imports
if "dobot_ui" not in sys.modules:
    sys.modules["dobot_ui"] = sys.modules[__name__]
