# คู่มือระบบควบคุมแขนกล Dobot Magician ด้วย ROS 2, OpenCV, pydobot2 และ PyQt
## การพัฒนาระบบแขนกลอัจฉริยะ คัดแยกสี หลบหลีกสิ่งกีดขวาง และซ้อนบล็อกอัตโนมัติ (เริ่มต้นจากศูนย์)

> **ผู้พัฒนา / สถาปัตยกรรมระบบ:** Thanadech (Google Deepmind Pair-Programming Assistant)  
> **สภาพแวดล้อมระบบ:** Ubuntu Linux 22.04 LTS / ROS 2 Humble  
> **เอกสารรูปแบบ PDF:** [ดาวน์โหลดไฟล์ PDF ภาษาไทย (`DOBOT_MAGACIAN_TUTORIAL_TH.pdf`)](file:///home/thxncdzch/dobot_ws/docs/DOBOT_MAGACIAN_TUTORIAL_TH.pdf)

---

## 🎯 วัตถุประสงค์ของเอกสาร
เอกสารฉบับนี้จัดทำขึ้นเพื่อให้ผู้เริ่มต้นที่ไม่มีพื้นฐานด้านหุ่นยนต์หรือ ROS 2 มาก่อน สามารถเข้าใจหลักการทำงาน สถาปัตยกรรมการสื่อสาร โค้ดคอมพิวเตอร์วิทัศน์ และการควบคุมฮาร์ดแวร์แขนกล Dobot Magician ได้อย่างถ่องแท้ ตั้งแต่ทฤษฎีพื้นฐานจนถึงระบบอัตโนมัติ 3 เฟสจริงในโรงงานอุตสาหกรรม

---

## สารบัญเนื้อหา (Table of Contents)

1. [บทที่ 1: สถาปัตยกรรมระบบและโครงร่างสนามทำงาน](#บทที่-1-สถาปัตยกรรมระบบและโครงร่างสนามทำงาน)
2. [บทที่ 2: ปูพื้นฐาน ROS 2 จากศูนย์](#บทที่-2-ปูพื้นฐาน-ros-2-จากศูนย์)
3. [บทที่ 3: ระบบประมวลผลภาพด้วย OpenCV](#บทที่-3-ระบบประมวลผลภาพด้วย-opencv)
4. [บทที่ 4: การควบคุมแขนกล Dobot Magician ด้วย pydobot2](#บทที่-4-การควบคุมแขนกล-dobot-magician-ด้วย-pydobot2)
5. [บทที่ 5: การสร้างส่วนติดต่อผู้ใช้ด้วย PyQt](#บทที่-5-การสร้างส่วนติดต่อผู้ใช้ด้วย-pyqt)
6. [บทที่ 6: ตรรกะภารกิจ 3 เฟส และการหลบหลีกสิ่งกีดขวาง](#บทที่-6-ตรรกะภารกิจ-3-เฟส-และการหลบหลีกสิ่งกีดขวาง)
7. [บทที่ 7: คู่มือการใช้งานหน้าต่างโปรแกรม (UI Walkthrough)](#บทที่-7-คู่มือการใช้งานหน้าต่างโปรแกรม-ui-walkthrough)
8. [บทที่ 8: คำสั่งเริ่มต้นใช้งานและการแก้ไขปัญหา](#บทที่-8-คำสั่งเริ่มต้นใช้งานและการแก้ไขปัญหา)

---

## บทที่ 1: สถาปัตยกรรมระบบและโครงร่างสนามทำงาน

### 1.1 ภาพรวมทางกายภาพของสนามทำงาน (Field Layout)
ระบบนี้ทำงานบนแผ่นกระดาษมาตรฐาน A4 ($210 \times 297\text{ มม.}$) เป็นระนาบทำงานหลัก ประกอบด้วย:
1. **ฐานแขนกล Dobot Magician:** ติดตั้งอยู่ที่พิกัด $(X=105.0\text{ มม.}, Y=270.0\text{ มม.})$
2. **ถาดตาราง 3x3 (Pallet Grid):** ขนาดภายนอก $114.5 \times 114.5\text{ มม.}$ มีระยะห่างระหว่างจุดศูนย์กลางช่อง (Pitch) $35.0\text{ มม.}$
3. **เป้าหมาย Center Goal (ช่อง [1, 1]):** จุดที่แขนกลต้องนำบล็อกมาวางซ้อนกันในแนวตั้ง (ล็อกไว้ไม่เกิน 4 ก้อน)
4. **ช่อง Feeder 4 ตำแหน่ง (Feeder 1..4):** อยู่ฝั่งซ้ายของตาราง ($Y \approx +79.3\text{ มม.}$) ใช้พักบล็อกสิ่งกีดขวางชั่วคราว

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

### 1.2 โครงสร้างซอฟต์แวร์ใน Workspace (`dobot_ws`)
- `dobot_v2`: ประมวลผลภาพกล้อง, คำนวณพิกัด, ไดรเวอร์ฮาร์ดแวร์แขนกล, และตัวสร้างเส้นทางการเคลื่อนที่
- `Dobot_UI`: หน้าจอแดชบอร์ดกราฟิก PyQt รับส่งข้อมูลผ่าน ROS 2 แบบเรียลไทม์

---

## บทที่ 2: ปูพื้นฐาน ROS 2 จากศูนย์

### 2.1 ROS 2 คืออะไร?
ROS 2 (Robot Operating System 2) เป็น Distributed Robotics Middleware ที่ช่วยให้โปรแกรมหลาย ๆ โปรแกรม (Nodes) สื่อสารและประสานงานกันได้ผ่านโปรโตคอลมาตรฐาน DDS (Data Distribution Service)

### 2.2 องค์ประกอบพื้นฐานใน ROS 2
* **Node (โหนด):** โปรเซสเดี่ยวที่มีหน้าที่เฉพาะ เช่น `detection_node` (กล้อง), `dobot_controller` (แขนกล), `dobot_ui_node` (หน้าจอ GUI)
* **Topic (หัวข้อรับส่งข้อมูล):** ช่องทางการส่งข้อมูลทิศทางเดียวแบบ Publish-Subscribe

| ชื่อ Topic | Message Type | Publisher | Subscriber | คำอธิบาย |
|:---|:---|:---|:---|:---|
| `/detected_objects` | `std_msgs/msg/String` (JSON) | `detection_node` | `Dobot_UI`, `dobot_controller` | รายการพิกัดและสีบล็อก |
| `/detected_objects_image/compressed` | `sensor_msgs/msg/CompressedImage` | `detection_node` | `Dobot_UI` | สตรีมภาพวิดีโอจากกล้องแบบ JPEG |
| `/dobot_status` | `std_msgs/msg/String` (JSON) | `dobot_controller` | `Dobot_UI` | สถานะแขนกล พิกัด X, Y, Z, R และลมดูด |
| `/dobot_ui_cmd` | `std_msgs/msg/String` (JSON) | `Dobot_UI` | `dobot_controller` | คำสั่งเริ่มภารกิจ, จ๊อกกิ้ง, หยุดฉุกเฉิน |

---

## บทที่ 3: ระบบประมวลผลภาพด้วย OpenCV

### 3.1 การจับภาพผ่าน V4L2
ใช้ไดรเวอร์ฮาร์ดแวร์ Video4Linux2 ร่วมกับบีบอัด MJPG เพื่อให้ได้เฟรมเรต 30 FPS ความหน่วงต่ำ:
```python
import cv2
cap = cv2.VideoCapture('/dev/video0', cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
ret, frame = cap.read()
```

### 3.2 ทำไมต้องใช้พื้นที่สี HSV?
- **BGR:** สีเปลี่ยนตามความสว่างและเงาในห้อง
- **HSV:** แยก **Hue (เนื้อสี)** ออกจากความสว่าง ทำให้ระบุสีบล็อก (แดง, เหลือง, เขียว, ฟ้า ฯลฯ) ได้คงที่แม้แสงในห้องจะเปลี่ยนแปลง

### 3.3 Homography แปลงพิกเซลเป็นมิลลิเมตรจริง
ภาพจากกล้องที่เอียงจะถูกคำนวณผ่านเมทริกซ์การแปลง $3 \times 3$ (`cv2.getPerspectiveTransform`) จากมุม 4 มุมของตารางกริด ทำให้ได้พิกัดมิลลิเมตรจริงบนโต๊ะ ($gx, gy$) และแปลงเข้าสู่พิกัดแขนกล ($rx, ry, rz$) ได้อย่างแม่นยำ

---

## บทที่ 4: การควบคุมแขนกล Dobot Magician ด้วย pydobot2

### 4.1 การสื่อสารและระบบพิกัด
- สื่อสารผ่านพอร์ต USB Serial Baudrate **115200 bps**
- พิกัด Cartesian:
  - **X (มม.):** ยื่นแขนหน้า-หลัง (100 ถึง 330 มม.)
  - **Y (มม.):** ซ้าย-ขวา (-250 ถึง +250 มม.)
  - **Z (มม.):** แนวดิ่ง (-60 ถึง +160 มม.)
  - **R (องศา):** มุมหมุนหัวดูด (-180° ถึง +180°)

### 4.2 โหมดการเคลื่อนที่ PTP
- `MOVJ_XYZ` (Joint Movement): เคลื่อนที่เร็วแบบเส้นโค้ง ใช้ตอนบินในที่โล่ง (Transit)
- `MOVL_XYZ` (Linear Movement): เคลื่อนที่เป็นเส้นตรงแนวดิ่ง $90^\circ$ ใช้ตอนลดระดับลงดูดบล็อกและยกขึ้น เพื่อไม่ให้ชนบล็อกข้างเคียง

---

## บทที่ 5: การสร้างส่วนติดต่อผู้ใช้ด้วย PyQt

### 5.1 การแก้ปัญหา GUI Freezing ด้วย `QThread`
หากรัน `rclpy.spin()` ใน Main Thread หน้าต่างโปรแกรมจะค้าง เราจึงแยกการทำงานเป็น:
1. **Main UI Thread:** ดูแลการวาดกราฟิกและรับคลิก
2. **Worker Thread (`RosBridge(QThread)`):** วิ่งดักฟัง ROS 2 อยู่เบื้องหลัง แล้วส่งข้อมูลผ่าน `pyqtSignal` ข้ามเธรดอย่างปลอดภัย

---

## บทที่ 6: ตรรกะภารกิจ 3 เฟส และการหลบหลีกสิ่งกีดขวาง

### 6.1 ขั้นตอนการทำงาน 3 เฟส
1. **Phase 1 (Clear Obstacles):** ย้ายบล็อกสิ่งกีดขวางไปพักไว้ที่ **Feeder 1..4** ทางซ้าย
2. **Phase 2 (Stack Goal):** หยิบบล็อกเป้าหมาย (#1..#4) วางซ้อนที่ **Center Goal [1, 1]** (ล็อกสูงสุด 4 ชั้น: $Z = 30, 55, 80, 105\text{ มม.}$)
3. **Phase 3 (Restore Obstacles):** ย้ายบล็อกสิ่งกีดขวางจาก Feeder กลับคืนยังช่องเดิมในตาราง

### 6.2 การป้องกันการชนเสา Goal
- **Keepout Radius ($R = 38.0\text{ มม.}$):** พื้นที่หวงห้ามรอบเสา Goal
- **Detour Waypoints:** หากเส้นทางบินตรงตัดผ่านรัศมีหวงห้าม ระบบจะบินอ้อมระเบียงด้านนอก:
  - **North Bypass:** อ้อมด้านบนผ่าน $X = 222.0\text{ มม.}$
  - **South Bypass:** อ้อมด้านล่างผ่าน $X = 132.0\text{ มม.}$
- **Safe Vertical Clearance:** ขณะมีบล็อกอยู่บน Goal ความสูงบินจะถูกยกขึ้นสู่ $Z = 142.0\text{ มม.}$ (สูงกว่ายอดเสา 4 ชั้น $130\text{ มม.}$)

---

## บทที่ 7: คู่มือการใช้งานหน้าต่างโปรแกรม (UI Walkthrough)

### 7.1 หน้าจอภารกิจ (Stacking Mission Tab)
![Stacking Mission UI](file:///home/thxncdzch/dobot_ws/docs/images/ui_mission_tab.png)

- **ปุ่ม Auto:** `↻ Auto 1..4 (Goal)` (เป้าหมายอย่างเดียว), `↻ Auto All` (เป้าหมาย 4 + สิ่งกีดขวาง 4), `🧹 Auto Obs` (กวาดบล็อกที่เหลือลง Feeder)
- **ตาราง Execution Plan:** แสดงลำดับขั้นตอนจริงครบทั้ง 3 เฟส

### 7.2 หน้าจอควบคุมด้วยตนเอง (Manual Control Tab)
![Manual Control UI](file:///home/thxncdzch/dobot_ws/docs/images/ui_manual_tab.png)

- **Quick Presets:** ปุ่มบินด่วน `Home`, `Hover`, `Drop-off`, `Zero R`
- **Cartesian Jog:** ปุ่มทิศทาง $X, Y, Z, R$ ปรับระยะก้าวได้ ($1, 5, 10, 50\text{ มม.}$)
- **Tool Control:** สั่งปั๊มลมดูด (`SUCTION`) และมือจับ (`GRIP` / `RELEASE`)

### 7.3 หน้าจอบันทึกพิกัดตำแหน่ง (Teach Positions Tab)
![Teach Positions UI](file:///home/thxncdzch/dobot_ws/docs/images/ui_teach_tab.png)

- จ๊อกหัวดูดไปแตะจุดที่ต้องการ แล้วกด `📍 Teach`
- บันทึกพิกัดลงไฟล์ `dobot_ui.yaml` ด้วยปุ่ม `💾 Save All Positions to YAML` สำหรับรันโหมด Vision Bypass

---

## บทที่ 8: คำสั่งเริ่มต้นใช้งานและการแก้ไขปัญหา

### 8.1 คำสั่งเปิดระบบ
```bash
# คอมไพล์และโหลด environment
cd /home/thxncdzch/dobot_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

# เปิดระบบทั้งหมดพร้อมกัน
ros2 launch dobot_v2 dobot_system.launch.py

# หรือเปิดเฉพาะ GUI โหมดจำลอง (ไม่ต้องต่อฮาร์ดแวร์)
ros2 launch Dobot_UI dobot_ui.launch.py mock:=true
```

### 8.2 การแก้ไขปัญหาสิทธิ์ USB Serial
```bash
sudo usermod -a -G dialout $USER
sudo chmod 666 /dev/ttyUSB0
```
