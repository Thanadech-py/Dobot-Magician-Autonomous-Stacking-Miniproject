import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('dobot_v2')
    default_config_path = os.path.join(pkg_share, 'config', 'usb_cam.yaml')
    default_detection_config_path = os.path.join(pkg_share, 'config', 'detection_node.yaml')

    # Default path to the camera calibration file
    default_calibration_path = os.path.join(pkg_share, 'config', 'C270_Calibration.yaml')
    test_calibration_path = os.path.join(pkg_share, 'config', 'Test_cam_calibration.yaml')

    # Overridable launch arguments
    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_config_path,
        description='Path to ROS 2 yaml parameters file for usb_cam'
    )

    detection_params_file_arg = DeclareLaunchArgument(
        'detection_params_file',
        default_value=default_detection_config_path,
        description='Path to ROS 2 yaml parameters file for detection_node'
    )

    video_device_arg = DeclareLaunchArgument(
        'video_device',
        default_value='/dev/video0',
        description='V4L2 video device path (e.g. /dev/video0 for external USB cam, /dev/video2 for ASUS FHD webcam)'
    )

    # ---- Camera Calibration ----
    camera_info_url_arg = DeclareLaunchArgument(
        'camera_info_url',
        default_value='file://' + test_calibration_path,
        description=(
            'URL to the camera calibration file (camera_info_url). '
            'Use file:// prefix for local files, e.g. '
            'file:///path/to/my_calibration.yaml'
        )
    )

    # Node: usb_cam
    usb_cam_node = Node(
        package='usb_cam',
        executable='usb_cam_node_exe',
        name='usb_cam',
        output='screen',
        respawn=True,
        respawn_delay=2.0,
        parameters=[
            LaunchConfiguration('params_file'),
            {
                'video_device':    LaunchConfiguration('video_device'),
                'camera_info_url': LaunchConfiguration('camera_info_url'),
            }
        ],
    )

    # Optional controller launch
    launch_controller_arg = DeclareLaunchArgument(
        'launch_controller',
        default_value='false',
        description='Optionally launch dobot_controller along with vision'
    )

    # Node: detection_node
    detection_node = Node(
        package='dobot_v2',
        executable='detection_node',
        name='detection_node',
        output='screen',
        respawn=True,
        respawn_delay=1.0,
        parameters=[LaunchConfiguration('detection_params_file')],
    )

    # Node: dobot_controller
    controller_node = Node(
        package='dobot_v2',
        executable='dobot_controller',
        name='dobot_controller',
        output='screen',
        respawn=True,
        respawn_delay=2.0,
        condition=IfCondition(LaunchConfiguration('launch_controller')),
    )

    return LaunchDescription([
        params_file_arg,
        detection_params_file_arg,
        video_device_arg,
        camera_info_url_arg,
        launch_controller_arg,
        usb_cam_node,
        detection_node,
        controller_node,
    ])
