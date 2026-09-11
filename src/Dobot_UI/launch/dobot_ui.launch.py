#!/usr/bin/env python3
"""Launch file for Dobot_UI node."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    image_topic_arg = DeclareLaunchArgument(
        'image_topic',
        default_value='detected_objects_image',
        description='Topic for annotated or raw camera image'
    )

    compressed_topic_arg = DeclareLaunchArgument(
        'image_compressed_topic',
        default_value='detected_objects_image/compressed',
        description='Topic for compressed image'
    )

    mock_mode_arg = DeclareLaunchArgument(
        'mock_mode',
        default_value='false',
        description='Enable mock data generator for simulation / standalone testing'
    )

    ui_node = Node(
        package='Dobot_UI',
        executable='dobot_ui',
        name='dobot_ui_node',
        output='screen',
        parameters=[{
            'image_topic': LaunchConfiguration('image_topic'),
            'image_compressed_topic': LaunchConfiguration('image_compressed_topic'),
            'mock_mode': LaunchConfiguration('mock_mode'),
        }]
    )

    return LaunchDescription([
        image_topic_arg,
        compressed_topic_arg,
        mock_mode_arg,
        ui_node
    ])
