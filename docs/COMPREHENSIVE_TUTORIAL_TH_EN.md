# Dobot Magician Vision Stacking & Control System: Comprehensive Beginner-to-Advanced Guide
# คู่มือการพัฒนาระบบควบคุมแขนกล Dobot Magician ด้วย ROS 2, OpenCV, PyQt และ pydobot2 ฉบับสมบูรณ์ (เริ่มต้นจากศูนย์)

---

## 📖 สารบัญ / Table of Contents

1. [ภาพรวมระบบและสถาปัตยกรรม / System Overview & Architecture](#1-system-overview--architecture)
2. [ปูพื้นฐาน ROS 2 จากศูนย์ / ROS 2 Fundamentals from Scratch](#2-ros-2-fundamentals-from-scratch)
   - 2.1 ROS 2 คืออะไร? / What is ROS 2?
   - 2.2 โหนดและการสื่อสาร (Nodes, Topics, Services, Actions)
   - 2.3 โครงสร้าง Workspace และ Packages (`ament_python`)
   - 2.4 การทำงานของ Launch Files และ Config YAML
3. [ระบบคอมพิวเตอร์วิทัศน์ด้วย OpenCV / Computer Vision with OpenCV](#3-computer-vision-with-opencv)
   - 3.1 การจับภาพจากกล้อง (V4L2 Video Streaming)
   - 3.2 สี BGR vs HSV และทำไมต้องใช้ HSV ในการตรวจจับวัตถุ
   - 3.3 การแยกสี (Color Masking) และการกรองสัญญาณรบกวน (Morphology)
   - 3.4 การหาขอบเขตวัตถุ (Contours & Bounding Boxes)
   - 3.5 การแปลงพิกัดภาพเป็นพิกัดจริงด้วย Perspective Homography
4. [การควบคุมแขนกล Dobot Magician ด้วย `pydobot2` / Robot Control with `pydobot2`](#4-robot-control-with-pydobot2)
   - 4.1 การสื่อสารแบบอนุกรม (Serial UART Communication)
   - 4.2 ระบบพิกัด Cartesian ($X, Y, Z, R$) vs พิกัดข้อต่อ (Joint Angles)
   - 4.3 โหมดการเคลื่อนที่แบบ PTP (`MOVJ` vs `MOVL`)
   - 4.4 การควบคุมเครื่องมือปลายแขน (Suction Cup & Gripper)
   - 4.5 การจัดการ Thread-Safety และสิทธิ์พอร์ต USB บน Linux
5. [การพัฒนาหน้าต่างส่วนติดต่อผู้ใช้ด้วย PyQt / GUI Development with PyQt](#5-gui-development-with-pyqt)
   - 5.1 พื้นฐานสถาปัตยกรรม PyQt (Event Loop, Widgets, Layouts, QSS)
   - 5.2 กลไก Signals & Slots สำหรับการเขียนโปรแกรมแบบ Asynchronous
   - 5.3 การเชื่อมโยง ROS 2 กับ PyQt ด้วย `QThread` ป้องกันโปรแกรมค้าง (GUI Freezing)
   - 5.4 การแปลงภาพ OpenCV Mat สู่ Qt `QImage` & `QPixmap`
6. [ตรรกะภารกิจและการหลบหลีกสิ่งกีดขวาง / 3-Phase Mission Logic & Collision Avoidance](#6-3-phase-mission-logic--collision-avoidance)
   - 6.1 ตรรกะ 3 เฟส: ย้ายสิ่งกีดขวาง ➔ วางซ้อน 4 ก้อน ➔ นำสิ่งกีดขวางกลับที่เดิม
   - 6.2 การป้องกันการชนเสา Goal (Horizontal Keepout & Detour Waypoints)
   - 6.3 ระยะยกสูงปลอดภัย (Vertical Clearance Trajectory)
7. [คู่มือการใช้งานหน้าจอ GUI / UI Interface Walkthrough with Screenshots](#7-ui-interface-walkthrough)
   - 7.1 หน้าจอภารกิจ (Stacking Mission Tab)
   - 7.2 หน้าจอควบคุมด้วยตนเอง (Manual Control Tab)
   - 7.3 หน้าจอบันทึกพิกัดตำแหน่ง (Teach Positions Tab)
8. [คู่มือการติดตั้ง ใช้งาน และแก้ไขปัญหา / Build, Run & Troubleshooting](#8-build-run--troubleshooting)

---

## 1. ภาพรวมระบบและสถาปัตยกรรม / System Overview & Architecture

### ภาษาไทย (TH)
โปรเจกต์นี้เป็นระบบอัตโนมัติอัจฉริยะที่ผสมผสาน **หุ่นยนต์แขนกล (Dobot Magician)**, **ระบบกล้องตรวจจับภาพสี (OpenCV Computer Vision)**, **ระบบสื่อสารหุ่นยนต์แบบกระจายศูนย์ (ROS 2 Humble)** และ **หน้าต่างควบคุมกราฟิก (PyQt GUI)** เข้าไว้ด้วยกัน

**ลักษณะสนามการทำงาน (Field Layout):**
- พื้นที่ทำงานอยู่บนแผ่นมาตรฐาน A4 ($210 \times 297\text{ mm}$)
- ฐานแขนกล Dobot Magician ติดตั้งอยู่ที่พิกัด $(X=105.0\text{ mm}, Y=270.0\text{ mm})$
- มีถาดตาราง $3 \times 3$ (Pallet Grid ขนาด $114.5 \times 114.5\text{ mm}$, ระยะพิตช์ $35\text{ mm}$)
  - ช่องรอบนอก 8 ช่อง: เป็นตำแหน่งวางบล็อกสีต่าง ๆ (แดง, เหลือง, เขียว, ฟ้า, ส้ม, ม่วง, ฟ้าคราม)
  - ช่องกึ่งกลาง `[1, 1]`: เป็นเป้าหมาย **STACK GOAL** สำหรับวางบล็อกซ้อนกันในแนวตั้ง (จำกัดล็อกไว้สูงสุด 4 ก้อน)
- ทางด้านซ้ายของตาราง มี **ช่อง Feeder 4 ตำแหน่ง** (Feeder 1 ถึง Feeder 4):
  - ใช้เป็นสถานีพักชั่วคราวสำหรับบล็อกที่เป็น "สิ่งกีดขวาง" (Obstacles)

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

### English (EN)
This project integrates an industrial-educational robot arm (**Dobot Magician**), a real-time vision system (**OpenCV**), a modular robotics middleware (**ROS 2 Humble**), and an intuitive control dashboard (**PyQt GUI**).

**Key Mission Objectives:**
1. **Perception**: Detect colored cubes inside the $3 \times 3$ grid and feeder slots, estimating real-world Cartesian metric coordinates $(X, Y, Z)$ in millimeters.
2. **Obstacle Clearance**: Identify non-goal obstacle cubes and transport them out of the pallet grid into 4 dedicated feeder slots.
3. **Goal Stacking**: Pick target cubes in operator-defined order and stack them vertically at Center Goal `[1, 1]` (strictly locked to a maximum of 4 blocks).
4. **Collision Avoidance**: Safely route all arm movements around the perimeter corridors to prevent knocking over the growing goal stack.
5. **Obstacle Restoration**: Return the obstacle cubes from the feeders back to their original grid slots once stacking completes.

---

## 2. ปูพื้นฐาน ROS 2 จากศูนย์ / ROS 2 Fundamentals from Scratch

### 2.1 ROS 2 คืออะไร? / What is ROS 2?
- **ROS 2 (Robot Operating System 2)** ไม่ใช่ระบบปฏิบัติการจริงเหมือน Windows หรือ Linux แต่เป็น **Software Framework & Middleware** ที่ช่วยจัดการการสื่อสารระหว่างโปรแกรมย่อย ๆ ให้ทำงานร่วมกันได้อย่างมีระเบียบ มีเสถียรภาพ และรองรับระบบ Real-time
- ในระบบนี้ มี 2 แพ็กเกจหลัก:
  1. `dobot_v2`: จัดการระบบกล้องตรวจจับภาพ (Vision) และคำนวณการเคลื่อนที่ของแขนกล (Controller)
  2. `Dobot_UI`: หน้าจอแดชบอร์ดแสดงผลกล้อง ภาพตรวจจับ ข้อมูลสถานะ และสั่งการหุ่นยนต์

### 2.2 โหนดและการสื่อสาร / Nodes, Topics, Services, Actions

#### 1. Node (โหนด)
- เปรียบเสมือน **"โปรแกรมย่อยหนึ่งโปรแกรมที่มีหน้าที่เฉพาะทาง"** ตัวอย่างในโปรเจกต์นี้:
  - `detection_node`: ทำหน้าที่เปิดกล้อง ดึงภาพ หาตำแหน่งก้อนสี แล้วส่งผลลัพธ์ออกมา
  - `dobot_controller`: ทำหน้าที่เชื่อมต่อกับ Dobot Magician รับคำสั่ง และสั่งมอเตอร์หมุน
  - `dobot_ui_node`: ทำหน้าที่วาดหน้าต่าง GUI ให้ผู้ใช้กดสั่งงาน

#### 2. Topic (หัวข้อการรับ-ส่งข้อมูล)
- เป็นการสื่อสารแบบ **Publish / Subscribe (ผู้ส่ง - ผู้รับ)** ข้อมูลจะไหลทางเดียวอย่างต่อเนื่อง:
  - **Publisher (ผู้ส่ง)**: ส่งข้อความ (Message) ออกมายัง Topic โดยไม่สนใจว่าใครจะอ่าน
  - **Subscriber (ผู้รับ)**: ดักฟังสัญญาณจาก Topic เมื่อมีข้อมูลใหม่เข้ามา ฟังก์ชัน Callback จะทำงานทันที

**ตาราง Topic หลักในโปรเจกต์นี้:**
| Topic Name | Message Type | ผู้ส่ง (Publisher) | ผู้รับ (Subscriber) | คำอธิบาย |
|:---|:---|:---|:---|:---|
| `/detected_objects` | `std_msgs/msg/String` (JSON) | `detection_node` | `Dobot_UI`, `dobot_controller` | รายการพิกัดและสีของบล็อกที่ตรวจจับได้ |
| `/detected_objects_image/compressed` | `sensor_msgs/msg/CompressedImage` | `detection_node` | `Dobot_UI` | สตรีมภาพวิดีโอจากกล้องแบบเรียลไทม์ |
| `/dobot_status` | `std_msgs/msg/String` (JSON) | `dobot_controller` | `Dobot_UI` | สถานะแขนกล พิกัดปัจจุบัน $(X,Y,Z,R)$ และสถานะลมดูด |
| `/dobot_ui_cmd` | `std_msgs/msg/String` (JSON) | `Dobot_UI` | `dobot_controller` | คำสั่งเริ่มภารกิจ, จ๊อกกิ้งมือ, โฮมมิ่ง, หยุดฉุกเฉิน |

```
┌───────────────────┐     /detected_objects_image/compressed     ┌──────────────┐
│  detection_node   ├───────────────────────────────────────────►│              │
│   (OpenCV Node)   ├─────────────┐ /detected_objects (JSON)     │   Dobot_UI   │
└───────────────────┘             ▼                              │  (PyQt GUI)  │
                          ┌───────────────┐  /dobot_status       │              │
                          │dobot_controller├────────────────────►│              │
                          │ (pydobot2)    │◄─────────────────────┤              │
                          └───────┬───────┘   /dobot_ui_cmd      └──────────────┘
                                  │ Serial USB
                                  ▼
                         [Dobot Magician Arm]
```

### 2.3 โครงสร้าง Workspace และ Packages
- **Workspace (`dobot_ws`)**: โฟลเดอร์รากที่รวมซอร์สโค้ดและไฟล์บิลด์ทั้งหมด
  - `src/`: ที่เก็บโฟลเดอร์ซอร์สโค้ดของแต่ละแพ็กเกจ
  - `install/`: โฟลเดอร์ผลลัพธ์หลังจากคอมไพล์ด้วยคำสั่ง `colcon build`
  - `build/` & `log/`: ไฟล์ชั่วคราวและบันทึกข้อความระหว่างการบิลด์

---

## 3. ระบบคอมพิวเตอร์วิทัศน์ด้วย OpenCV / Computer Vision with OpenCV

### 3.1 การจับภาพจากกล้อง (V4L2 Video Streaming)
ในไฟล์ [`Open_cam.py`](file:///home/thxncdzch/dobot_ws/src/dobot_project/dobot_project/Open_cam.py) และ [`detection_node.py`](file:///home/thxncdzch/dobot_ws/src/dobot_v2/dobot_v2/detection_node.py) ใช้ OpenCV ในการติดต่อกล้องผ่านไดรเวอร์ Video4Linux2 (`cv2.CAP_V4L2`) เพื่อลดความหน่วง (Latency):

```python
cap = cv2.VideoCapture(video_device, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)
```

### 3.2 ทำไมต้องใช้พื้นที่สี HSV แทน RGB/BGR?
- กล้องทั่วไปส่งภาพออกมาเป็น **BGR (Blue, Green, Red)** ซึ่งค่าสีทั้ง 3 ตัวแปรจะเปลี่ยนไปตามความเข้มแสงเงา (ถ้าห้องมืดลง ค่า R, G, B จะเปลี่ยนทั้งหมด ทำให้ตรวจจับสียากมาก)
- **HSV (Hue, Saturation, Value)**:
  - **H (Hue - เนื้อสี)**: ระบุชนิดของสี เช่น แดง, เหลือง, เขียว โดยไม่ขึ้นกับความสว่าง (ช่วง 0-180 ใน OpenCV)
  - **S (Saturation - ความสดของสี)**: ความอิ่มตัวของสี (0 = ขาว/เทา, 255 = สีสดจัด)
  - **V (Value - ความสว่าง)**: ความสว่างของแสง (0 = มืดสนิท, 255 = สว่างจ้า)
- การใช้ HSV ช่วยให้ระบบสามารถตรวจจับสีของบล็อกได้แม่นยำแม้แสงในห้องจะเปลี่ยนไป!

```python
# แปลงภาพจาก BGR เป็น HSV
hsv_image = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2HSV)
```

### 3.3 การแยกสี (Color Masking) และ Morphology
1. **`cv2.inRange()`**: กรองพิกเซลที่อยู่ในช่วง HSV ที่กำหนด ให้ค่าเป็น 255 (สีขาว) และส่วนอื่นเป็น 0 (สีดำ)
2. **Morphological Operations**: ลบจุดรบกวน (Noise) และเชื่อมรูพรุนในก้อนวัตถุ
   - **Erode (การกัดกร่อน)**: ตัดจุดขาวเล็ก ๆ ที่เป็นสัญญาณรบกวนออกไป
   - **Dilate (การขยาย)**: ขยายขอบเขตของเนื้อสีให้กลับมาเต็มก้อนเหมือนเดิม

```python
# ตัวอย่างการมาสก์สีเขียว
lower_green = np.array([35, 80, 70])
upper_green = np.array([85, 255, 255])
mask = cv2.inRange(hsv_image, lower_green, upper_green)

# ลบ Noise ด้วยการเปิดและปิด (Morphological Opening & Closing)
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
```

### 3.4 การหาเส้นขอบวัตถุ (Contours) และ Bounding Boxes
ฟังก์ชัน `cv2.findContours()` จะหาเส้นขอบรอบพื้นที่สีขาว จากนั้นคัดกรองตามขนาดพื้นที่ (`cv2.contourArea`):

```python
contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
for cnt in contours:
    area = cv2.contourArea(cnt)
    if min_area <= area <= max_area:
        rect = cv2.minAreaRect(cnt)  # ((cx, cy), (w, h), angle)
        box = cv2.boxPoints(rect)     # 4 มุมของสี่เหลี่ยมบล็อก
```

### 3.5 การแปลงพิกัดภาพเป็นพิกัดจริงด้วย Perspective Homography
เนื่องจากกล้องติดตั้งมุมเอียง (ไม่ได้อยู่ระนาบดิ่ง $90^\circ$ เป๊ะ ๆ) ภาพจึงเกิดการบิดเบี้ยวรูปสี่เหลี่ยมคางหมู:
1. หาจุดมุม 4 มุมของถาดตาราง $3 \times 3$ บนภาพพิกเซล
2. กำหนดพิกัดจริงเป้าหมายของถาดขนาด $114.5 \times 114.5\text{ mm}$
3. คำนวณเมทริกซ์โฮโมกราฟีด้วย `cv2.getPerspectiveTransform()`
4. แปลงพิกัดพิกเซล $(u, v)$ ใด ๆ ให้กลายเป็นพิกัดมิลลิเมตรบนถาด $(gx, gy)$ และแปลงต่อเป็นพิกัดของหุ่นยนต์ $(rx, ry)$ ทันที!

---

## 4. การควบคุมแขนกล Dobot Magician ด้วย `pydobot2` / Robot Control with `pydobot2`

### 4.1 การสื่อสารแบบอนุกรม (Serial UART Communication)
- แขนกล Dobot Magician สื่อสารผ่านพอร์ต USB-to-Serial (ชิป CP210x หรือ CH340) ด้วยความเร็ว Baudrate **115200 bps**
- ไลบรารี [`pydobot2`](https://github.com/luismesas/pydobot) จะแปลงฟังก์ชันไพธอนเป็นแพ็กเก็ตข้อมูลไบนารีตามโปรโตคอลทางการของ Dobot (มี Header `0xAA 0xAA`, Payload ความยาว, รหัสคำสั่ง, และ Checksum)

### 4.2 ระบบพิกัดของ Dobot Magician
1. **Cartesian Coordinates ($X, Y, Z, R$)**:
   - $X$ (mm): แกนหน้า-หลัง (ยื่นแขนไปข้างหน้า = ค่าบวก, ดึงเข้าหาตัว = ค่าลบ)
   - $Y$ (mm): แกนซ้าย-ขวา (หมุนไปทางซ้าย = ค่าบวก, หมุนไปทางขวา = ค่าลบ)
   - $Z$ (mm): แกนความสูง (ยกแขนขึ้น = ค่าบวก, ลดแขนลงต่ำติดโต๊ะ = ค่าลบ)
   - $R$ (องศา): มุมหมุนของเซอร์โวเครื่องมือปลายแขน (End-effector angle)
2. **Joint Coordinates ($J_1, J_2, J_3, J_4$)**:
   - มุมหมุนของมอเตอร์สเต็ปเปอร์แต่ละข้อต่อ 4 แกน

### 4.3 โหมดการเคลื่อนที่แบบ PTP (Point-To-Point)
- **`MOVJ_XYZ` (Joint Movement)**: มอเตอร์ทุกข้อต่อหมุนพร้อมกัน แขนจะเหวี่ยงเป็นเส้นโค้งอิสระ เคลื่อนที่ได้เร็ว เหมาะสำหรับการเคลื่อนที่ในที่โล่ง (Transit)
- **`MOVL_XYZ` (Linear Movement)**: หัวแขนกลจะเคลื่อนที่เป็น **เส้นตรงแนวราบหรือแนวดิ่งเป๊ะ ๆ** เหมาะสำหรับตอนหยิบบล็อก (ลงตรง ๆ) และตอนวางบล็อกซ้อน (ขึ้นตรง ๆ) เพื่อไม่ให้ชนบล็อกข้างเคียง

```python
from pydobot import Dobot
from pydobot.dobot import MODE_PTP

# เชื่อมต่อหุ่นยนต์
device = Dobot(port='/dev/ttyUSB0')

# ตั้งค่าความเร็วและความเร่ง
device.speed(velocity=150.0, acceleration=150.0)

# เคลื่อนที่แบบเชิงเส้น (Linear descent)
device.move_to(x=200.0, y=0.0, z=12.5, r=0.0, mode=MODE_PTP.MOVL_XYZ)

# เปิดปั๊มลมดูดบล็อก
device.suck(True)
```

### 4.4 การจัดการสิทธิ์พอร์ต USB บน Linux
บนระบบปฏิบัติการ Linux (Ubuntu / Pop!_OS) พอร์ต `/dev/ttyUSB0` ถูกจำกัดสิทธิ์ไว้เฉพาะกลุ่ม `dialout`:
```bash
# เพิ่มผู้ใช้ปัจจุบันเข้ากลุ่ม dialout
sudo usermod -a -G dialout $USER

# กำหนดสิทธิ์ให้อ่านเขียนพอร์ตได้โดยตรง
sudo chmod 666 /dev/ttyUSB0
```

---

## 5. การพัฒนาหน้าต่างส่วนติดต่อผู้ใช้ด้วย PyQt / GUI Development with PyQt

### 5.1 พื้นฐานสถาปัตยกรรม PyQt (PyQt6 / PyQt5)
- **Event Loop**: หัวใจการทำงานของโปรแกรม GUI ที่คอยดักจับเหตุการณ์ (คลิกเมาส์, ข้อมูลมาใหม่, นาฬิกาจับเวลา)
- **Widgets**: ชิ้นส่วนกราฟิก เช่น `QPushButton` (ปุ่มกด), `QLabel` (ข้อความ/รูปภาพ), `QComboBox` (เมนูดร็อปดาวน์), `QTableWidget` (ตาราง)
- **Layouts**: ตัวจัดตำแหน่งอัตโนมัติ เช่น `QVBoxLayout` (แนวตั้ง), `QHBoxLayout` (แนวนอน), `QGridLayout` (ตารางกริด)
- **QSS (Qt Style Sheets)**: กำหนดสีและธีมแบบโมเดิร์น Dark Theme (สีน้ำเงิน Navy `#0f172a`, ข้อความสีฟ้า `#38bdf8`)

### 5.2 กลไก Signals & Slots
เป็นการเชื่อมเหตุการณ์จาก Widget สู่ฟังก์ชันประมวลผล:
```python
self.btn_start.clicked.connect(self._start_mission)
```

### 5.3 ปัญหา GUI ค้าง (Freezing) และการแก้ปัญหาด้วย `QThread`
- **ปัญหา**: หากเราสั่งให้ ROS 2 วนลูปฟังข้อมูล (`rclpy.spin()`) หรือสั่งให้ Dobot ทำงานที่กินเวลาหลายวินาทีใน Thread หลักของ GUI หน้าต่างโปรแกรมจะค้าง ไม่ตอบสนอง และกลายเป็นสีเทา (Not Responding)
- **วิธีแก้ปัญหา**: แยกการทำงานออกเป็น **2 Threads**:
  1. **Main Thread (UI Thread)**: ทำหน้าที่วาดหน้าต่าง รับคลิกผู้ใช้ และอัปเดตภาพ
  2. **Worker Thread (`RosBridge(QThread)`)**: วิ่งอยู่เบื้องหลังเพื่อดักฟังสัญญาณ ROS 2 เมื่อได้ข้อมูลภาพหรือสถานะใหม่ จะส่งผ่าน `pyqtSignal` มาสะกิดให้ Main Thread วาดภาพใหม่ทันที โดยไม่มีการค้างเกิดขึ้นแม้แต่มิลลิวินาทีเดียว!

```python
class RosBridge(QThread):
    image_received = pyqtSignal(QImage, float)
    status_received = pyqtSignal(dict)

    def run(self):
        while self._running:
            rclpy.spin_once(self.node, timeout_sec=0.01)
```

### 5.4 การแปลงภาพจาก OpenCV สู่ Qt QImage
OpenCV เก็บภาพเป็น NumPy Array (สี BGR) แต่ Qt แสดงภาพด้วย `QImage` (สี RGB):
```python
# แปลง BGR เป็น RGB
rgb_image = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
h, w, ch = rgb_image.shape
bytes_per_line = ch * w

# สร้าง QImage จากหน่วยความจำของ NumPy
qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

# แสดงผลบน QLabel ผ่าน QPixmap
self.lbl_camera.setPixmap(QPixmap.fromImage(qt_image))
```

---

## 6. ตรรกะภารกิจและการหลบหลีกสิ่งกีดขวาง / 3-Phase Mission Logic & Collision Avoidance

### 6.1 ตรรกะภารกิจ 3 เฟส (3-Phase Workflow)
ระบบถูกออกแบบตามสถาปัตยกรรมโรงงานอัตโนมัติ เพื่อรองรับสถานการณ์ที่มีสิ่งกีดขวางขวางทาง:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       3-PHASE AUTONOMOUS MISSION                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. PHASE 1: CLEAR OBSTACLES                                                 │
│    - ตรวจพบสิ่งกีดขวาง (Obstacles) ในช่องที่ไม่ได้ถูกเลือกเป็น Goal         │
│    - ดูดย้ายก้อนสิ่งกีดขวางไปพักไว้ที่ Feeder 1..4 (ฝั่งซ้ายของตาราง)        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. PHASE 2: STACK GOAL BLOCKS                                               │
│    - หยิบบล็อกเป้าหมายที่เลือกไว้ตามลำดับ (#1, #2, #3, #4)                  │
│    - วางซ้อนบน Center Goal [1, 1] แนวตั้ง (ล็อกไว้ไม่เกิน 4 ชั้น)           │
│    - ระดับความสูงจะเพิ่มขึ้นตามความสูงบล็อก: Z = 30mm, 55mm, 80mm, 105mm     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. PHASE 3: RESTORE OBSTACLES TO ORIGIN                                     │
│    - เมื่อวางบล็อกเสร็จสิ้น ย้ายบล็อกสิ่งกีดขวางจาก Feeder กลับมาวางยังช่องเดิม│
│    - รักษาระยะความสูงและเส้นทางหลบเสา Goal ไม่ให้ชนล้มเด็ดขาด               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 การป้องกันการชนเสา Goal (Horizontal Keepout & Detour Waypoints)
- **ปัญหา**: เมื่อวางบล็อกซ้อนกัน 4 ชั้น เสา Goal จะสูงถึง $130\text{ mm}$ หากแขนกลลากบล็อกจาก Feeder ผ่านกึ่งกลางสนามในแนวราบ มันจะชนเสา Goal ล้มลงมาทันที!
- **วิธีการแก้ไข**:
  1. สร้าง **Keepout Circle** รัศมี $38\text{ mm}$ รอบพิกัด Goal $(X=176.0, Y=0.0)$
  2. ก่อนเคลื่อนที่ ฟังก์ชัน `_plan_safe_transit()` จะคำนวณระยะทางจากเส้นทางตรงไปยังจุดศูนย์กลาง Goal
  3. หากเส้นทางผ่านวงกลมรัศมีอันตราย ระบบจะสร้าง **จุดเลี้ยวหลบ (Detour Waypoint)** ทันที:
     - **North Corridor (ช่องทางเลี่ยงทิศเหนือ)**: อ้อมผ่านพิกัด $X=222.0\text{ mm}$ (ด้านบนของแถว 0)
     - **South Corridor (ช่องทางเลี่ยงทิศใต้)**: อ้อมผ่านพิกัด $X=132.0\text{ mm}$ (ด้านล่างของแถว 2)
  4. ทำให้แขนกลโค้งอ้อมนอกกริด ไม่ตัดผ่านตรงกลางเสาอย่างแน่นอน!

```
                    [North Corridor Waypoint: X=222 mm]
                                ▲           ▲
                               /             \
    [Feeder Slot] ────────────+   (1,1) GOAL  +────────────► [Grid Cell [1,2]]
                                  (KEEPOUT)
```

### 6.3 ระยะยกสูงปลอดภัย (Vertical Clearance Trajectory)
- เมื่อมีบล็อกวางซ้อนบน Goal อย่างน้อย 1 ก้อน ความสูงในการเดินทาง (Transit Height) จะถูกยกระดับอัตโนมัติขึ้นสู่:
  $$Z_{\text{transit}} = \max(\text{hover\_z}, 142.0\text{ mm})$$
- ซึ่งสูงกว่ายอดเสา $130\text{ mm}$ อย่างปลอดภัย
- ทุกจังหวะการลงวางบล็อกที่ Goal จะลงในแนวดิ่ง $90^\circ$ และเมื่อปล่อยบล็อกเสร็จแล้ว จะยกถอยขึ้นในแนวดิ่ง $90^\circ$ จนพ้น $142\text{ mm}$ ก่อนจะเริ่มเคลื่อนที่ในแนวราบ

---

## 7. คู่มือการใช้งานหน้าจอ GUI / UI Interface Walkthrough with Screenshots

หน้าต่างโปรแกรมแบ่งออกเป็น 3 แถบเมนูหลักที่ออกแบบอย่างเป็นสัดส่วน:

### 7.1 หน้าจอภารกิจ (Stacking Mission Tab)
ใช้สำหรับวางแผนภารกิจ จัดลำดับการซ้อนบล็อก และสั่งเริ่มการทำงานอัตโนมัติ

![Stacking Mission UI](/docs/images/ui_mission_tab.png)

**รายละเอียดองค์ประกอบบนหน้าจอ:**
1. **Live Vision Stream (ซ้ายบน)**: แสดงภาพสดจากกล้องที่ผ่านการตรวจจับสีและพิกัด พร้อมบอกอัตราเฟรมเรต (FPS)
2. **Robot Telemetry (ซ้ายล่าง)**: แสดงสถานะการทำงาน (`IDLE`, `MOVING`), พิกัดจริงของแขนกล ($X, Y, Z, R$) และสถานะปั๊มลมดูด (`SUCTION: ON/OFF`)
3. **Field Mission Grid 3x3 (ขวาบน)**:
   - แต่ละช่องรอบนอกจะมีเมนูเลือก:
     - `#1 (Goal)` ถึง `#4 (Goal)`: บล็อกที่จะนำไปซ้อนที่เป้าหมาย
     - `Obs #1 (Feeder 1)` ถึง `Obs #4 (Feeder 4)`: บล็อกที่เป็นสิ่งกีดขวาง ย้ายไปพักที่ Feeder
   - **ปุ่มช่วยอำนวยความสะดวก**:
     - `🔄 Sync Vision`: ดึงสีบล็อกที่กล้องตรวจจับได้มาใส่ช่องตารางให้อัตโนมัติ
     - `↻ Auto 1..4 (Goal)`: กำหนด 4 บล็อกแรกเป็น Goal ตามเข็มนาฬิกา
     - `↻ Auto All (4 Goal + 4 Obs)`: กำหนด 4 บล็อกเป็น Goal และอีก 4 บล็อกเป็น Obstacle ไป Feeder
     - `🧹 Auto Obs`: กวาดบล็อกที่เหลือที่ไม่ได้ซ้อน ส่งไป Feeder อัตโนมัติ
     - `⚡ Use Stored Coordinates`: ติ๊กเมื่อต้องการใช้พิกัดจากการบันทึกมือ (ใช้แทนกล้องเวลาแสงเปลี่ยน)
4. **Mission Execution Plan (ขวาล่าง)**: ตารางแสดงขั้นตอนการทำงานจริงทั้ง 3 เฟสอย่างละเอียด พร้อมแสดงความสูงเป้าหมาย และสรุปจำนวนก้อนที่ด้านล่าง

---

### 7.2 หน้าจอควบคุมด้วยตนเอง (Manual Control Tab)
ใช้สำหรับทดสอบการทำงานของแขนกล จ๊อกกิ้งมือ และปรับแต่งตำแหน่ง

![Manual Control UI](/docs/images/ui_manual_tab.png)

**ฟังก์ชันหลัก:**
1. **Quick Presets**: ปุ่มด่วนสำหรับเคลื่อนที่ไปยังตำแหน่งมาตรฐาน (`Home`, `Hover` $Z=80\text{mm}$, `Drop-off` $Z=30\text{mm}$, `Zero R`)
2. **Cartesian Jog**: ปุ่มทิศทางควบคุมการเคลื่อนที่ตามแกน $X, Y, Z$ และมุมหมุน $R$ โดยสามารถเลือกขนาดก้าวได้ ($1\text{mm}, 5\text{mm}, 10\text{mm}, 50\text{mm}$)
3. **Tool Control**: ปุ่มเปิด/ปิดลมดูด (`SUCTION`), กางและหุบมือจับกลไก (`GRIP` / `RELEASE`)
4. **Direct Position (Move To)**: กล่องป้อนพิกัด $X, Y, Z, R$ เพื่อสั่งเคลื่อนที่ตรง พร้อมปุ่ม `Copy Pose` คัดลอกพิกัดปัจจุบันมาใส่

---

### 7.3 หน้าจอบันทึกพิกัดตำแหน่ง (Teach Positions Tab)
เมนูพิเศษสำหรับ **สอนจำพิกัด (Teaching & Calibration)** เพื่อแก้ปัญหากรณีกล้องเสียหรือแสงสะท้อน

![Teach Positions UI](/docs/images/ui_teach_tab.png)

**ขั้นตอนการบันทึกพิกัด:**
1. ใช้ปุ่ม Jog ด้านล่างขยับแขนกลให้ปลายหัวดูดแตะตรงกลางบล็อกหรือช่องเป้าหมายที่ต้องการ
2. กดปุ่ม **`📍 Teach`** ในแถวของช่องนั้น พิกัด $X, Y, Z$ ปัจจุบันจะถูกบันทึกทันที
3. สามารถกดปุ่ม **`🚀 Go To`** เพื่อทดสอบให้แขนกลบินไปหาพิกัดนั้นได้
4. กดปุ่ม **`💾 Save All Positions to YAML`** เพื่อบันทึกพิกัดทั้งหมดลงไฟล์ `dobot_ui.yaml` อย่างถาวร!

---

## 8. คู่มือการติดตั้ง ใช้งาน และแก้ไขปัญหา / Build, Run & Troubleshooting

### 8.1 การติดตั้งและคอมไพล์ (Build Instructions)
เปิด Terminal ในโฟลเดอร์ Workspace:
```bash
cd /home/thxncdzch/dobot_ws

# 1. โหลด Environment ของ ROS 2 Humble
source /opt/ros/humble/setup.bash

# 2. คอมไพล์แพ็กเกจทั้งหมด
colcon build --symlink-install

# 3. โหลด Environment ของโปรเจกต์
source install/setup.bash
```

### 8.2 การเปิดโปรแกรม (Run Instructions)

#### วิธีที่ 1: เปิดระบบทั้งหมดพร้อมกันด้วย Launch File (แนะนำ)
คำสั่งเดียวเปิดทั้งกล้องตรวจจับภาพ, โหนดควบคุมแขนกล และหน้าต่าง GUI:
```bash
ros2 launch dobot_v2 dobot_system.launch.py
```

#### วิธีที่ 2: เปิดเฉพาะหน้าต่าง GUI ในโหมดจำลอง (Mock Simulation Mode)
สามารถทดสอบการทำงานของ UI ได้แม้ไม่ได้เสียบแขนกล Dobot หรือกล้อง:
```bash
ros2 launch Dobot_UI dobot_ui.launch.py mock:=true
```

### 8.3 การแก้ไขปัญหาที่พบบ่อย (Troubleshooting & FAQ)

1. **ปัญหา: `Dobot not found` หรือเชื่อมต่อ USB ไม่ได้**
   - ตรวจสอบสาย USB ของ Dobot Magician เสียบแน่นหนา
   - ตรวจสอบชื่อพอร์ตด้วยคำสั่ง `ls -l /dev/ttyUSB*`
   - ให้สิทธิ์พอร์ต: `sudo chmod 666 /dev/ttyUSB0`
   - เพิ่มผู้ใช้เข้ากลุ่ม: `sudo usermod -a -G dialout $USER` แล้ว Logout ออกและ Login ใหม่อีกครั้ง

2. **ปัญหา: กล้องเปิดไม่ติด หรือขึ้น Error V4L2 Device Busy**
   - ตรวจสอบว่ามีโปรแกรมอื่นเปิดกล้องค้างอยู่หรือไม่: `fuser -v /dev/video0`
   - หรือกดปุ่ม **`🔄 Reset Detection Node`** บนแถบ Action Toolbar ของ UI โปรแกรมจะสั่ง Kill โปรเซสกล้องเดิมและเปิดขึ้นมาใหม่ให้ทันที

3. **ปัญหา: ข้อผิดพลาดเกี่ยวกับการนำเข้าไลบรารี `pydobot2`**
   - ตรวจสอบว่าติดตั้งเรียบร้อยแล้ว: `pip install pydobot2`
   - โปรเจกต์นี้เขียนตัวดักจับ Fallback อัตโนมัติ รองรับทั้ง `from pydobot import Dobot` และ `from pydobot.dobot import DobotException, MODE_PTP`

---

*จัดทำโดย: Thanadech (Google Deepmind Pair-Programming Assistant - Antigravity)*
*วันที่อัปเดตล่าสุด: กันยายน 2026*
