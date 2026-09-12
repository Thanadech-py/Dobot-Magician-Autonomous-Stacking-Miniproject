# dobot_project: Baseline Prototype Package for Dobot Magician

`dobot_project` contains the baseline prototype implementation of the Dobot Magician robotic control and color detection scripts.

> [!NOTE]
> For production use, please prefer:
> - **[`dobot_v2`](file:///home/thxncdzch/dobot_ws/src/dobot_v2)** for perspective-corrected vision tracking, homography calibration, and the modular hardware controller.
> - **[`Dobot_UI`](file:///home/thxncdzch/dobot_ws/src/Dobot_UI)** for the full PyQt mission dashboard, live video stream, and interactive manual jogging controls.

---

## Package Structure

```
src/dobot_project/
├── config/
│   ├── cube_detector.yaml        # Color thresholds and camera parameters
│   └── usb_cam.yaml              # USB camera V4L2 configuration
├── dobot_project/
│   ├── __init__.py
│   ├── dobot_controller.py       # Monolithic ROS 2 controller node for Dobot Magician
│   ├── cube_detector.py          # Standalone OpenCV multi-color cube detector
│   ├── Open_cam.py               # Standalone OpenCV webcam test script
│   └── dobot_ui.py               # Early prototype GUI script
├── launch/
│   ├── dobot_system.launch.py    # Prototype system launch file
│   └── dobot_vision.launch.py    # Prototype vision launch file
├── package.xml
└── setup.py
```

---

## Nodes & Scripts

### 1. `dobot_controller.py`
Monolithic ROS 2 node interfacing with the Dobot Magician via `pydobot2`:
- Subscribes to `/detected_objects` for cube coordinates.
- Subscribes to `/dobot_ui_cmd` for homing and mission triggers.
- Publishes `/dobot_status` telemetry.
- Direct hardware execution of pick-and-place trajectories.

### 2. `cube_detector.py`
OpenCV HSV segmentation script detecting colored cubes (Red, Yellow, Green, Blue) from USB webcam frames.

### 3. `Open_cam.py`
Direct camera verification utility to test `/dev/video0` or `/dev/video2` outside of ROS.

---

## Evolution & Differences with `dobot_v2`

| Feature | `dobot_project` (Prototype) | `dobot_v2` & `Dobot_UI` (Modern) |
| :--- | :--- | :--- |
| **Architecture** | Monolithic scripts | Decoupled modular subsystems |
| **Configuration** | Mixed inline / YAML | 100% separated into YAML configs |
| **Perspective Calibration** | Fixed pixel ratios | Homography with 4-corner auto-locking |
| **Manual Jogging** | Limited / absent | Full Cartesian $X, Y, Z, R$ jog & step selector |
| **UI Dashboard** | Prototype script | Production dark-theme PyQt UI with tabs & event log |
