#!/usr/bin/env python3
"""
Launch file for the full Dobot Vision + Control Pipeline.

Uses the usb_cam package (instead of the custom open_cam node) so the
camera is captured with MJPEG encoding.  An image_transport republish
node decodes /image_raw/theora → /image_decoded for downstream nodes.

Nodes started:
  1. usb_cam/usb_cam_node        – captures frames via V4L2/MJPEG
  2. theora_republisher           – decodes /image_raw/theora → /image_decoded
  3. cube_detector_node          – detects colored cubes, publishes coords & poses
  4. dobot_controller_node       – subscribes to detections and controls Dobot arm
  5. dobot_ui_node               – Qt/RViz user-interface node

Usage:
  ros2 launch dobot_project dobot_system.launch.py
  ros2 launch dobot_project dobot_system.launch.py video_device:=/dev/video0 pick_color:=red
  ros2 launch dobot_project dobot_system.launch.py serial_port:=/dev/ttyUSB0
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('dobot_project')

    # Config files
    cam_config      = os.path.join(pkg_share, 'config', 'usb_cam.yaml')
    detector_config = os.path.join(pkg_share, 'config', 'cube_detector.yaml')

    # ---- Overridable launch arguments ----
    args = [
        # Camera
        DeclareLaunchArgument(
            'video_device',
            default_value='/dev/video4',
            description='V4L2 camera device path (e.g. /dev/video0)'),
        DeclareLaunchArgument(
            'image_width',
            default_value='640',
            description='Capture width in pixels'),
        DeclareLaunchArgument(
            'image_height',
            default_value='480',
            description='Capture height in pixels'),
        DeclareLaunchArgument(
            'framerate',
            default_value='15.0',
            description='Camera framerate (fps)'),

        # Detector
        DeclareLaunchArgument(
            'image_topic',
            default_value='image_decoded',
            description='Decoded image topic (republished from theora) fed to cube_detector'),
        DeclareLaunchArgument(
            'show_field_overlay',
            default_value='true',
            description='Draw A4 overlay on annotated image'),

        # Dobot Controller
        DeclareLaunchArgument(
            'serial_port',
            default_value='',
            description='Dobot serial port, e.g. /dev/ttyUSB0 (empty=auto)'),
        DeclareLaunchArgument(
            'velocity',
            default_value='150.0',
            description='Dobot PTP velocity (mm/s)'),
        DeclareLaunchArgument(
            'acceleration',
            default_value='150.0',
            description='Dobot PTP acceleration (mm/s²)'),
        DeclareLaunchArgument(
            'hover_z',
            default_value='80.0',
            description='Z height when hovering above workspace (mm)'),
        DeclareLaunchArgument(
            'pick_z',
            default_value='12.5',
            description='Z height to descend to for picking (mm)'),
        DeclareLaunchArgument(
            'dropoff_x',
            default_value='200.0',
            description='Drop-off X in robot frame (mm)'),
        DeclareLaunchArgument(
            'dropoff_y',
            default_value='0.0',
            description='Drop-off Y in robot frame (mm)'),
        DeclareLaunchArgument(
            'dropoff_z',
            default_value='30.0',
            description='Drop-off Z in robot frame (mm)'),
        DeclareLaunchArgument(
            'pick_color',
            default_value='all',
            description='Color to pick: all | red | green | blue | yellow'),
        DeclareLaunchArgument(
            'use_suction',
            default_value='true',
            description='true=suction cup, false=gripper'),
        DeclareLaunchArgument(
            'home_on_start',
            default_value='true',
            description='Home robot on startup'),
    ]

    # ---- Node: usb_cam (replaces custom open_cam) ----
    # usb_cam publishes /image_raw.  image_transport auto-advertises
    # /image_raw/theora, /image_raw/compressed, etc.
    usb_cam_node = Node(
        package='usb_cam',
        executable='usb_cam_node_exe',
        name='usb_cam_node',
        output='screen',
        parameters=[
            cam_config,
            {
                'video_device': LaunchConfiguration('video_device'),
                'image_width':  LaunchConfiguration('image_width'),
                'image_height': LaunchConfiguration('image_height'),
                'framerate':    LaunchConfiguration('framerate'),
                'pixel_format': 'mjpeg2rgb',
                'io_method':    'mmap',
            },
        ],
        remappings=[
            ('image_raw',   'image_raw'),
            ('camera_info', 'camera_info'),
        ],
    )

    # ---- Node: Theora Republisher ----
    # Subscribes to /image_raw/theora and republishes as /image_decoded
    # (standard sensor_msgs/Image) so downstream nodes avoid the raw stream.
    theora_republisher = Node(
        package='image_transport',
        executable='republish',
        name='theora_republisher',
        output='screen',
        arguments=['theora', 'raw'],
        remappings=[
            ('in/theora', 'image_raw/theora'),
            ('out',       'image_decoded'),
        ],
    )

    # ---- Node: Cube Detector ----
    cube_detector_node = Node(
        package='dobot_project',
        executable='cube_detector',
        name='cube_detector_node',
        output='screen',
        parameters=[
            detector_config,
            {
                'image_topic':        LaunchConfiguration('image_topic'),
                'show_field_overlay': LaunchConfiguration('show_field_overlay'),
            },
        ],
    )

    # ---- Node: Dobot Controller ----
    dobot_controller_node = Node(
        package='dobot_project',
        executable='dobot_controller',
        name='dobot_controller_node',
        output='screen',
        parameters=[
            detector_config,
            {
                'serial_port':   LaunchConfiguration('serial_port'),
                'velocity':      LaunchConfiguration('velocity'),
                'acceleration':  LaunchConfiguration('acceleration'),
                'hover_z':       LaunchConfiguration('hover_z'),
                'pick_z':        LaunchConfiguration('pick_z'),
                'dropoff_x':     LaunchConfiguration('dropoff_x'),
                'dropoff_y':     LaunchConfiguration('dropoff_y'),
                'dropoff_z':     LaunchConfiguration('dropoff_z'),
                'pick_color':    LaunchConfiguration('pick_color'),
                'use_suction':   LaunchConfiguration('use_suction'),
                'home_on_start': LaunchConfiguration('home_on_start'),
            },
        ],
    )

    # ---- Node: Dobot UI ----
    dobot_ui_node = Node(
        package='dobot_project',
        executable='dobot_ui',
        name='dobot_ui_node',
        output='screen',
        parameters=[detector_config],
    )

    return LaunchDescription(args + [
        usb_cam_node,
        theora_republisher,
        cube_detector_node,
        dobot_controller_node,
        dobot_ui_node,
    ])
