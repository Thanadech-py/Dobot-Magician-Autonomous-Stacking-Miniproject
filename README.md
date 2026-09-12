# Dobot Magician Autonomous Stacking Workspace (`dobot_ws`)

A complete ROS 2 robotics workspace for the **Dobot Magician** robotic arm featuring real-time perspective computer vision, automated 8-cube stacking, manual Cartesian jogging controls, and an interactive PyQt mission dashboard.

---

## Workspace Architecture

```
dobot_ws/
├── src/
│   ├── dobot_v2/                 # Vision tracking, perspective homography & robot arm controller
│   │   ├── config/
│   │   │   ├── dobot_controller.yaml  # Robot kinematics, limits, geometry, effector dwell
│   │   │   ├── detection_node.yaml    # Vision geometry, homography corners, HSV color bounds
│   │   │   └── usb_cam.yaml           # Camera parameters
│   │   ├── dobot_v2/
│   │   │   ├── dobot_controller_node.py # Hardware controller node interfacing UI & arm
│   │   │   ├── dobot_driver.py          # Thread-safe pydobot driver & simulation fallback
│   │   │   ├── mission_executor.py      # Trajectory generator & sequential stacking engine
│   │   │   ├── detection_node.py        # Vision tracker & cube coordinate publisher
│   │   │   ├── transforms.py            # Perspective homography & metric conversions
│   │   │   ├── grid_detector.py         # Pallet contouring & corner locking
│   │   │   ├── cube_detector.py         # Multi-color cube segmenter
│   │   │   ├── visualizer.py            # HUD drawing & visual overlay rendering
│   │   │   └── calibrate_grid.py        # Interactive 4-corner calibration GUI
│   │   └── launch/
│   │       ├── dobot_system.launch.py   # Unified launcher (Cam + Vision + Controller + UI)
│   │       └── dobot_vision.launch.py   # Dedicated vision launcher
│   │
│   ├── Dobot_UI/                 # Modern dark-themed PyQt mission dashboard & manual control
│   │   ├── config/
│   │   │   └── dobot_ui.yaml            # UI geometry, topic mappings, defaults
│   │   ├── Dobot_UI/
│   │   │   ├── app.py                   # UI entry point & event loop
│   │   │   ├── main_window.py           # Splitter window with tabs (Mission & Manual)
│   │   │   ├── ros_bridge.py            # ROS 2 communication bridge & interactive mock mode
│   │   │   └── widgets/
│   │   │       ├── manual_control_widget.py # Cartesian jog D-pad, tool toggle, direct move-to
│   │   │       ├── grid_widget.py           # Interactive 3x3 mission grid cards
│   │   │       ├── sequence_widget.py       # 1st-to-8th stacking sequence table
│   │   │       ├── video_widget.py          # Live annotated video stream viewer
│   │   │       ├── robot_telemetry_widget.py # Live Cartesian X/Y/Z/R readout
│   │   │       ├── control_bar_widget.py    # Top toolbar & mode toggle button
│   │   │       └── log_widget.py            # System event log
│   │   └── launch/
│   │       └── dobot_ui.launch.py
│   │
│   └── dobot_project/            # Baseline prototype implementation & reference utilities
└── README.md
```

---

## Quick Start (Single-Command Run)

### 1. Launch Everything Together
To launch the camera driver, vision detector, Dobot controller, and UI dashboard with a single command:
```bash
ros2 launch dobot_v2 dobot_system.launch.py
```

### 2. Standalone Simulation / Mock Mode (No Hardware Required)
You can test the entire UI interface, live simulated vision feed, manual jogging, and telemetry without physical hardware:
```bash
python3 src/Dobot_UI/Dobot_UI/app.py --mock
```

---

## System Workflow & Capabilities

### 1. Vision-Guided Cube Stacking
1. Place 8 colored cubes (Red, Yellow, Green, Blue, etc.) on the outer cells of the 3x3 pallet grid.
2. The overhead camera detects each cube's centroid and computes its metric coordinates in the Dobot base frame.
3. In [`Dobot_UI`](file:///home/thxncdzch/dobot_ws/src/Dobot_UI), click **Sync from Vision** or customize the stack sequence (#1 to #8).
4. Click **▶ START STACKING** to command Dobot to sequentially pick each cube and stack them at the center goal cell.

### 2. Full Manual Jogging & Tool Control
1. Click the **🎮 Manual Mode** button in the toolbar or select the **🎮 Manual Control** tab.
2. Watch the live camera feed and real-time coordinates on the left.
3. Select step size ($1\,\text{mm}$, $5\,\text{mm}$, $10\,\text{mm}$, $50\,\text{mm}$) and jog along $X, Y, Z, R$ using the directional D-pad.
4. Toggle the suction cup or gripper on/off with instant feedback.
5. Use **📥 Copy Pose** to grab current coordinates, adjust values, and click **🚀 Move To**.

---

## Prerequisites & Installation

### ROS 2 & System Packages
```bash
sudo apt update
sudo apt install -y ros-humble-desktop ros-humble-usb-cam ros-humble-cv-bridge python3-pip
```

### Python Dependencies
```bash
pip install pydobot2 PyQt5 opencv-python pyyaml numpy
```

### Serial Port Permissions
To allow non-root communication with the Dobot USB serial device:
```bash
sudo usermod -a -G dialout $USER
```
*(Log out and log back in for group permissions to take effect)*

---

## Package References & Documentation

- [**`dobot_v2` Documentation**](file:///home/thxncdzch/dobot_ws/src/dobot_v2/README.md): Vision tracking, homography math, controller node, and configuration guide.
- [**`Dobot_UI` Documentation**](file:///home/thxncdzch/dobot_ws/src/Dobot_UI/README.md): Mission dashboard, manual control panel, telemetry, and topics.
- [**`dobot_project` Documentation**](file:///home/thxncdzch/dobot_ws/src/dobot_project/README.md): Prototype package and reference scripts.
