"""
Unified System Launch File: Dobot Magician Autonomous Stacking System
======================================================================
Launches all subsystems simultaneously:
  1. usb_cam:           Camera driver node
  2. detection_node:    Real-time pallet grid and multi-color cube detector
  3. dobot_controller:  Dobot Magician hardware arm controller
  4. dobot_ui:          PyQt GUI dashboard with live camera feed and manual control

Usage:
  ros2 launch dobot_v2 dobot_system.launch.py
  ros2 launch dobot_v2 dobot_system.launch.py launch_cam:=false
  ros2 launch dobot_v2 dobot_system.launch.py video_device:=/dev/video0
"""

import os
from ament_index_python.packages import get_package_share_directory, PackageNotFoundError
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Package directories
    try:
        pkg_dobot_v2 = get_package_share_directory("dobot_v2")
    except PackageNotFoundError:
        pkg_dobot_v2 = os.path.expanduser("~/dobot_ws/src/dobot_v2")

    # Configuration files
    default_usb_cam_yaml = os.path.join(pkg_dobot_v2, "config", "usb_cam.yaml")
    default_detection_yaml = os.path.join(pkg_dobot_v2, "config", "detection_node.yaml")
    default_controller_yaml = os.path.join(pkg_dobot_v2, "config", "dobot_controller.yaml")
    default_calibration_yaml = os.path.join(pkg_dobot_v2, "config", "Test_cam_calibration.yaml")

    # ── Launch Arguments ──────────────────────────────────────────
    arg_launch_cam = DeclareLaunchArgument(
        "launch_cam",
        default_value="true",
        description="Whether to launch the usb_cam camera driver node"
    )
    arg_launch_vision = DeclareLaunchArgument(
        "launch_vision",
        default_value="true",
        description="Whether to launch the detection_node vision tracker"
    )
    arg_launch_controller = DeclareLaunchArgument(
        "launch_controller",
        default_value="true",
        description="Whether to launch the dobot_controller arm node"
    )
    arg_launch_ui = DeclareLaunchArgument(
        "launch_ui",
        default_value="true",
        description="Whether to launch the Dobot_UI dashboard"
    )

    arg_video_device = DeclareLaunchArgument(
        "video_device",
        default_value="/dev/video0",
        description="V4L2 camera device path"
    )
    arg_camera_info_url = DeclareLaunchArgument(
        "camera_info_url",
        default_value="file://" + default_calibration_yaml,
        description="Camera calibration YAML URL"
    )

    arg_cam_params = DeclareLaunchArgument(
        "cam_params_file",
        default_value=default_usb_cam_yaml,
        description="Path to usb_cam parameters YAML"
    )
    arg_detection_params = DeclareLaunchArgument(
        "detection_params_file",
        default_value=default_detection_yaml,
        description="Path to detection_node parameters YAML"
    )
    arg_controller_params = DeclareLaunchArgument(
        "controller_params_file",
        default_value=default_controller_yaml,
        description="Path to dobot_controller parameters YAML"
    )

    # ── Nodes ─────────────────────────────────────────────────────

    # 1. Camera Driver
    usb_cam_node = Node(
        package="usb_cam",
        executable="usb_cam_node_exe",
        name="usb_cam",
        output="screen",
        respawn=True,
        respawn_delay=2.0,
        condition=IfCondition(LaunchConfiguration("launch_cam")),
        parameters=[
            LaunchConfiguration("cam_params_file"),
            {
                "video_device": LaunchConfiguration("video_device"),
                "camera_info_url": LaunchConfiguration("camera_info_url"),
            }
        ],
    )

    # 2. Vision Detection Node
    detection_node = Node(
        package="dobot_v2",
        executable="detection_node",
        name="detection_node",
        output="screen",
        respawn=False,
        condition=IfCondition(LaunchConfiguration("launch_vision")),
        parameters=[LaunchConfiguration("detection_params_file")],
    )

    # 3. Dobot Hardware Controller Node
    controller_node = Node(
        package="dobot_v2",
        executable="dobot_controller",
        name="dobot_controller",
        output="screen",
        respawn=True,
        respawn_delay=2.0,
        condition=IfCondition(LaunchConfiguration("launch_controller")),
        parameters=[LaunchConfiguration("controller_params_file")],
    )

    # 4. PyQt Mission UI Dashboard
    ui_node = Node(
        package="Dobot_UI",
        executable="dobot_ui",
        name="dobot_ui",
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_ui")),
    )

    return LaunchDescription([
        arg_launch_cam,
        arg_launch_vision,
        arg_launch_controller,
        arg_launch_ui,
        arg_video_device,
        arg_camera_info_url,
        arg_cam_params,
        arg_detection_params,
        arg_controller_params,
        usb_cam_node,
        detection_node,
        controller_node,
        ui_node,
    ])
