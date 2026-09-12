"""Configuration loader for Dobot_UI.

Loads dobot_ui.yaml from config directory and provides safe fallbacks.
"""

import copy
import logging
import os
import yaml

logger = logging.getLogger("Dobot_UI.config")

# Built-in robust defaults (used if YAML is missing, damaged, or partially populated)
DEFAULT_CONFIG = {
    "topics": {
        "image_raw":   "detected_objects_image",
        "image_comp":  "detected_objects_image/compressed",
        "detections":  "detected_objects",
        "status":      "dobot_status",
        "command":     "dobot_ui_cmd",
        "reset_grid":  "reset_grid",
    },
    "window": {
        "title":  "Dobot Magician - Stacking Mission UI",
        "width":  1100,
        "height": 750,
    },
    "grid": {
        "cell_pitch_mm":    35.0,
        "origin_offset_x":  22.0,
        "origin_offset_y":  22.0,
        "grid_tl_x_mm":    48.0,
        "grid_tl_y_mm":    37.0,
        "robot_base_x_mm": 105.0,
        "robot_base_y_mm": 270.0,
        "pick_z_mm":        12.5,
    },
    "stacking": {
        "base_drop_z_mm": 30.0,
        "cube_height_mm": 25.0,
    },
    "cell_defaults": {
        "orders": [1, 2, 3, 4, 5, 6, 7, 8],
        "colors": ["red", "yellow", "green", "blue", "orange", "purple", "cyan", "red"],
    },
    "detection_node": {
        "ros2_package":      "dobot_v2",
        "ros2_node":         "detection_node",
        "installed_exe":     "/home/thxncdzch/dobot_ws/install/dobot_v2/lib/dobot_v2/detection_node",
        "src_script":        "/home/thxncdzch/dobot_ws/src/dobot_v2/dobot_v2/detection_node.py",
        "restart_delay_sec": 0.5,
    },
    "color_hex": {
        "red":    "#ef4444",
        "yellow": "#eab308",
        "green":  "#22c55e",
        "blue":   "#3b82f6",
        "orange": "#f97316",
        "purple": "#a855f7",
        "cyan":   "#06b6d4",
        "none":   "#64748b",
    },
    "manual_control": {
        "default_step_mm":      10.0,
        "default_rot_step_deg": 5.0,
        "hover_z_mm":           80.0,
        "dropoff_z_mm":         30.0,
    },
}


def _deep_merge(base: dict, update: dict) -> dict:
    """Recursively merges update dict into base dict."""
    for k, v in update.items():
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def find_config_path() -> str | None:
    """Searches for dobot_ui.yaml across standard ROS 2 and package locations."""
    # 1. Environment variable override
    env_cfg = os.environ.get("DOBOT_UI_CONFIG")
    if env_cfg and os.path.isfile(env_cfg):
        return env_cfg

    # 2. ROS 2 ament package share directory (installed package standard)
    try:
        from ament_index_python.packages import get_package_share_directory
        share_dir = get_package_share_directory("Dobot_UI")
        share_yaml = os.path.join(share_dir, "config", "dobot_ui.yaml")
        if os.path.isfile(share_yaml):
            return share_yaml
    except Exception:
        pass

    # 3. Relative to current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        # From src/Dobot_UI/Dobot_UI -> src/Dobot_UI/config/dobot_ui.yaml
        os.path.normpath(os.path.join(current_dir, "..", "config", "dobot_ui.yaml")),
        # From install/Dobot_UI/lib/python3.X/site-packages/Dobot_UI -> install/Dobot_UI/share/Dobot_UI/config/dobot_ui.yaml
        os.path.normpath(os.path.join(current_dir, "..", "..", "..", "..", "share", "Dobot_UI", "config", "dobot_ui.yaml")),
        # Direct workspace paths
        "/home/thxncdzch/dobot_ws/src/Dobot_UI/config/dobot_ui.yaml",
        "/home/thxncdzch/dobot_ws/install/Dobot_UI/share/Dobot_UI/config/dobot_ui.yaml",
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    return None


def load_config() -> dict:
    """Loads config from YAML file, merged with defaults."""
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    path = find_config_path()
    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    _deep_merge(cfg, loaded)
        except Exception as e:
            logger.warning("Failed to parse config at %s: %s", path, e)
    return cfg


# Module-level singletons for immediate convenience access
_CONFIG = load_config()

TOPICS        = _CONFIG["topics"]
WINDOW        = _CONFIG["window"]
GRID          = _CONFIG["grid"]
STACKING      = _CONFIG["stacking"]
CELL_DEFAULTS = _CONFIG["cell_defaults"]
DETECTION     = _CONFIG["detection_node"]
COLOR_HEX     = _CONFIG["color_hex"]
MANUAL_CONTROL = _CONFIG["manual_control"]
