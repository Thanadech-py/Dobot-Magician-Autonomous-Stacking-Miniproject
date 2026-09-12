#!/usr/bin/env python3
"""Entry point for Dobot_UI node."""

import os
import signal
import sys

# Support direct script execution (python3 app.py) as well as package imports
if __package__ is None or __package__ == "":
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.dirname(pkg_dir)
    if workspace_dir not in sys.path:
        sys.path.insert(0, workspace_dir)
    from Dobot_UI.config import WINDOW
    from Dobot_UI.main_window import DobotMainWindow
    from Dobot_UI.ros_bridge import RosBridge
else:
    from .config import WINDOW
    from .main_window import DobotMainWindow
    from .ros_bridge import RosBridge

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        print("Please install PyQt6: pip install PyQt6")
        sys.exit(1)

try:
    import rclpy
    import rclpy.utilities
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


def main(args=None):
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    cli_args = sys.argv if args is None else list(args)
    mock = (
        "--mock" in cli_args
        or "-m" in cli_args
        or "--simulate" in cli_args
        or os.environ.get("DOBOT_UI_MOCK", "0") in ("1", "true", "True")
        or not HAS_ROS2
    )

    clean_args = list(cli_args)
    if HAS_ROS2:
        try:
            if not rclpy.ok():
                rclpy.init(args=cli_args)
            try:
                clean_args = rclpy.utilities.remove_ros_args(args=cli_args)
            except Exception:
                pass
        except Exception as e:
            print(f"[Dobot_UI] ROS 2 init warning: {e}")

    app = QApplication(clean_args)
    app.setApplicationName(WINDOW.get("title", "Dobot Magician UI"))

    bridge = RosBridge(mock_mode=mock)
    window = DobotMainWindow(bridge)
    window.show()

    bridge.start()
    ret = app.exec()
    bridge.stop()

    if HAS_ROS2:
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass

    sys.exit(ret)


if __name__ == "__main__":
    main()
