# dobot_v2: Vision Tracking & Robotic Arm Controller for Dobot Magician

A high-performance, modular ROS 2 package providing real-time computer vision tracking and robotic arm control for the **Dobot Magician**.

`dobot_v2` tracks a physical **3x3 pallet grid** on an A4 reference workspace, establishes a metric local coordinate frame using perspective homography, detects multi-colored cubes in real time, executes multi-step pick-and-place stacking missions, and provides full manual jogging and tool control compatible with [`Dobot_UI`](file:///home/thxncdzch/dobot_ws/src/Dobot_UI).

---

## Table of Contents

- [System Overview](#system-overview)
- [Package Architecture](#package-architecture)
- [Nodes & Subsystems](#nodes--subsystems)
  - [1. Detection Node (`detection_node`)](#1-detection-node-detection_node)
  - [2. Dobot Controller Node (`dobot_controller`)](#2-dobot-controller-node-dobot_controller)
  - [3. Hardware Driver (`dobot_driver.py`)](#3-hardware-driver-dobot_driverpy)
  - [4. Mission Sequencer (`mission_executor.py`)](#4-mission-sequencer-mission_executorpy)
- [Configuration System (`config/`)](#configuration-system-config)
  - [`dobot_controller.yaml`](#dobot_controlleryaml)
  - [`detection_node.yaml`](#detection_nodeyaml)
- [ROS 2 Interface & Topics](#ros-2-interface--topics)
  - [Published Topics](#published-topics)
  - [Subscribed Topics](#subscribed-topics)
  - [UI Command Protocol Specification](#ui-command-protocol-specification)
  - [Robot Status Telemetry Specification](#robot-status-telemetry-specification)
- [Launch Files & Running](#launch-files--running)
  - [1. Launch All (Unified System)](#1-launch-all-unified-system)
  - [2. Launch Vision & Controller Only](#2-launch-vision--controller-only)
- [Interactive Grid Calibration Tool](#interactive-grid-calibration-tool)
- [Troubleshooting & FAQ](#troubleshooting--faq)

---

## System Overview

The system operates on an **A4 reference field** ($210\text{ mm} \times 297\text{ mm}$) with a Dobot Magician robot mounted at base origin $(X=105.0\text{ mm}, Y=270.0\text{ mm})$:
- **3x3 Pallet Grid** ($114.5\text{ mm} \times 114.5\text{ mm}$ outer boundary, $35\text{ mm}$ pitch).
- **8 Outer Cube Cells**: Host colored cubes (Red, Yellow, Green, Blue, Orange, Purple, Cyan).
- **Center Goal Cell (1, 1)**: Destination where cubes are stacked vertically from 1st (bottom) to 8th (top).

```
       [4 Feeder Slots]       [3x3 Pallet Grid: 114.5 x 114.5 mm]
         (Green Rims)
           ( #1 )             +-----------+-----------+-----------+
                              |   (0,0)   |   (0,1)   |   (0,2)   |
           ( #2 )             +-----------+-----------+-----------+
                              |   (1,0)   |   (1,1)   |   (1,2)   |
           ( #3 )             |           |   GOAL    |           |
                              +-----------+-----------+-----------+
           ( #4 )             |   (2,0)   |   (2,1)   |   (2,2)   |
                              +-----------+-----------+-----------+

                                  [Dobot Magician Robot Base]
                                         (105, 270) mm
```

---

## Package Architecture

Every component is cleanly isolated into dedicated Python modules following the Single Responsibility Principle:

```
src/dobot_v2/
├── config/
│   ├── dobot_controller.yaml     # Robot speeds, safety limits, geometry heights, effector dwell
│   ├── detection_node.yaml       # Vision geometry, homography corners, HSV color bounds
│   ├── usb_cam.yaml              # V4L2 camera driver parameters
│   ├── C270_Calibration.yaml    # Logitech C270 camera matrix profile
│   └── Test_cam_calibration.yaml# Generic camera calibration profile
├── dobot_v2/
│   ├── __init__.py               # Package exports
│   ├── dobot_controller_node.py  # ROS 2 node interfacing UI commands and Dobot hardware
│   ├── dobot_driver.py           # Thread-safe pydobot/pydobot2 hardware driver & mock fallback
│   ├── mission_executor.py       # Trajectory generator & multi-cube stacking sequencer
│   ├── detection_node.py         # ROS 2 vision node orchestrator
│   ├── transforms.py             # Perspective homography & metric coordinate conversions
│   ├── grid_detector.py          # Pallet contouring, green rim subtraction & corner locking
│   ├── cube_detector.py          # Color segmentation & geometric cube contour filtering
│   ├── visualizer.py             # Debug visual overlays & HUD drawing
│   └── calibrate_grid.py         # Standalone 4-corner interactive calibration tool
├── launch/
│   ├── dobot_system.launch.py    # Unified system launcher (Cam + Vision + Controller + UI)
│   └── dobot_vision.launch.py    # Dedicated vision & camera launcher
├── package.xml                   # ROS 2 package manifest
├── setup.cfg
└── setup.py                      # Ament Python entry points
```

---

## Nodes & Subsystems

### 1. Detection Node (`detection_node`)
- Subscribes to camera frames via `sensor_msgs/msg/Image`.
- Detects the outer pallet corners, isolates the green feeder rings, and computes perspective homography.
- Segment colors (Red, Yellow, Green, Blue) and maps cube centroids to Dobot base coordinates in millimeters.
- Publishes `/detected_objects` JSON and compressed debug video stream.

### 2. Dobot Controller Node (`dobot_controller`)
- Subscribes to `/dobot_ui_cmd` and `/detected_objects`.
- Coordinates hardware movement, homing, tool actuation, and emergency stop.
- Publishes high-frequency status telemetry to `/dobot_status`.
- Loads all configurations from [`config/dobot_controller.yaml`](file:///home/thxncdzch/dobot_ws/src/dobot_v2/config/dobot_controller.yaml).

### 3. Hardware Driver (`dobot_driver.py`)
- Thread-safe encapsulation of `pydobot` / `pydobot2`.
- Clamps coordinates to configured software workspace limits ($X: 100\dots 330\,\text{mm}, Y: -250\dots 250\,\text{mm}, Z: -60\dots 160\,\text{mm}$).
- Features a graceful simulation mode if running without physical hardware or without `pydobot2`.

### 4. Mission Sequencer (`mission_executor.py`)
- Executes automated stacking trajectories:
  1. Hover above cube: $(X_{pick}, Y_{pick}, Z_{hover})$
  2. Suction ON
  3. Descend vertically: $(X_{pick}, Y_{pick}, Z_{pick})$
  4. Grip dwell pause
  5. Lift vertically to $Z_{hover}$
  6. Carry to drop-off $(X_{drop}, Y_{drop}, Z_{hover})$
  7. Lower to stack level: $(X_{drop}, Y_{drop}, Z_{drop} + \text{layer} \times \text{cube\_height})$
  8. Suction OFF
  9. Release dwell pause
  10. Lift vertically clear of stack to $Z_{hover}$

---

## Configuration System (`config/`)

### `dobot_controller.yaml`
```yaml
dobot_controller:
  ros__parameters:
    serial_port: ""              # Port (e.g. '/dev/ttyUSB0'). Empty = auto-detect
    velocity: 150.0              # PTP velocity (mm/s)
    acceleration: 150.0          # PTP acceleration (mm/s²)
    limits:
      min_x: 100.0
      max_x: 330.0
      min_y: -250.0
      max_y: 250.0
      min_z: -60.0
      max_z: 160.0
    geometry:
      hover_z: 80.0              # Safe transit height (mm)
      pick_z: 12.5               # Pick suction height (mm)
      dropoff_x: 200.0           # Center goal X (mm)
      dropoff_y: 0.0             # Center goal Y (mm)
      dropoff_z: 30.0            # First cube drop Z (mm)
      cube_height: 25.0          # Stacking increment per cube (mm)
    effector:
      use_suction: true
      dwell_grip_sec: 0.35
      dwell_release_sec: 0.25
    telemetry:
      publish_rate_hz: 10.0
```

---

## ROS 2 Interface & Topics

### Published Topics

| Topic | Type | Description |
| :--- | :--- | :--- |
| `/dobot_status` | `std_msgs/msg/String` | Real-time robot state, coordinates, suction status |
| `/detected_objects` | `std_msgs/msg/String` | JSON payload of detected cubes and cell locations |
| `/detected_objects_image/compressed` | `sensor_msgs/msg/CompressedImage` | Annotated camera stream for the UI |

### Subscribed Topics

| Topic | Type | Description |
| :--- | :--- | :--- |
| `/dobot_ui_cmd` | `std_msgs/msg/String` | Control commands dispatched from `Dobot_UI` |
| `/image_raw` | `sensor_msgs/msg/Image` | Raw camera stream from `usb_cam` |

### UI Command Protocol Specification

Commands sent over `/dobot_ui_cmd`:

```json
// Jogging
{"cmd": "jog", "axis": "x", "direction": 1, "step": 10.0}

// Direct Cartesian Move
{"cmd": "move_to", "x": 200.0, "y": 0.0, "z": 80.0, "r": 0.0}

// Suction Cup
{"cmd": "suction", "enable": true}

// Gripper
{"cmd": "gripper", "grip": true}

// Presets ("home", "hover", "dropoff", "zero_r")
{"cmd": "preset", "name": "hover"}

// Emergency Stop
{"cmd": "stop"}

// Stacking Mission
{
  "cmd": "mission",
  "task_count": 8,
  "tasks": [
    {
      "order": 1,
      "index": 1,
      "cell_id": "TL",
      "color": "red",
      "pick": {"x": 128.0, "y": -48.0, "z": 12.5},
      "drop_z": 30.0
    }
  ]
}
```

### Robot Status Telemetry Specification

Published on `/dobot_status` at 10 Hz:

```json
{
  "state": "IDLE",
  "message": "Ready",
  "x": 200.0,
  "y": 0.0,
  "z": 80.0,
  "r": 0.0,
  "suction": false,
  "gripper": false,
  "connected": true
}
```

---

## Launch Files & Running

### 1. Launch All (Unified System)
To launch the camera driver, vision detector, Dobot controller, and UI dashboard together:
```bash
ros2 launch dobot_v2 dobot_system.launch.py
```

*Optional Launch Arguments:*
```bash
# Launch without camera driver (e.g. testing with mock feed or recorded bag)
ros2 launch dobot_v2 dobot_system.launch.py launch_cam:=false

# Specify custom video device
ros2 launch dobot_v2 dobot_system.launch.py video_device:=/dev/video2
```

### 2. Launch Vision & Controller Only
```bash
ros2 launch dobot_v2 dobot_vision.launch.py launch_controller:=true
```

---

## Interactive Grid Calibration Tool

```bash
ros2 run dobot_v2 calibrate_grid
```
1. Click the 4 corners of the grey pallet in clockwise order (TL $\to$ TR $\to$ BR $\to$ BL).
2. Press **`s`** to save calibration directly into `config/detection_node.yaml`.
3. Press **`q`** to exit.
