#!/usr/bin/env python3
"""
Launch file for the full Dobot Vision + Control Pipeline.

Nodes started:
  1. usb_cam_node        – captures and publishes raw frames from USB camera
  2. cube_detector_node  – detects colored cubes, publishes coordinates & poses
  3. dobot_controller_node – subscribes to detections and controls Dobot arm

Usage:
  ros2 launch dobot_project dobot_vision.launch.py
  ros2 launch dobot_project dobot_vision.launch.py device_id:=0 pick_color:=red
  ros2 launch dobot_project dobot_vision.launch.py serial_port:=/dev/ttyUSB0
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('dobot_project')
    default_config = os.path.join(pkg_share, 'config', 'cube_detector.yaml')

    # ---- Overridable launch arguments ----
    args = [
        DeclareLaunchArgument('device_id',        default_value='4',
                              description='V4L2 camera device index'),
        DeclareLaunchArgument('image_topic',       default_value='image_raw',
                              description='Raw camera image topic'),
        DeclareLaunchArgument('show_field_overlay',default_value='true',
                              description='Draw A4 overlay on annotated image'),
        DeclareLaunchArgument('serial_port',       default_value='',
                              description='Dobot serial port, e.g. /dev/ttyUSB0 (empty=auto)'),
        DeclareLaunchArgument('velocity',          default_value='150.0',
                              description='Dobot PTP velocity (mm/s)'),
        DeclareLaunchArgument('acceleration',      default_value='150.0',
                              description='Dobot PTP acceleration (mm/s²)'),
        DeclareLaunchArgument('hover_z',           default_value='80.0',
                              description='Z height when hovering above workspace (mm)'),
        DeclareLaunchArgument('pick_z',            default_value='12.5',
                              description='Z height to descend to for picking (mm)'),
        DeclareLaunchArgument('dropoff_x',         default_value='200.0',
                              description='Drop-off X in robot frame (mm)'),
        DeclareLaunchArgument('dropoff_y',         default_value='0.0',
                              description='Drop-off Y in robot frame (mm)'),
        DeclareLaunchArgument('dropoff_z',         default_value='30.0',
                              description='Drop-off Z in robot frame (mm)'),
        DeclareLaunchArgument('pick_color',        default_value='all',
                              description='Color to pick: all|red|green|blue|yellow'),
        DeclareLaunchArgument('use_suction',       default_value='true',
                              description='true=suction cup, false=gripper'),
        DeclareLaunchArgument('home_on_start',     default_value='true',
                              description='Home robot on startup'),
    ]

    # ---- Node: USB Camera ----
    usb_cam_node = Node(
        package='dobot_project',
        executable='open_cam',
        name='usb_cam_node',
        output='screen',
        parameters=[
            default_config,
            {'device_id': LaunchConfiguration('device_id')},
        ]
    )

    # ---- Node: Cube Detector ----
    cube_detector_node = Node(
        package='dobot_project',
        executable='cube_detector',
        name='cube_detector_node',
        output='screen',
        parameters=[
            default_config,
            {
                'image_topic':       LaunchConfiguration('image_topic'),
                'show_field_overlay':LaunchConfiguration('show_field_overlay'),
            }
        ]
    )

    # ---- Node: Dobot Controller ----
    dobot_controller_node = Node(
        package='dobot_project',
        executable='dobot_controller',
        name='dobot_controller_node',
        output='screen',
        parameters=[
            default_config,
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
            }
        ]
    )

    return LaunchDescription(args + [
        usb_cam_node,
        cube_detector_node,
        dobot_controller_node,
    ])
