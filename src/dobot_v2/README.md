# dobot_v2: Real-Time Field Grid Tracker & Cube Vision Node for Dobot

A high-performance, modular ROS 2 computer vision package for the **Dobot Magician** robotic arm. 

`dobot_v2` tracks a physical **3x3 pallet grid** on an A4 reference workspace, establishes a metric local coordinate frame using perspective homography, detects multi-colored cubes in real-time, and publishes high-precision pick coordinates in the Dobot Magician base frame.

---

## Table of Contents

- [System Overview](#system-overview)
- [Package Architecture](#package-architecture)
- [Coordinate Frames & Mathematics](#coordinate-frames--mathematics)
- [Key Features & Algorithms](#key-features--algorithms)
  - [1. 3x3 Pallet Detection & Green Circle Isolation](#1-3x3-pallet-detection--green-circle-isolation)
  - [2. Multi-Color Cube Detection & Geometric Filtering](#2-multi-color-cube-detection--geometric-filtering)
  - [3. Demand-Driven Rendering & CPU Optimization](#3-demand-driven-rendering--cpu-optimization)
- [Configuration Guide (`detection_node.yaml`)](#configuration-guide-detection_nodeyaml)
- [ROS 2 Interface](#ros-2-interface)
  - [Published Topics](#published-topics)
  - [Subscribed Topics](#subscribed-topics)
  - [JSON Detections Payload Specification](#json-detections-payload-specification)
- [Build & Run Instructions](#build--run-instructions)
- [Interactive Grid Calibration Tool](#interactive-grid-calibration-tool)
- [Troubleshooting & FAQ](#troubleshooting--faq)

---

## System Overview

The workspace template is an **A4 reference field** ($210\text{ mm} \times 297\text{ mm}$) featuring:
- **3x3 Pallet Grid** ($114.5\text{ mm} \times 114.5\text{ mm}$ outer frame, 9 cutouts of $25\text{ mm} \times 25\text{ mm}$ on a $35\text{ mm}$ pitch).
- **4 Feeder Slots** (Green circular slots on the left side of the pallet).
- **Dobot Base Origin** located at $(X=105.0\text{ mm}, Y=270.0\text{ mm})$ on the field.

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

`dobot_v2` automatically locates the 4 outer corners of the pallet, calculates the perspective homography, monitors tracking stability, and locks the local frame. When colored cubes (Red, Yellow, Green, Blue) are placed in the cells or feeder slots, the node outputs their 3D coordinates in robot base millimeters $(X, Y, Z)$ for pick-and-place stacking operations.

---

## Package Architecture

The node is designed according to the **Single Responsibility Principle**. Each component is isolated into a dedicated Python module:

```
src/dobot_v2/
├── config/
│   ├── detection_node.yaml       # All parameters: geometry, HSV ranges, thresholds
│   ├── usb_cam.yaml              # V4L2 camera driver configuration
│   ├── C270_Calibration.yaml    # Logitech C270 camera matrix & distortion coefficients
│   └── Test_cam_calibration.yaml# Generic camera calibration profile
├── dobot_v2/
│   ├── detection_node.py         # Lean ROS 2 node orchestrator (< 290 lines)
│   ├── transforms.py             # Homography, metric conversions, and cell indexing
│   ├── grid_detector.py          # Pallet contouring, green exclusion, and auto-locking
│   ├── cube_detector.py          # Color segmentation and geometric cube validation
│   ├── visualizer.py             # Debug HUD, bounding boxes, and grid overlay drawing
│   └── calibrate_grid.py         # Standalone GUI tool for interactive manual alignment
├── launch/
│   └── dobot_vision.launch.py    # Combined camera streaming + detection launcher
├── package.xml
├── setup.py
└── README.md
```

---

## Coordinate Frames & Mathematics

Four coordinate frames are managed seamlessly:

```
Camera Pixels (u, v)
        │  Perspective Homography H (cv2.getPerspectiveTransform)
        ▼
Grid Local Frame (gx, gy) [mm, Origin at Pallet Top-Left]
        │  Field Translation (+48 mm X, +37 mm Y)
        ▼
Field Sheet Frame (fx, fy) [mm, Origin at A4 Top-Left]
        │  Robot Base Transformation
        ▼
Dobot Base Frame (rx, ry, rz) [mm, Origin at Dobot Center Base]
```

### Transformation Equations:

1. **Grid Local to Field Sheet ($mm$):**
   $$f_x = \text{grid\_tl\_field\_x} + g_x = 48.0 + g_x$$
   $$f_y = \text{grid\_tl\_field\_y} + g_y = 37.0 + g_y$$

2. **Field Sheet to Dobot Magician Base ($mm$):**
   $$r_x = \text{robot\_base\_y} - f_y = 270.0 - f_y$$
   $$r_y = \text{robot\_base\_x} - f_x = 105.0 - f_x$$
   $$r_z = \text{cube\_height} = 12.5\text{ mm (center of 25mm cube)}$$

3. **Symmetric 3x3 Cell Indexing:**
   The pallet grid center is at $(\frac{\text{grid\_size}}{2}, \frac{\text{grid\_size}}{2})$. The cell pitch is $35.0\text{ mm}$.
   - Center cell $(1, 1)$ is marked as `GOAL`.
   - Offsets $dx, dy$ relative to each cell's nominal center are computed to allow fine pick offsets.

---

## Key Features & Algorithms

### 1. 3x3 Pallet Detection & Green Circle Isolation

The physical gap between the Dobot reach arc / Feeder Slot #4 and the grey pallet frame is only **$6.3\text{ mm}$ (~12 pixels)**. Standard thresholding or large morphological kernels bridge this gap, causing the grid to incorrectly swallow the feeder circles.

`dobot_v2` resolves this through a **5-layer isolation pipeline**:
1. **Green Feeder Mask Subtraction**: HSV green feeder pixels ($H \in [35, 85]$, $S \ge 50$) are extracted, dilated with a $9\times 9$ elliptical kernel, and bitwise-subtracted from both the grey pallet mask and edge threshold images.
2. **Kernel Size Limitation**: Morphological close uses a small $3\times 3$ kernel ($1\text{ iteration} \le 3\text{ px}$), preventing bridge formation across the $12\text{ px}$ gap.
3. **Aspect Ratio Gate ($\text{aspect} \le 1.22$)**: A square pallet has an aspect ratio $\approx 1.00$. Contours merging with feeder circles have aspect $\approx 1.35$ and are instantly rejected.
4. **Squareness Scoring Function**: Candidates are ranked by:
   $$\text{Score} = \text{Area} \times (1.0 - 2.0 \cdot |\text{aspect} - 1.0|)$$
5. **Pattern Contrast Verification**: Perspective-warps candidate quads to a normalized $150\times 150$ patch. Candidates are rejected if the leftmost 25% contains green pixels ($> 8\%$) or if cell cutout contrast against dividers is $< 12.0$.

### 2. Multi-Color Cube Detection & Geometric Filtering

Cubes are segmented in HSV space for **Red** (dual range wrap-around), **Yellow**, **Green**, and **Blue**.
- **Geometry Checks**: Rejects noise via minimum area, maximum area, aspect ratio ($\le 2.2$), convexity solidity ($\ge 0.78$), and extent ($\ge 0.65$).
- **Circularity Filter**: Green paper markings and circles on the template have high circularity ($> 0.84$) and low extent ($< 0.82$). These are filtered out, ensuring only actual 3D cubes are recognized.
- **Workspace Bounds**: Detections are clipped strictly to the active workspace ($X \in [-35, 130]$, $Y \in [-2, 155]\text{ mm}$).

### 3. Demand-Driven Rendering & CPU Optimization

- **Zero Idle Drawing Overhead**: The node checks `pub.get_subscription_count()`. If no GUI (`Dobot_UI`) or RViz client is subscribed to the image topic, all OpenCV overlay drawing and JPEG compression are bypassed, saving **$50\%\text{--}70\%$ CPU**.
- **Instant Locked Bypass**: Once the pallet frame reaches the stability threshold (10 consecutive steady frames), contour search is disabled and cached homography is reused with 0 CV overhead.
- **Frame Rate Limiter**: Drops excess incoming camera frames above `publish_rate` (default 30 Hz).
- **Best-Effort QoS**: Uses `ReliabilityPolicy.BEST_EFFORT` with `depth=1` to drop delayed frames, ensuring low-latency tracking.

---

## Configuration Guide (`detection_node.yaml`)

All parameters are stored in [`src/dobot_v2/config/detection_node.yaml`](file:///home/thxncdzch/dobot_ws/src/dobot_v2/config/detection_node.yaml). The node loads defaults directly from YAML with zero hardcoded parameters in Python.

| Section | Parameter | Default | Description |
| :--- | :--- | :--- | :--- |
| **Streaming** | `image_topic` | `/image_raw/compressed` | Input camera topic |
| | `publish_rate` | `30.0` | Maximum processing rate in Hz |
| | `show_overlay` | `true` | Enable/disable visual debug rendering |
| | `publish_raw_image` | `true` | Publish uncompressed image |
| **Geometry** | `grid_size_mm` | `114.5` | Outer square pallet width & height |
| | `cell_pitch_mm` | `35.0` | Center-to-center cell spacing |
| | `grid_tl_field_x_mm` | `48.0` | Grid Top-Left X on A4 sheet |
| | `grid_tl_field_y_mm` | `37.0` | Grid Top-Left Y on A4 sheet |
| | `robot_base_x_mm` | `105.0` | Dobot Base center X on A4 sheet |
| | `robot_base_y_mm` | `270.0` | Dobot Base center Y on A4 sheet |
| | `cube_height_mm` | `12.5` | Cube center pick height Z |
| **Tracking** | `auto_detect_grid` | `true` | Automatically track pallet grid |
| | `lock_grid_after_detect` | `true` | Lock grid when steady frames reached |
| | `lock_stable_frame_count` | `10` | Consecutive steady frames to lock |
| | `grid_max_aspect_ratio` | `1.22` | Strict square ratio limit |
| | `grid_corners` | `[0.0, ...]` | 8 floats for manual corners (`[0,...]` for auto) |
| **Cubes** | `min_cube_area` | `250` | Minimum cube contour pixels |
| | `max_cube_area` | `30000` | Maximum cube contour pixels |
| | `min_cube_solidity` | `0.78` | Minimum contour area / hull area |
| | `green_circle_max_circularity` | `0.84` | Rejection threshold for printed circles |

---

## ROS 2 Interface

### Published Topics

| Topic | Type | Description |
| :--- | :--- | :--- |
| `/detected_objects` | `std_msgs/String` | Structured JSON containing objects, coordinates, and color counts |
| `/detected_objects_poses` | `geometry_msgs/PoseArray` | Detected cube positions in **Dobot Base Frame** (`dobot_base`) in mm |
| `/grid_local_poses` | `geometry_msgs/PoseArray` | Detected cube positions in **Grid Frame** (`grid_frame`) in mm |
| `/detected_objects_image/compressed`| `sensor_msgs/CompressedImage` | JPEG-compressed stream with HUD, cell boxes, and bounding tags |
| `/detected_objects_image` | `sensor_msgs/Image` | Uncompressed BGR8 debug image stream |

### Subscribed Topics

| Topic | Type | Description |
| :--- | :--- | :--- |
| `/image_raw/compressed` | `sensor_msgs/CompressedImage` | Raw camera stream |
| `/camera_info` | `sensor_msgs/CameraInfo` | Camera intrinsics and distortion model |
| `/reset_grid` | `std_msgs/String` | Resets locked grid state and resumes auto-search |
| `/lock_grid` | `std_msgs/String` | Manually locks current grid corners |
| `/unlock_grid` | `std_msgs/String` | Unlocks grid tracking |
| `/set_grid_corners` | `std_msgs/String` | Sets 4 corners via JSON array: `[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]` |

### JSON Detections Payload Specification

Published on `/detected_objects`:

```json
{
  "timestamp": 1789153474.73,
  "grid_locked": true,
  "counts": { "red": 1, "yellow": 0, "green": 1, "blue": 0 },
  "total_objects": 2,
  "objects": [
    {
      "color": "red",
      "bgr_color": [0, 0, 255],
      "pixel": { "u": 412, "v": 305 },
      "grid_local_mm": { "x": 57.2, "y": 57.2 },
      "in_grid": true,
      "cell": {
        "row": 1,
        "col": 1,
        "name": "GOAL",
        "is_goal": true,
        "cell_center_mm": { "x": 57.2, "y": 57.2 },
        "offset_mm": { "dx": 0.0, "dy": 0.0 }
      },
      "grid_cell": { "row": 1, "col": 1, "name": "GOAL" },
      "feeder_id": null,
      "field_mm": { "x": 105.2, "y": 94.2 },
      "robot_mm": { "x": 175.8, "y": -0.2, "z": 12.5 },
      "angle_deg": -14.2,
      "size_px": [42, 44],
      "rect_points": [[390.1, 280.4], [432.5, 275.1], [438.0, 318.2], [395.6, 323.5]],
      "area": 1820
    }
  ]
}
```

---

## Build & Run Instructions

### 1. Build the Package
```bash
cd ~/dobot_ws
colcon build --packages-select dobot_v2 --symlink-install
source install/setup.bash
```

### 2. Launch Camera & Detection Node
```bash
ros2 launch dobot_v2 dobot_vision.launch.py
```

*Optional Launch Arguments:*
```bash
# Switch video device (e.g. /dev/video2 for integrated laptop webcam)
ros2 launch dobot_v2 dobot_vision.launch.py video_device:=/dev/video2

# Specify custom parameters file
ros2 launch dobot_v2 dobot_vision.launch.py detection_params_file:=/path/to/custom.yaml
```

### 3. Launch with GUI
In a separate terminal, launch the mission interface:
```bash
ros2 launch Dobot_UI dobot_ui.launch.py
```

---

## Interactive Grid Calibration Tool

If camera lighting or optical distortion makes automatic detection difficult, you can click the 4 corners manually using the built-in calibration tool:

```bash
ros2 run dobot_v2 calibrate_grid
```

1. Click the 4 corners of the outer grey pallet in clockwise order:
   - **Click 1**: Top-Left
   - **Click 2**: Top-Right
   - **Click 3**: Bottom-Right
   - **Click 4**: Bottom-Left
2. A green 3x3 grid preview and coordinate axes will appear instantly.
3. Press **`s`** to save the coordinates directly into [`config/detection_node.yaml`](file:///home/thxncdzch/dobot_ws/src/dobot_v2/config/detection_node.yaml) and publish them to the active detection node.
4. Press **`r`** to reset points, or **`q`** to quit.

---

## Troubleshooting & FAQ

### 1. `usb_cam process has died [exit code -11]` or `Device or resource busy (EBUSY)`
- **Cause**: An orphaned background process is holding `/dev/video0` exclusively, or `usb_cam` encountered a V4L2 segfault upon unclean termination.
- **Solution**:
  ```bash
  # Check if video device is held
  fuser /dev/video*

  # Terminate any hung camera processes
  killall -9 usb_cam_node_exe
  ```
  *Note: `dobot_vision.launch.py` has `respawn=True` enabled to automatically recover from momentary glitches.*

### 2. Contoured grid includes the green feeder circles
- Ensure `grid_max_aspect_ratio` in `detection_node.yaml` is set to $\le 1.22$. A square grid has aspect $\approx 1.0$, while a merged feeder shape has $\approx 1.35$.
- Check that green feeder slot subtraction is active in `grid_detector.py`.

### 3. Cubes not detected or wrong color assigned
- Open `rqt_image_view` or `Dobot_UI` to inspect the lighting.
- Tune the HSV bounds in `config/detection_node.yaml` under `color_red_1`, `color_red_2`, `color_yellow`, `color_green`, and `color_blue`.
- If small noise is detected, increase `min_cube_area` (default: 250 px).
