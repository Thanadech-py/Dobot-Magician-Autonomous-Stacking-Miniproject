# Dobot_UI: ROS 2 PyQt6 Mission Interface for Dobot Magician

A modular, lightweight, and responsive Graphical User Interface (GUI) package built for the **Dobot Magician** robotic arm and vision-guided pick-and-place cube stacking missions.

The UI visualizes the live camera feed and object detections from `dobot_v2`, provides real-time Dobot telemetry, and enables operators to plan and execute custom 1st-to-8th cube stacking orders from a 3x3 mission field grid into a central stacking zone.

---

## Table of Contents

- [Overview & Workflow](#overview--workflow)
- [Package Architecture](#package-architecture)
- [Key Features & UI Layout](#key-features--ui-layout)
- [Mathematical & Coordinate Model](#mathematical--coordinate-model)
- [Configuration System (`dobot_ui.yaml`)](#configuration-system-dobot_uiyaml)
- [ROS 2 Interface & Topics](#ros-2-interface--topics)
- [Prerequisites & Dependencies](#prerequisites--dependencies)
- [Build & Run Instructions](#build--run-instructions)
- [Operational Guide (Step-by-Step)](#operational-guide-step-by-step)
- [Troubleshooting & FAQ](#troubleshooting--faq)

---

## Overview & Workflow

The mission field consists of a **3x3 grid** positioned on an A4 reference workspace in front of the Dobot Magician:
- **8 Outer Cells**: Contain colored cubes (Red, Yellow, Green, Blue, Orange, Purple, Cyan) placed at specific grid positions: Top-Left, Top, Top-Right, Left, Right, Bottom-Left, Bottom, Bottom-Right.
- **Center Goal Cell (1, 1)**: The destination target where cubes are stacked vertically in a user-selected sequence (1st cube on the bottom to 8th cube on the top).

```
+-------------------+-------------------+-------------------+
|  [0,0] Top-Left   |    [0,1] Top      |  [0,2] Top-Right  |
|      (Cube)       |      (Cube)       |      (Cube)       |
+-------------------+-------------------+-------------------+
|    [1,0] Left     |   [1,1] GOAL      |   [1,2] Right     |
|      (Cube)       | (Stacking Center) |      (Cube)       |
+-------------------+-------------------+-------------------+
| [2,0] Bottom-Left |   [2,1] Bottom    | [2,2] Bottom-Right|
|      (Cube)       |      (Cube)       |      (Cube)       |
+-------------------+-------------------+-------------------+
```

### High-Level Operation:
1. Overhead camera stream is captured and processed by `dobot_v2/detection_node`.
2. `Dobot_UI` displays the live stream and can automatically synchronize detected cube colors to their respective cells with one click (**Sync from Vision**).
3. The operator assigns or customizes the stacking order (**#1 to #8**) for each cell or uses **Auto 1..8**.
4. The sequence table computes physical Dobot coordinates (X, Y, Z) and stacking heights (`drop_z`).
5. Clicking **START STACKING** dispatches a structured JSON mission command to the robot controller via `/dobot_ui_cmd`.

---

## Package Architecture

To ensure high maintainability and ease of debugging, the package follows strict separation of concerns into small, modular files (typically under 100 lines each):

```
src/Dobot_UI/
├── config/
│   └── dobot_ui.yaml             # All configurable parameters (geometry, topics, defaults)
├── launch/
│   └── dobot_ui.launch.py        # ROS 2 launch file supporting topic remappings & mock mode
├── Dobot_UI/
│   ├── __init__.py               # Package metadata and module aliases
│   ├── app.py                    # Application entry point & Qt event loop lifecycle
│   ├── config.py                 # Multi-path YAML loader with built-in safe defaults
│   ├── constants.py              # Dark theme QSS stylesheet
│   ├── ros_bridge.py             # QThread ROS 2 node (pub/sub, process manager, mock feed)
│   ├── main_window.py            # QMainWindow integrating layouts with QSplitter
│   ├── models/
│   │   ├── __init__.py           # Grid definitions, cell metadata, coordinate math
│   │   └── grid_model.py         # Backward compatibility re-export
│   └── widgets/
│       ├── __init__.py           # Widget exports
│       ├── control_bar_widget.py # Action toolbar (Connect, Home, Reset Node, Start, Stop)
│       ├── video_widget.py       # Camera feed viewer with live FPS and reset button
│       ├── grid_widget.py        # 3x3 interactive mission grid cards
│       ├── sequence_widget.py    # 1st-to-8th execution sequence table
│       ├── robot_telemetry_widget.py # Dobot state, Cartesian X/Y/Z/R, suction status
│       └── log_widget.py         # Color-coded system event log console
├── resource/
│   ├── Dobot_UI                  # ament package resource index marker
│   └── dobot_ui                  # lowercase alias marker
├── test/                         # Unit and lint tests (flake8, copyright, pep257)
├── package.xml                   # ROS 2 package manifest with dependencies
└── setup.py                      # Ament Python setup & console scripts
```

---

## Key Features & UI Layout

The application window is organized into functional panels using an adjustable splitter:

### 1. Control Toolbar (`ControlBarWidget`)
- **⚡ Connect**: Publishes `{"cmd": "connect"}` to initialize communication with Dobot Magician.
- **🏠 Home**: Publishes `{"cmd": "home"}` to trigger Dobot axis homing calibration.
- **🔄 Reset Detection Node**: Terminates any hung `detection_node` process, releases device locks, relaunches the node, and resets homography calibration.
- **▶ START STACKING (1st..8th)**: Formulates the mission payload and sends pick/drop coordinates to the controller.
- **🛑 EMERGENCY STOP**: Immediately publishes `{"cmd": "stop"}` to halt robot motion.

### 2. Live Vision Stream (`VideoWidget`)
- Renders JPEG/PNG compressed image frames (`sensor_msgs/msg/CompressedImage`) from the detection pipeline.
- Calculates and displays real-time frame rates (**FPS**).
- Includes a dedicated quick-action **Reset Node** button in the header bar.
- Generates an active simulated animation feed when running in standalone `--mock` mode.

### 3. Interactive 3x3 Field Grid (`FieldGridWidget`)
- **8 Outer Cell Cards**: Each cell features:
  - Coordinate label: `[row, col]` and abbreviation (`TL`, `T`, `TR`, `L`, `R`, `BL`, `B`, `BR`).
  - **Stack Order Selector**: Dropdown to choose `#1` through `#8` (or `None`).
  - **Color Selector**: Dropdown for cube color (`Red`, `Yellow`, `Green`, `Blue`, `Orange`, `Purple`, `Cyan`, `None`).
  - Dynamic visual feedback: The border of each cell card changes color to match the selected cube color.
- **Center Goal Cell**: Highlighted in gold dashed styling indicating the stacking destination.
- **🔄 Sync from Vision**: Reads the latest detections published by `dobot_v2` and automatically selects corresponding colors in each cell.
- **↻ Auto 1..8**: Fast preset that orders all outer cells clockwise starting from Top-Left.

### 4. Stacking Sequence Table (`SequenceWidget`)
- Renders a 4-column execution plan sorted strictly by stack order (1 to 8):
  1. **Stack #**: Indicates position (`#1 (Base)`, `#2` ... `#8 (Top)`).
  2. **Grid Cell**: Identifies source cell name and coordinates (e.g., `[0,0] Top-Left`).
  3. **Color**: Formatted in matching colored badges.
  4. **Drop Z**: Calculated drop height in millimeters (e.g., `Z = 30.0 mm`, `Z = 55.0 mm`, etc.).
- Summary footer shows total active tasks and final top-of-stack height.

### 5. Robot Telemetry (`RobotTelemetryWidget`)
- **State Banner**: Shows arm status (`IDLE`, `RUNNING`, `HOMING`, `ERROR`) and controller messages.
- **Coordinate Readouts**: High-visibility digital panels for **X (mm)**, **Y (mm)**, **Z (mm)**, and **R (deg)**.
- **Suction Status**: Clear badge indicating whether the vacuum gripper is `ON` (green) or `OFF` (gray).

### 6. Event Log Console (`LogWidget`)
- Rolling timestamped log console with distinct syntax highlighting:
  - `[INFO]` (Green): Normal operations, topic connections, commands sent.
  - `[WARN]` (Yellow): Detection node restarts, simulation notices.
  - `[ERROR]` (Red): ROS 2 communication errors or missing parameters.
- Includes a **Clear Log** utility button.

---

## Mathematical & Coordinate Model

The pick-and-place coordinates are calculated deterministically using the physical field geometry defined in [`config/dobot_ui.yaml`](file:///home/thxncdzch/dobot_ws/src/Dobot_UI/config/dobot_ui.yaml):

### 1. Grid Cell to Field Millimeters
For cell indices `row ∈ {0, 1, 2}` and `col ∈ {0, 1, 2}`:
$$gx = \text{origin\_offset\_x} + col \times \text{cell\_pitch\_mm} = 22.0 + col \times 35.0$$
$$gy = \text{origin\_offset\_y} + row \times \text{cell\_pitch\_mm} = 22.0 + row \times 35.0$$

Relative to the A4 reference sheet:
$$\text{field\_x} = \text{grid\_tl\_x\_mm} + gx = 48.0 + gx$$
$$\text{field\_y} = \text{grid\_tl\_y\_mm} + gy = 37.0 + gy$$

### 2. Field to Dobot Arm Base Coordinates
$$\text{rx} = \text{robot\_base\_y\_mm} - \text{field\_y} = 270.0 - \text{field\_y}$$
$$\text{ry} = \text{robot\_base\_x\_mm} - \text{field\_x} = 105.0 - \text{field\_x}$$
$$\text{rz} = \text{pick\_z\_mm} = 12.5\text{ mm}$$

### 3. Vertical Stacking Drop Z
For task order $k \in \{1, \dots, 8\}$:
$$\text{drop\_z} = \text{base\_drop\_z\_mm} + (k - 1) \times \text{cube\_height\_mm} = 30.0 + (k - 1) \times 25.0$$

---

## Configuration System (`dobot_ui.yaml`)

All parameters are externalized in [`config/dobot_ui.yaml`](file:///home/thxncdzch/dobot_ws/src/Dobot_UI/config/dobot_ui.yaml). You can modify topic names, physical offsets, or default behaviors without altering Python code:

```yaml
# ── ROS 2 Topics ──────────────────────────────────────────────────
topics:
  image_raw:   "detected_objects_image"
  image_comp:  "detected_objects_image/compressed"
  detections:  "detected_objects"
  status:      "dobot_status"
  command:     "dobot_ui_cmd"
  reset_grid:  "reset_grid"

# ── Window Settings ───────────────────────────────────────────────
window:
  title:  "Dobot Magician - Stacking Mission UI"
  width:  1100
  height: 750

# ── Grid & Field Geometry (mm) ────────────────────────────────────
grid:
  cell_pitch_mm:    35.0   # Center-to-center distance between adjacent cells
  origin_offset_x:  22.0   # Offset of first cell center in grid frame
  origin_offset_y:  22.0
  grid_tl_x_mm:    48.0   # A4 sheet top-left X offset
  grid_tl_y_mm:    37.0   # A4 sheet top-left Y offset
  robot_base_x_mm: 105.0  # Robot origin X on A4 sheet
  robot_base_y_mm: 270.0  # Robot origin Y on A4 sheet
  pick_z_mm:        12.5   # Suction pick height

# ── Stacking Mission ──────────────────────────────────────────────
stacking:
  base_drop_z_mm:  30.0   # Drop Z height for 1st cube (bottom of stack)
  cube_height_mm:  25.0   # Stacking height increment per layer

# ── Default Cell Assignments ──────────────────────────────────────
cell_defaults:
  orders: [1, 2, 3, 4, 5, 6, 7, 8]
  colors: ["red", "yellow", "green", "blue", "orange", "purple", "cyan", "red"]

# ── Detection Node Process Management ─────────────────────────────
detection_node:
  ros2_package:      "dobot_v2"
  ros2_node:         "detection_node"
  installed_exe:     "/home/thxncdzch/dobot_ws/install/dobot_v2/lib/dobot_v2/detection_node"
  src_script:        "/home/thxncdzch/dobot_ws/src/dobot_v2/dobot_v2/detection_node.py"
  restart_delay_sec: 0.5

# ── Badge Color Palette ───────────────────────────────────────────
color_hex:
  red:    "#ef4444"
  yellow: "#eab308"
  green:  "#22c55e"
  blue:   "#3b82f6"
  orange: "#f97316"
  purple: "#a855f7"
  cyan:   "#06b6d4"
  none:   "#64748b"
```

### Config Loading Order
[`Dobot_UI/config.py`](file:///home/thxncdzch/dobot_ws/src/Dobot_UI/Dobot_UI/config.py) discovers the YAML file using a resilient priority cascade:
1. Environment variable `DOBOT_UI_CONFIG` (if specified).
2. Standard ROS 2 share directory (`ament_index_python.packages.get_package_share_directory('Dobot_UI')`).
3. Source directory relative path (`../config/dobot_ui.yaml`).
4. Install directory relative path (`../../../../share/Dobot_UI/config/dobot_ui.yaml`).
5. Built-in hardcoded fallback dictionary (guarantees the UI will launch even if the YAML is missing or invalid).

---

## ROS 2 Interface & Topics

### Subscribed Topics

| Topic | Message Type | Description |
|---|---|---|
| `detected_objects_image/compressed` | `sensor_msgs/msg/CompressedImage` | Annotated camera feed from vision node |
| `detected_objects` | `std_msgs/msg/String` | JSON string containing detected objects and cell positions |
| `dobot_status` | `std_msgs/msg/String` | JSON string containing arm state, coordinates, suction status |

#### Telemetry JSON Payload Schema (`dobot_status`):
```json
{
  "state": "IDLE",
  "x": 210.5,
  "y": 35.0,
  "z": 50.0,
  "r": 0.0,
  "suction": false,
  "message": "Connected"
}
```

#### Detections JSON Payload Schema (`detected_objects`):
```json
{
  "objects": [
    {
      "color": "red",
      "cell": {"row": 0, "col": 0},
      "robot_mm": {"x": 211.0, "y": 35.0, "z": 12.5}
    }
  ]
}
```

### Published Topics

| Topic | Message Type | Description |
|---|---|---|
| `dobot_ui_cmd` | `std_msgs/msg/String` | JSON commands dispatched to robot controller |
| `reset_grid` | `std_msgs/msg/String` | Triggers detection node homography and grid reset |

#### Mission Command Schema (`dobot_ui_cmd`):
```json
{
  "cmd": "mission",
  "task_count": 8,
  "tasks": [
    {
      "order": 1,
      "index": 1,
      "cell_id": 0,
      "color": "red",
      "pick": {"x": 211.0, "y": 35.0, "z": 12.5},
      "drop_z": 30.0
    },
    {
      "order": 2,
      "index": 2,
      "cell_id": 1,
      "color": "yellow",
      "pick": {"x": 211.0, "y": 0.0, "z": 12.5},
      "drop_z": 55.0
    }
  ]
}
```

#### Other Commands:
- Connection: `{"cmd": "connect"}`
- Homing: `{"cmd": "home"}`
- Emergency Stop: `{"cmd": "stop"}`

---

## Prerequisites & Dependencies

- **ROS 2 Distribution**: Humble Hawksbill (Ubuntu 22.04 LTS)
- **Python**: 3.10+
- **GUI Framework**: PyQt6 (recommended) or PyQt5 (supported automatically)
- **Computer Vision**: OpenCV (`opencv-python`), NumPy
- **Parser**: PyYAML (`python3-yaml`)

To install required system libraries:
```bash
sudo apt update
sudo apt install -y python3-pyqt5 python3-pyqt5.qtwidgets python3-yaml python3-opencv
# Optional: install PyQt6 via pip if preferred
pip install PyQt6
```

---

## Build & Run Instructions

### 1. Build the Package
From your ROS 2 workspace root:
```bash
cd ~/dobot_ws
colcon build --packages-select Dobot_UI
source install/setup.bash
```

### 2. Run with ROS 2
```bash
ros2 run Dobot_UI dobot_ui
```

### 3. Run with ROS 2 Launch File
The launch file supports runtime argument overrides:
```bash
# Default launch
ros2 launch Dobot_UI dobot_ui.launch.py

# Launch in simulated/mock mode
ros2 launch Dobot_UI dobot_ui.launch.py mock_mode:=true

# Override image topic
ros2 launch Dobot_UI dobot_ui.launch.py image_compressed_topic:=/camera/image/compressed
```

### 4. Standalone Simulation Mode (No Robot Hardware Needed)
For rapid UI testing or previewing without a live Dobot arm or camera:
```bash
python3 -m Dobot_UI.app --mock
# or execute directly
python3 ~/dobot_ws/src/Dobot_UI/Dobot_UI/app.py --mock
```

---

## Operational Guide (Step-by-Step)

1. **Power On & Connect Hardware**:
   - Ensure the Dobot Magician is powered on and connected via USB.
   - Launch camera / detection node: `ros2 run dobot_v2 detection_node`.
   - Launch Dobot controller driver node.
2. **Launch the UI**:
   - Run `ros2 run Dobot_UI dobot_ui`.
3. **Initialize Robot**:
   - Click **⚡ Connect** to open serial communication.
   - Click **🏠 Home** to calibrate arm joint limits.
4. **Calibrate Vision & Grid**:
   - Ensure the A4 mission paper is visible in the camera view.
   - If corners need recalibration, click **🔄 Reset Detection Node**.
5. **Assign Stacking Sequence**:
   - Click **🔄 Sync from Vision** to pull detected cube colors into the grid.
   - Adjust the dropdown order numbers (`#1` to `#8`) as desired, or click **↻ Auto 1..8**.
   - Verify the sequence and target `Drop Z` heights in the **STACKING SEQUENCE** table.
6. **Execute Stacking**:
   - Click **▶ START STACKING (1st..8th)**.
   - Monitor live telemetry in the **DOBOT MAGICIAN STATUS** panel and events in the **SYSTEM EVENT LOG**.
   - If an unexpected collision occurs, immediately press **🛑 EMERGENCY STOP**.

---

## Troubleshooting & FAQ

### 1. `FileNotFoundError: No such file or directory: '.../config/dobot_ui.yaml'`
- **Cause**: The configuration loader path is desynchronized between install and source trees.
- **Solution**: Rebuild the package with `colcon build --packages-select Dobot_UI` and source `install/setup.bash`. The config loader will automatically resolve the share directory.

### 2. `ModuleNotFoundError: No module named 'PyQt6'`
- **Cause**: PyQt6 is not installed on the system.
- **Solution**: The application includes an automatic fallback to PyQt5 (`python3-pyqt5`). To use PyQt6 explicitly, run `pip install PyQt6`.

### 3. Camera Feed Shows "Waiting for video stream..."
- **Cause**: `dobot_v2/detection_node` is not publishing to `detected_objects_image/compressed`.
- **Solution**: Click **🔄 Reset Detection Node** on the toolbar to restart the detection process, or verify that the camera USB device `/dev/video*` is connected and accessible.

### 4. Direct Execution Error (`attempted relative import`)
- **Cause**: Running `python3 Dobot_UI/app.py` from outside the package directory.
- **Solution**: The entry point in `app.py` includes automatic path injection. Always run via `python3 -m Dobot_UI.app` or `ros2 run Dobot_UI dobot_ui`.

---

## License

This project is licensed under the **MIT License**.
Maintainer: Thanadech (Thanadech9834@hotmail.com)
