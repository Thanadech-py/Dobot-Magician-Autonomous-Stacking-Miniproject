# Dobot Magician Robot System: ROS 2, OpenCV, pydobot2 & PyQt Full Guide
## Autonomous Pick-and-Place, Multi-Color Segmentation, 3-Phase Mission Execution & Collision Avoidance (From Scratch)

> **Author / System Architect:** Thanadech (Google Deepmind Pair-Programming Assistant)  
> **Target OS & Framework:** Ubuntu Linux 22.04 LTS / ROS 2 Humble  
> **Compiled PDF Document:** [Download English PDF (`DOBOT_MAGACIAN_TUTORIAL_EN.pdf`)](file:///home/thxncdzch/dobot_ws/docs/DOBOT_MAGACIAN_TUTORIAL_EN.pdf)

---

## 🎯 Guide Objective
This comprehensive documentation is tailored for students, engineers, and researchers starting with zero robotics or ROS 2 background. It explains every concept from the ground up: communication middleware, perspective computer vision, robot kinematics, asynchronous GUI design, 3-phase automated obstacle clearance, and goal collision avoidance.

---

## Table of Contents

1. [Chapter 1: System Overview & Physical Field Geometry](#chapter-1-system-overview--physical-field-geometry)
2. [Chapter 2: ROS 2 Fundamentals from Scratch](#chapter-2-ros-2-fundamentals-from-scratch)
3. [Chapter 3: Computer Vision Pipeline with OpenCV](#chapter-3-computer-vision-pipeline-with-opencv)
4. [Chapter 4: Dobot Magician Control with pydobot2](#chapter-4-dobot-magician-control-with-pydobot2)
5. [Chapter 5: GUI Architecture with PyQt](#chapter-5-gui-architecture-with-pyqt)
6. [Chapter 6: 3-Phase Mission Execution & Collision Avoidance](#chapter-6-3-phase-mission-execution--collision-avoidance)
7. [Chapter 7: UI Dashboard Walkthrough with Screenshots](#chapter-7-ui-dashboard-walkthrough-with-screenshots)
8. [Chapter 8: Build, Execution & Troubleshooting Guide](#chapter-8-build-execution--troubleshooting-guide)

---

## Chapter 1: System Overview & Physical Field Geometry

### 1.1 Physical Layout & Coordinate Frame
The operational setup is configured on an international standard A4 sheet ($210 \times 297\text{ mm}$) with four core spatial landmarks:
1. **Dobot Magician Robot Base:** Mounted at field origin coordinates $(X = 105.0\text{ mm}, Y = 270.0\text{ mm})$.
2. **3x3 Pallet Grid:** Outer bounding footprint of $114.5 \times 114.5\text{ mm}$ with a $35.0\text{ mm}$ cell pitch. The 8 outer grid cells host colored cubes (Red, Yellow, Green, Blue, Orange, Purple, Cyan).
3. **Center Goal Cell [1, 1]:** The central drop target where selected cubes are vertically stacked (strictly locked to a 4-block maximum ceiling).
4. **4 Feeder Slots (Feeder 1 to 4):** Situated on the left perimeter strip ($Y \approx +79.3\text{ mm}$). Marked with green rings, these act as designated holding stations for obstacle cubes.

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

### 1.2 Workspace Architecture (`dobot_ws`)
- `dobot_v2`: Core vision processing node, perspective transform math, hardware serial driver, and 3-phase trajectory sequencer.
- `Dobot_UI`: Rich interactive PyQt dashboard providing camera streaming, live robot status telemetry, mission sequencing, and manual Cartesian jogging.

---

## Chapter 2: ROS 2 Fundamentals from Scratch

### 2.1 What is ROS 2?
ROS 2 (Robot Operating System 2) is a distributed robotics software middleware built on the DDS (Data Distribution Service) standard. It allows independent executable processes (Nodes) to exchange data and coordinate complex tasks seamlessly.

### 2.2 Core ROS 2 Primitives
* **Nodes (`rclpy.node.Node`):** Independent processes with single responsibilities: `detection_node` (vision), `dobot_controller` (arm hardware), `dobot_ui_node` (dashboard).
* **Topics & Publisher-Subscriber Pattern:** Asynchronous streaming data channels.

| Topic Name | Message Type | Publisher | Subscriber | Description |
|:---|:---|:---|:---|:---|
| `/detected_objects` | `std_msgs/msg/String` (JSON) | `detection_node` | `Dobot_UI`, `dobot_controller` | Real-time metric coordinates (X, Y, Z), colors, and cell assignments. |
| `/detected_objects_image/compressed` | `sensor_msgs/msg/CompressedImage` | `detection_node` | `Dobot_UI` | Low-latency compressed JPEG stream rendered in the GUI viewer. |
| `/dobot_status` | `std_msgs/msg/String` (JSON) | `dobot_controller` | `Dobot_UI` | State telemetry: X, Y, Z, R Cartesian pose, suction status, connection state. |
| `/dobot_ui_cmd` | `std_msgs/msg/String` (JSON) | `Dobot_UI` | `dobot_controller` | Control messages: mission dispatch, manual jog, homing, emergency stop. |

---

## Chapter 3: Computer Vision Pipeline with OpenCV

### 3.1 V4L2 Video Streaming
Interfacing USB webcams on Linux via Video4Linux2 (`cv2.CAP_V4L2`) with MJPG decoding delivers low-latency streaming at $640 \times 480$ resolution and 30 FPS:
```python
import cv2
cap = cv2.VideoCapture('/dev/video0', cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
ret, frame = cap.read()
```

### 3.2 Why HSV is Superior for Color Detection
- **BGR:** Pixel values shift under changing room ambient lighting and shadows.
- **HSV:** Isolates **Hue (spectral color [0..180])** from brightness, ensuring robust color detection (Red, Yellow, Green, Blue, etc.) even when lighting changes.

### 3.3 Metric Perspective Homography
The oblique camera view is transformed using a $3 \times 3$ Homography matrix (`cv2.getPerspectiveTransform`) calibrated from the 4 grid corners. Centroids in pixel space $(u, v)$ map directly to table millimeters $(gx, gy)$ and robot base coordinates $(rx, ry, rz)$.

---

## Chapter 4: Dobot Magician Control with pydobot2

### 4.1 Serial Protocol & Coordinate Envelope
- Communicates over USB-to-UART serial at **115200 bps**.
- Cartesian Envelope:
  - **X (mm):** Forward/backward (100.0 to 330.0 mm)
  - **Y (mm):** Lateral left/right (-250.0 to +250.0 mm)
  - **Z (mm):** Vertical height (-60.0 to +160.0 mm)
  - **R (deg):** End-effector rotation (-180.0° to +180.0°)

### 4.2 PTP Motion Modes
- `MOVJ_XYZ` (Joint Movement): High-speed curved trajectory for transit across open space.
- `MOVL_XYZ` (Linear Movement): Pure Cartesian straight-line motion at $90^\circ$ vertical for descending onto cubes and rising clear of neighbors without collisions.

---

## Chapter 5: GUI Architecture with PyQt

### 5.1 Resolving GUI Freezing with `QThread`
Running `rclpy.spin()` on the main GUI thread causes UI freezing. We decouple execution:
1. **Main UI Thread:** Handles mouse clicks, layouts, and widget painting.
2. **Worker Thread (`RosBridge(QThread)`):** Continuously spins ROS 2 in the background and emits updates via thread-safe `pyqtSignal` events.

---

## Chapter 6: 3-Phase Mission Execution & Collision Avoidance

### 6.1 3-Phase Mission Workflow
1. **Phase 1 (Clear Obstacles):** Non-goal cubes are cleared to **Feeder Slots 1..4** on the left.
2. **Phase 2 (Stack Goal):** Target cubes are picked in sequence (#1..#4) and vertically stacked at **Center Goal [1, 1]** (locked to max 4 blocks: $Z = 30, 55, 80, 105\text{ mm}$).
3. **Phase 3 (Restore Obstacles):** Once goal stacking finishes, all obstacle cubes in the feeders are returned to their original grid slots.

### 6.2 Goal Collision Avoidance System
- **Keepout Cylinder ($R = 38.0\text{ mm}$):** Protected zone around Center Goal $(176.0, 0.0)$.
- **Corridor Detour Waypoints:** Evaluates straight-line paths and detours around the perimeter if a collision is detected:
  - **North Bypass:** Detours via $X = 222.0\text{ mm}$ (above row 0).
  - **South Bypass:** Detours via $X = 132.0\text{ mm}$ (below row 2).
- **Elevated Vertical Clearance:** Elevates transit height to $Z = 142.0\text{ mm}$ whenever cubes exist on the goal, safely clearing the $130\text{ mm}$ 4-block tower.

---

## Chapter 7: UI Dashboard Walkthrough with Screenshots

### 7.1 Stacking Mission Tab
![Stacking Mission UI](file:///home/thxncdzch/dobot_ws/docs/images/ui_mission_tab.png)

- **Auto Buttons:** `↻ Auto 1..4 (Goal)`, `↻ Auto All (4 Goal + 4 Obs)`, `🧹 Auto Obs`
- **Execution Plan Table:** Displays all 3 phases in real-time with color-coded status badges.

### 7.2 Manual Control Tab
![Manual Control UI](file:///home/thxncdzch/dobot_ws/docs/images/ui_manual_tab.png)

- **Quick Presets:** Instant positioning to `Home`, `Hover`, `Drop-off`, `Zero R`.
- **Cartesian Jog:** Directional buttons for $X, Y, Z, R$ with step size selection ($1, 5, 10, 50\text{ mm}$).
- **Tool Control:** Suction cup pump toggle (`SUCTION`) and gripper controls (`GRIP` / `RELEASE`).

### 7.3 Teach Positions Tab (Vision Bypass)
![Teach Positions UI](file:///home/thxncdzch/dobot_ws/docs/images/ui_teach_tab.png)

- Jog the robot tip to touch any cell or feeder and record coordinates with `📍 Teach`.
- Save all calibrated positions to `dobot_ui.yaml` with `💾 Save All Positions to YAML`.

---

## Chapter 8: Build, Execution & Troubleshooting Guide

### 8.1 Build & Launch Commands
```bash
# Source ROS 2 Humble and build workspace
cd /home/thxncdzch/dobot_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

# Launch complete system (Vision + Controller + GUI)
ros2 launch dobot_v2 dobot_system.launch.py

# Or launch GUI in simulation mode (no hardware required)
ros2 launch Dobot_UI dobot_ui.launch.py mock:=true
```

### 8.2 USB Permissions on Linux
```bash
sudo usermod -a -G dialout $USER
sudo chmod 666 /dev/ttyUSB0
```
