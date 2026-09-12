# Dobot_UI: ROS 2 PyQt Mission Dashboard & Manual Control for Dobot Magician

A modular, lightweight, and responsive Graphical User Interface (GUI) package for the **Dobot Magician** robotic arm, vision-guided cube stacking missions, and manual Cartesian jogging.

The UI visualizes the live camera feed and object detections from `dobot_v2`, provides real-time Dobot telemetry (Cartesian X, Y, Z, R and suction status), provides interactive 1st-to-8th mission planning from a 3x3 grid, and features an integrated **Manual Control Panel** for jogging, tool testing, and direct coordinate positioning.

---

## Table of Contents

- [Overview & Workflow](#overview--workflow)
- [Package Architecture](#package-architecture)
- [Key Features & UI Layout](#key-features--ui-layout)
  - [1. Action Toolbar](#1-action-toolbar)
  - [2. Live Vision & Camera Viewer](#2-live-vision--camera-viewer)
  - [3. Robot Telemetry Panel](#3-robot-telemetry-panel)
  - [4. Mission Planner Tab](#4-mission-planner-tab)
  - [5. Manual Control & Jogging Tab](#5-manual-control--jogging-tab)
  - [6. System Event Log](#6-system-event-log)
- [ROS 2 Interface & Topics](#ros-2-interface--topics)
- [Configuration System (`dobot_ui.yaml`)](#configuration-system-dobot_uiyaml)
- [Build & Run Instructions](#build--run-instructions)
- [Troubleshooting & FAQ](#troubleshooting--faq)

---

## Overview & Workflow

The workspace layout combines:
1. **Live Camera Feed & Detections**: Streams compressed video from `dobot_v2/detection_node`.
2. **Interactive 3x3 Mission Grid**: Represents the 8 outer cube cells and central stacking goal.
3. **Sequential Stacking Planner**: Generates ordered stacking tasks (#1 on bottom to #8 on top) with calculated pick/drop coordinates.
4. **Manual Control & Cartesian Jogging**: Allows fine-positioning along $X, Y, Z, R$, tool toggling, and direct coordinate moves while watching the live camera and telemetry.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 🤖 DOBOT MISSION UI   [⚡ Connect] [🏠 Home] [🎮 Manual Mode] ... [▶ START] [🛑 STOP]  │
├──────────────────────────────────────────┬─────────────────────────────────────────────┤
│ 🎥 Live Camera Stream                    │  [ 🎯 Stacking Mission ] [ 🎮 Manual Control ]│
│                                          ├─────────────────────────────────────────────┤
│                                          │  QUICK PRESETS                              │
│                                          │  [🏠 Home] [🛡️ Hover] [📦 Drop-off] [Zero R]│
│                                          ├─────────────────────────────────────────────┤
│                                          │  CARTESIAN JOG                              │
│                                          │  Step: (•) 1mm  ( ) 5mm  ( ) 10mm  ( ) 50mm │
│                                          │       [▲ +X]         [▲ +Z]      [↺ R-]     │
│                                          │  [◀ +Y] [XY] [-Y ▶]                         │
│                                          │       [▼ -X]         [▼ -Z]      [↻ R+]     │
│                                          ├─────────────────────────────────────────────┤
│ 📊 Dobot Magician Status (Telemetry)     │  END-EFFECTOR TOOL CONTROL                  │
│  [IDLE]  Suction: OFF                    │  [ 💨 SUCTION: OFF/ON ]  [ ✊ GRIP ] [ 🖐️ RELEASE]│
│  [ X: 200.0 ] [ Y: 0.0 ] [ Z: 80.0 ] ... ├─────────────────────────────────────────────┤
│                                          │  DIRECT POSITION (MOVE TO)                  │
│                                          │  X: [200.0]  Y: [0.0]  Z: [80.0]  R: [0.0]   │
│                                          │  [📥 Copy Pose]   [🚀 Move To]   [🛑 Stop]  │
├──────────────────────────────────────────┴─────────────────────────────────────────────┤
│ 📝 System Event Log & Console                                                          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Package Architecture

```
src/Dobot_UI/
├── config/
│   └── dobot_ui.yaml             # Configurable geometry, topic mappings, defaults
├── launch/
│   └── dobot_ui.launch.py        # ROS 2 launch file supporting topic remappings & mock mode
├── Dobot_UI/
│   ├── __init__.py               # Package exports
│   ├── app.py                    # Entry point & QApplication lifecycle
│   ├── config.py                 # Multi-path YAML configuration loader
│   ├── constants.py              # Dark theme QSS stylesheet (QTabWidget, buttons, spinboxes)
│   ├── ros_bridge.py             # QThread ROS 2 bridge (pub/sub & interactive mock fallback)
│   ├── main_window.py            # QMainWindow integrating layouts, tabs, and signal dispatch
│   ├── models/
│   │   ├── __init__.py           # Grid definitions, cell math, coordinate conversions
│   │   └── grid_model.py         # Backward compatibility re-export
│   └── widgets/
│       ├── __init__.py           # Widget exports
│       ├── control_bar_widget.py # Action toolbar & mode toggle button
│       ├── video_widget.py       # Camera feed viewer with FPS and reset node button
│       ├── grid_widget.py        # 3x3 interactive mission grid cards
│       ├── sequence_widget.py    # 1st-to-8th execution sequence table
│       ├── manual_control_widget.py # Cartesian jog, step selector, move_to, tool controls
│       ├── robot_telemetry_widget.py # Cartesian coordinates & suction indicator
│       └── log_widget.py         # Color-coded system event log console
├── package.xml
└── setup.py
```

---

## Key Features & UI Layout

### 1. Action Toolbar (`ControlBarWidget`)
- **⚡ Connect**: Commands controller to connect to serial port.
- **🏠 Home**: Commands Dobot axis homing sequence.
- **🎮 Manual Mode / 🎯 Mission Mode**: One-click toggle switching the right panel between Stacking Mission and Manual Control.
- **🔄 Reset Detection Node**: Gracefully terminates any hanging vision process and relaunches `detection_node`.
- **▶ START STACKING (1st..8th)**: Formulates structured mission JSON and dispatches to controller.
- **🛑 EMERGENCY STOP**: Immediately halts robot motion and clears mission queues.

### 2. Live Vision & Camera Viewer (`VideoWidget`)
- Displays compressed image stream from `dobot_v2` with live FPS counter.
- Aspect-ratio preserving auto-scaling.

### 3. Robot Telemetry Panel (`RobotTelemetryWidget`)
- Displays live robot state (`IDLE`, `MOVING`, `BUSY`, `ERROR`).
- Real-time Cartesian coordinates: **X**, **Y**, **Z** in mm, and **R** in degrees.
- Live suction status badge (`SUCTION: ON` in green, `SUCTION: OFF` in muted grey).

### 4. Mission Planner Tab (`FieldGridWidget` & `SequenceWidget`)
- **3x3 Grid Cards**: Interactive cell assignment for 8 outer cubes.
- **Sync from Vision**: Automatically assigns detected cube colors to grid cells from live camera feed.
- **Auto 1..8**: Instantly assigns sequential order clockwise.
- **Sequence Table**: Lists order, grid cell, color, and vertical drop height ($Z_{drop}$).

### 5. Manual Control & Jogging Tab (`ManualControlWidget`)
- **Quick Presets**: Jump directly to `Home`, `Hover` ($Z=80\,\text{mm}$), `Drop-off` ($Z=30\,\text{mm}$), or `Zero R` ($R=0^\circ$).
- **Cartesian Jogging**:
  - Linear step: $1\,\text{mm}$, $5\,\text{mm}$, $10\,\text{mm}$, $50\,\text{mm}$.
  - Rotation step: $5^\circ$ adjustable.
  - Directional D-Pad: $+X$ (forward), $-X$ (backward), $+Y$ (left), $-Y$ (right), $+Z$ (up), $-Z$ (down), $\circlearrowleft R-$ (CCW), $\circlearrowright R+$ (CW).
- **End-Effector Tool Control**:
  - Suction Cup toggle button with active green indicator.
  - Pneumatic/servo `GRIP` and `RELEASE` buttons.
- **Direct Position (Move To)**:
  - Coordinate inputs ($X, Y, Z, R$) with Dobot physical workspace limits.
  - `📥 Copy Pose`: Copies current live robot telemetry into inputs.
  - `🚀 Move To`: Commands direct PTP travel to target coordinates.

### 6. System Event Log (`LogWidget`)
- Color-coded timestamped log messages (`INFO`, `WARN`, `ERROR`, `SUCCESS`).

---

## ROS 2 Interface & Topics

| Topic | Direction | Type | Description |
| :--- | :--- | :--- | :--- |
| `detected_objects_image/compressed` | Subscribed | `sensor_msgs/msg/CompressedImage` | Annotated vision stream |
| `detected_objects` | Subscribed | `std_msgs/msg/String` | Detected cubes JSON |
| `dobot_status` | Subscribed | `std_msgs/msg/String` | Real-time Dobot telemetry |
| `dobot_ui_cmd` | Published | `std_msgs/msg/String` | Dispatched UI & manual commands |

---

## Build & Run Instructions

### 1. Build Package
```bash
colcon build --packages-select Dobot_UI --symlink-install
source install/setup.bash
```

### 2. Run with ROS 2
```bash
ros2 launch Dobot_UI dobot_ui.launch.py
```

### 3. Run in Simulation / Mock Mode (No Hardware Required)
```bash
# Standalone execution with interactive mock feed & telemetry
python3 src/Dobot_UI/Dobot_UI/app.py --mock
```

---

## Troubleshooting & FAQ

- **UI opens but camera shows "Waiting for video stream"**: Ensure `detection_node` or `dobot_system.launch.py` is running, or click `🔄 Reset Detection Node`.
- **Manual jog buttons don't move physical robot**: Ensure the robot is connected by clicking `⚡ Connect` first, and check that `dobot_controller` is running.
