#!/usr/bin/env python3
"""Generator script for creating standalone Thai and English PDF, HTML, and Markdown
documents for the Dobot Magician Vision Stacking & Control System.
"""

import base64
import os
import subprocess

DOCS_DIR = "/home/thxncdzch/dobot_ws/docs"
IMAGES_DIR = os.path.join(DOCS_DIR, "images")


def get_base64_image(filename: str) -> str:
    path = os.path.join(IMAGES_DIR, filename)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


b64_mission = get_base64_image("ui_mission_tab.png")
b64_manual = get_base64_image("ui_manual_tab.png")
b64_teach = get_base64_image("ui_teach_tab.png")

CSS = """
@page {
    size: A4;
    margin: 18mm 16mm 18mm 16mm;
    @bottom-right {
        content: counter(page);
        font-family: 'Noto Sans Thai', 'Inter', sans-serif;
        font-size: 9pt;
        color: #64748b;
    }
}
body {
    font-family: 'Noto Sans Thai', 'Inter', system-ui, -apple-system, sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #1e293b;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
}
h1.doc-title {
    font-size: 22pt;
    font-weight: 800;
    color: #0369a1;
    margin-top: 0;
    margin-bottom: 6px;
    line-height: 1.25;
}
h2.doc-subtitle {
    font-size: 12.5pt;
    font-weight: 500;
    color: #475569;
    margin-top: 0;
    margin-bottom: 20px;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 12px;
}
h2.section-header {
    font-size: 14pt;
    font-weight: 700;
    color: #0f172a;
    border-bottom: 1.5px solid #0284c7;
    padding-bottom: 4px;
    margin-top: 24px;
    margin-bottom: 10px;
    page-break-after: avoid;
}
h3.sub-header {
    font-size: 11.5pt;
    font-weight: 600;
    color: #0369a1;
    margin-top: 16px;
    margin-bottom: 6px;
    page-break-after: avoid;
}
h4 {
    font-size: 10.5pt;
    font-weight: 600;
    color: #334155;
    margin-top: 12px;
    margin-bottom: 4px;
    page-break-after: avoid;
}
p, li {
    text-align: justify;
    margin-top: 3px;
    margin-bottom: 6px;
}
ul, ol {
    margin-top: 3px;
    margin-bottom: 10px;
    padding-left: 22px;
}
li { margin-bottom: 3px; }
.chapter-break { page-break-before: always; }
.callout {
    border-left: 4px solid #0284c7;
    background-color: #f0f9ff;
    padding: 10px 14px;
    margin: 12px 0;
    border-radius: 0 6px 6px 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}
.callout-warning { border-left-color: #f97316; background-color: #fff7ed; }
.callout-success { border-left-color: #10b981; background-color: #f0fdf4; }
.callout-title { font-weight: 700; margin-bottom: 4px; color: #0369a1; }
.callout-warning .callout-title { color: #c2410c; }
.callout-success .callout-title { color: #047857; }
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9pt;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid #cbd5e1;
    padding: 6px 9px;
    text-align: left;
}
th {
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 600;
}
tr:nth-child(even) { background-color: #f8fafc; }
pre {
    background-color: #0f172a;
    color: #f8fafc;
    padding: 9px 12px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
    font-size: 8.5pt;
    line-height: 1.4;
    overflow-x: auto;
    margin: 8px 0;
    page-break-inside: avoid;
}
code {
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
    font-size: 8.5pt;
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 1px 4px;
    border-radius: 3px;
}
pre code { background-color: transparent; color: inherit; padding: 0; }
.figure {
    text-align: center;
    margin: 14px 0;
    page-break-inside: avoid;
}
.figure img {
    max-width: 95%;
    height: auto;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
}
.figure-caption {
    font-size: 8.5pt;
    color: #64748b;
    margin-top: 5px;
    font-weight: 500;
}
.meta-box {
    display: flex;
    justify-content: space-between;
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 14px;
    margin-bottom: 20px;
    font-size: 9pt;
    color: #475569;
}
"""

TH_BODY = """
<h1 class="doc-title">คู่มือระบบควบคุมแขนกล Dobot Magician ด้วย ROS 2, OpenCV, pydobot2 และ PyQt</h1>
<h2 class="doc-subtitle">การพัฒนาระบบแขนกลอัจฉริยะ คัดแยกสี หลบหลีกสิ่งกีดขวาง และซ้อนบล็อกอัตโนมัติ (เริ่มต้นจากศูนย์)</h2>

<div class="meta-box">
    <div><strong>ผู้พัฒนา / ผู้จัดทำ:</strong> Thanadech (Google Deepmind Pair-Programming Assistant)</div>
    <div><strong>สภาพแวดล้อม:</strong> Ubuntu Linux 22.04 LTS / ROS 2 Humble</div>
    <div><strong>วันที่:</strong> กันยายน 2026</div>
</div>

<div class="callout callout-success">
    <div class="callout-title">🎯 เป้าหมายของเอกสารฉบับนี้</div>
    เอกสารฉบับนี้ถูกเขียนขึ้นเพื่อให้ผู้เริ่มต้นที่ไม่มีพื้นฐานด้านหุ่นยนต์หรือ ROS 2 มาก่อน สามารถเข้าใจหลักการทำงาน สถาปัตยกรรมการสื่อสาร โค้ดคอมพิวเตอร์วิทัศน์ และการควบคุมฮาร์ดแวร์แขนกล Dobot Magician ได้อย่างถ่องแท้ ตั้งแต่ทฤษฎีพื้นฐานจนถึงระบบอัตโนมัติ 3 เฟสจริงในโรงงานอุตสาหกรรม
</div>

<h2 class="section-header">สารบัญเนื้อหา (Table of Contents)</h2>
<ul>
    <li><strong>บทที่ 1:</strong> สถาปัตยกรรมระบบและโครงร่างสนามทำงาน (System Architecture & Field Layout)</li>
    <li><strong>บทที่ 2:</strong> ปูพื้นฐาน ROS 2 จากศูนย์ (ROS 2 Fundamentals from Scratch)</li>
    <li><strong>บทที่ 3:</strong> ระบบประมวลผลภาพด้วย OpenCV (Computer Vision & Homography)</li>
    <li><strong>บทที่ 4:</strong> การควบคุมแขนกล Dobot Magician ด้วย pydobot2 (Hardware Control)</li>
    <li><strong>บทที่ 5:</strong> การสร้างส่วนติดต่อผู้ใช้ด้วย PyQt (GUI Architecture & Multi-Threading)</li>
    <li><strong>บทที่ 6:</strong> ตรรกะภารกิจ 3 เฟส และการหลบหลีกสิ่งกีดขวาง (3-Phase Mission & Collision Avoidance)</li>
    <li><strong>บทที่ 7:</strong> คู่มือการใช้งานหน้าต่างโปรแกรม (UI Interface Walkthrough with Screenshots)</li>
    <li><strong>บทที่ 8:</strong> คำสั่งเริ่มต้นใช้งานและการแก้ไขปัญหา (Build, Run & Troubleshooting)</li>
</ul>

<div class="chapter-break"></div>

<h2 class="section-header">บทที่ 1: สถาปัตยกรรมระบบและโครงร่างสนามทำงาน</h2>

<h3 class="sub-header">1.1 ภาพรวมทางกายภาพของสนามทำงาน (Field Layout)</h3>
<p>
ระบบนี้ออกแบบมาสำหรับการแข่งขันและปฏิบัติการอัตโนมัติ โดยใช้แผ่นกระดาษขนาด A4 (210 x 297 มม.) เป็นระนาบทำงานหลัก ประกอบด้วยส่วนประกอบสำคัญ 4 ส่วน:
</p>
<ol>
    <li><strong>ฐานแขนกล Dobot Magician:</strong> ติดตั้งอยู่ที่พิกัด (X = 105.0 มม., Y = 270.0 มม.) ด้านหน้าของสนาม</li>
    <li><strong>ถาดตาราง 3x3 (Pallet Grid):</strong> ขนาดภายนอก 114.5 x 114.5 มม. มีระยะห่างระหว่างจุดศูนย์กลางช่อง (Pitch) 35.0 มม. ประกอบด้วย 8 ช่องรอบนอกสำหรับวางบล็อกสีต่าง ๆ</li>
    <li><strong>เป้าหมาย Center Goal (ช่อง [1, 1]):</strong> ช่องตรงกลางของตาราง เป็นจุดที่แขนกลต้องนำบล็อกมาวางซ้อนกันในแนวตั้ง (ถูกล็อกให้ซ้อนได้สูงสุด 4 ก้อน)</li>
    <li><strong>ช่อง Feeder 4 ตำแหน่ง (Feeder Slots 1..4):</strong> อยู่ทางฝั่งซ้ายของตาราง มีลักษณะเป็นวงกลมสีเขียว ใช้เป็นสถานีพักชั่วคราวสำหรับบล็อกที่เป็น "สิ่งกีดขวาง"</li>
</ol>

<pre>
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
</pre>

<h3 class="sub-header">1.2 สถาปัตยกรรมของซอฟต์แวร์ใน Workspace (dobot_ws)</h3>
<p>โปรเจกต์ถูกแบ่งออกเป็น 2 แพ็กเกจหลักตามหลักการ Single Responsibility Principle:</p>
<ul>
    <li><code>dobot_v2</code>: แพ็กเกจแกนหลักสำหรับประมวลผลภาพกล้อง (Vision), คำนวณเส้นทางการเคลื่อนที่ (Trajectory Generator), ควบคุมมอเตอร์และเครื่องมือปลายแขน (Hardware Driver)</li>
    <li><code>Dobot_UI</code>: หน้าต่างแดชบอร์ดกราฟิก พัฒนาด้วย PyQt เชื่อมต่อกับ ROS 2 เพื่อแสดงผลภาพสด แสดงพิกัดสถานะแบบเรียลไทม์ และส่งคำสั่งควบคุมหุ่นยนต์</li>
</ul>

<h2 class="section-header">บทที่ 2: ปูพื้นฐาน ROS 2 จากศูนย์ (ROS 2 Fundamentals)</h2>

<h3 class="sub-header">2.1 ROS 2 คืออะไร?</h3>
<p>
<strong>ROS 2 (Robot Operating System 2)</strong> ไม่ใช่ระบบปฏิบัติการที่ลงทับคอมพิวเตอร์เหมือน Windows แต่เป็น <em>Middleware</em> หรือกรอบการพัฒนาซอฟต์แวร์หุ่นยนต์แบบกระจายศูนย์ (Distributed System) ที่ช่วยให้โปรแกรมย่อยหลาย ๆ โปรแกรมสามารถคุยกัน รับส่งข้อมูลภาพ พิกัด และคำสั่งได้อย่างรวดเร็วและปลอดภัย ผ่านโปรโตคอลมาตรฐานอุตสาหกรรมที่เรียกว่า <strong>DDS (Data Distribution Service)</strong>
</p>

<h3 class="sub-header">2.2 องค์ประกอบพื้นฐานใน ROS 2</h3>

<h4>1. Node (โหนด)</h4>
<p>
เปรียบเสมือน "พนักงานหนึ่งคน" ในโรงงานที่มีหน้าที่ชัดเจนเพียงอย่างเดียว การแยกโปรแกรมเป็นโหนดเดี่ยว ๆ ช่วยให้หากโหนดใดโหนดหนึ่งมีปัญหา โหนดอื่นจะไม่พังตามไปด้วย:
</p>
<ul>
    <li><code>detection_node</code>: ดึงภาพจากกล้อง แปลงพิกัด และส่งรายชื่อบล็อกที่ตรวจจับได้</li>
    <li><code>dobot_controller</code>: ติดต่อกับแขนกล Dobot รับคำสั่งภารกิจ และสั่งเคลื่อนที่</li>
    <li><code>dobot_ui_node</code>: วาดหน้าจอ GUI รับคลิกจากผู้ใช้</li>
</ul>

<h4>2. Topic (หัวข้อการรับส่งข้อมูล) และ Publisher / Subscriber</h4>
<p>
เป็นการสื่อสารแบบทางเดียว (One-Way Streaming) แบบ <strong>Publish-Subscribe</strong>:
</p>
<ul>
    <li><strong>Publisher (ผู้ส่ง):</strong> ส่งข้อมูล (Message) เข้ามายังชื่อ Topic อย่างสม่ำเสมอ</li>
    <li><strong>Subscriber (ผู้รับ):</strong> ดักฟังสัญญาณ เมื่อมีข้อมูลใหม่เข้ามา Callback Function จะถูกเรียกทำงานทันที</li>
</ul>

<table>
    <thead>
        <tr>
            <th>ชื่อ Topic</th>
            <th>ประเภทข้อมูล (Message Type)</th>
            <th>ผู้ส่ง (Publisher)</th>
            <th>ผู้รับ (Subscriber)</th>
            <th>คำอธิบาย</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>/detected_objects</code></td>
            <td><code>std_msgs/msg/String</code> (JSON)</td>
            <td><code>detection_node</code></td>
            <td><code>Dobot_UI</code>, <code>dobot_controller</code></td>
            <td>ส่งข้อมูลพิกัด (X, Y, Z) สี และตำแหน่งตารางของบล็อกทั้งหมด</td>
        </tr>
        <tr>
            <td><code>/detected_objects_image/compressed</code></td>
            <td><code>sensor_msgs/msg/CompressedImage</code></td>
            <td><code>detection_node</code></td>
            <td><code>Dobot_UI</code></td>
            <td>สตรีมภาพวิดีโอแบบบีบอัด JPEG เพื่อแสดงผลบนหน้าจอ GUI แบบความหน่วงต่ำ</td>
        </tr>
        <tr>
            <td><code>/dobot_status</code></td>
            <td><code>std_msgs/msg/String</code> (JSON)</td>
            <td><code>dobot_controller</code></td>
            <td><code>Dobot_UI</code></td>
            <td>สถานะแขนกล (IDLE/MOVING), พิกัดปัจจุบัน X, Y, Z, R และสถานะลมดูด</td>
        </tr>
        <tr>
            <td><code>/dobot_ui_cmd</code></td>
            <td><code>std_msgs/msg/String</code> (JSON)</td>
            <td><code>Dobot_UI</code></td>
            <td><code>dobot_controller</code></td>
            <td>ส่งคำสั่งจากปุ่มกด เช่น เริ่มภารกิจ (mission), จ๊อกมือ (jog), โฮมมิ่ง (home)</td>
        </tr>
    </tbody>
</table>

<div class="chapter-break"></div>

<h2 class="section-header">บทที่ 3: ระบบประมวลผลภาพด้วย OpenCV (Computer Vision)</h2>

<h3 class="sub-header">3.1 การจับภาพจากกล้อง (V4L2 Video Streaming)</h3>
<p>
ในระบบ Linux กล้อง USB จะถูกมองเป็นอุปกรณ์ใน <code>/dev/video*</code> โดย OpenCV สามารถเชื่อมต่อผ่านไดรเวอร์ระดับเคอร์เนล <strong>V4L2 (Video4Linux2)</strong> ร่วมกับการถอดรหัสบีบอัดภาพฮาร์ดแวร์ MJPG ทำให้สามารถสตรีมภาพความละเอียด 640 x 480 ได้ที่ 30 เฟรมต่อวินาที (FPS) โดยไม่หน่วง CPU:
</p>
<pre><code>import cv2

cap = cv2.VideoCapture('/dev/video0', cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)
ret, frame = cap.read() # frame เป็น NumPy Array ในรูปแบบ BGR
</code></pre>

<h3 class="sub-header">3.2 ทำไมต้องใช้พื้นที่สี HSV แทน RGB/BGR ในการตรวจจับวัตถุ?</h3>
<p>
กล้องทั่วไปให้ภาพในระบบ <strong>BGR (Blue, Green, Red)</strong> ซึ่งทั้ง 3 ค่าจะแปรผันตามความสว่างของแสงในห้อง หากแสงแดดส่องเข้ามา หรือมีเงาตกกระทบ ค่า R, G, B จะเปลี่ยนไปทั้งหมด ทำให้การเขียนเงื่อนไขตรวจจับสีล้มเหลว
</p>
<p>
การแก้ปัญหาคือแปลงภาพเข้าสู่พื้นที่สี <strong>HSV (Hue, Saturation, Value)</strong>:
</p>
<ul>
    <li><strong>H (Hue - เนื้อสี):</strong> มีค่าตั้งแต่ 0 ถึง 180 ใน OpenCV ระบุเฉดสีแท้จริง เช่น สีแดง (~0-10 และ 160-180), สีเหลือง (~20-35), สีเขียว (~35-85), สีฟ้า (~90-130) ค่านี้จะ<strong>คงที่เสมอแม้แสงจะเปลี่ยน</strong></li>
    <li><strong>S (Saturation - ความสดของสี):</strong> แยกวัตถุสีเข้มออกจากสีขาวและแสงสะท้อน</li>
    <li><strong>V (Value - ความสว่าง):</strong> แสดงความเข้มของแสง สามารถกำหนดขอบเขตต่ำสุดเพื่อตัดเงาดำออกไปได้</li>
</ul>

<h3 class="sub-header">3.3 การแยกสี (Color Masking) และ Morphology</h3>
<p>
เราใช้คำสั่ง <code>cv2.inRange()</code> เพื่อสร้าง Mask ไบนารี (พิกเซลที่อยู่ในช่วงสีที่ต้องการจะเป็นสีขาว 255 และส่วนอื่นเป็นสีดำ 0) จากนั้นใช้การแปลงสัณฐานวิทยา (Morphology) เพื่อลบสัญญาณรบกวน:
</p>
<pre><code># แปลงสี BGR เป็น HSV
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

# ตัวอย่างช่วงสีเขียว
lower_green = np.array([35, 80, 70])
upper_green = np.array([85, 255, 255])
mask = cv2.inRange(hsv, lower_green, upper_green)

# ลบ Noise เม็ดทรายด้วย Morphological Opening (Erode แล้ว Dilate)
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
</code></pre>

<h3 class="sub-header">3.4 การแปลงภาพเป็นพิกัดจริงด้วย Perspective Homography</h3>
<p>
เนื่องจากกล้องติดตั้งทำมุมเฉียงกับโต๊ะ ภาพที่ได้จะเอียงเป็นสี่เหลี่ยมคางหมู เราจึงใช้คณิตศาสตร์ <strong>Homography Matrix (3x3)</strong> เพื่อบิดภาพระนาบเอียงให้กลายเป็นระนาบตั้งฉากสมบูรณ์:
</p>
<ol>
    <li>ตรวจหาจุดมุม 4 จุดของตารางกริดบนภาพกล้อง (u, v เป็นพิกเซล)</li>
    <li>จับคู่กับพิกัดจริงของถาดตาราง 114.5 x 114.5 มม. (x, y เป็นมิลลิเมตร)</li>
    <li>คำนวณเมทริกซ์การแปลงด้วย <code>cv2.getPerspectiveTransform()</code></li>
    <li>นำพิกัดพิกเซลของบล็อกทุกก้อนมาคูณเมทริกซ์นี้ เพื่อได้พิกัดจริงบนสนาม และแปลงเข้าสู่พิกัดฐานแขนกล (rx, ry, rz) ได้อย่างแม่นยำระดับมิลลิเมตร!</li>
</ol>

<div class="chapter-break"></div>

<h2 class="section-header">บทที่ 4: การควบคุมแขนกล Dobot Magician ด้วย pydobot2</h2>

<h3 class="sub-header">4.1 การสื่อสารแบบอนุกรม (Serial UART Protocol)</h3>
<p>
แขนกล Dobot Magician เชื่อมต่อกับคอมพิวเตอร์ผ่านสาย USB โดยภายในมีชิปแปลง USB-to-UART สื่อสารที่ Baudrate <strong>115200 bps</strong> โดยโปรโตคอลของ Dobot จะส่งแพ็กเก็ตข้อมูลขนาดคงที่ มี Header <code>0xAA 0xAA</code>, ความยาวข้อมูล (Length), รหัสคำสั่ง (Command ID), ข้อมูลคำสั่ง (Payload) และ Checksum ไลบรารี <code>pydobot2</code> ทำหน้าที่เป็น Wrapper แปลงคำสั่ง Python ให้กลายเป็นไบนารีแพ็กเก็ตเหล่านี้โดยอัตโนมัติ
</p>

<h3 class="sub-header">4.2 ระบบพิกัด Cartesian (X, Y, Z, R)</h3>
<div class="callout">
    <div class="callout-title">📐 ระบบแกนพิกัดของ Dobot Magician</div>
    <ul>
        <li><strong>X (มม.):</strong> แกนหน้า-หลัง (ยื่นแขนไปข้างหน้าเป็นบวก, ดึงเข้าหาตัวเป็นลบ) ขอบเขตปลอดภัย: 100 ถึง 330 มม.</li>
        <li><strong>Y (มม.):</strong> แกนซ้าย-ขวา (หมุนไปทางซ้ายเป็นบวก, หมุนไปทางขวาเป็นลบ) ขอบเขต: -250 ถึง +250 มม.</li>
        <li><strong>Z (มม.):</strong> แกนแนวดิ่ง (ยกแขนขึ้นด้านบนเป็นบวก, กดลงต่ำเป็นลบ) ขอบเขต: -60 ถึง +160 มม.</li>
        <li><strong>R (องศา):</strong> มุมหมุนเซอร์โวหัวดูดปลายแขน ขอบเขต: -180° ถึง +180°</li>
    </ul>
</div>

<h3 class="sub-header">4.3 โหมดการเคลื่อนที่แบบ PTP: MOVJ vs MOVL</h3>
<ul>
    <li><strong><code>MOVJ_XYZ</code> (Joint Interpolation):</strong> มอเตอร์ทุกข้อต่อหมุนพร้อมกัน แขนจะเหวี่ยงเป็นเส้นโค้งอิสระด้วยความเร็วสูงสุด ใช้สำหรับการบินเดินทางในที่โล่ง (Transit)</li>
    <li><strong><code>MOVL_XYZ</code> (Linear Interpolation):</strong> หัวดูดปลายแขนจะวิ่งเป็น<strong>เส้นตรงบริสุทธิ์</strong> เหมาะสำหรับจังหวะลดระดับลงไปดูดบล็อก (ลงตรง 90°) และยกบล็อกขึ้น เพื่อป้องกันไม่ให้หัวดูดหรือบล็อกเฉี่ยวชนบล็อกก้อนข้างเคียง</li>
</ul>

<pre><code>from pydobot import Dobot
from pydobot.dobot import MODE_PTP

device = Dobot(port='/dev/ttyUSB0')
device.speed(velocity=150.0, acceleration=150.0)

# บินแบบ MOVJ ไปยังพิกัดเหนือบล็อก
device.move_to(200.0, 0.0, 80.0, 0.0, mode=MODE_PTP.MOVJ_XYZ)

# ลดระดับลงแนวดิ่งแบบเส้นตรง MOVL ไปดูดบล็อก
device.suck(True)
device.move_to(200.0, 0.0, 12.5, 0.0, mode=MODE_PTP.MOVL_XYZ)
</code></pre>

<h2 class="section-header">บทที่ 5: การพัฒนาหน้าต่างส่วนติดต่อผู้ใช้ด้วย PyQt</h2>

<h3 class="sub-header">5.1 สถาปัตยกรรม PyQt (Event Loop & Multi-Threading)</h3>
<p>
หน้าต่างโปรแกรม GUI ทำงานด้วย <strong>Event Loop</strong> ที่คอยดักจับการคลิกเมาส์และวาดหน้าจอ หากมีงานที่ใช้เวลานาน (เช่น คำนวณภาพ หรือรอการเคลื่อนที่ของแขนกล) มารันบน Main Thread จะทำให้หน้าต่างโปรแกรม "ค้าง" (GUI Freezing) ทันที
</p>
<p>
<strong>วิธีแก้ปัญหาในโปรเจกต์นี้:</strong> เราแยกการทำงานออกเป็น 2 Threads ผ่านคลาส <code>RosBridge(QThread)</code>:
</p>
<ol>
    <li><strong>Main UI Thread:</strong> ดูแลการวาดกราฟิก รับคลิกผู้ใช้ และแสดงผลลัพธ์</li>
    <li><strong>ROS Bridge Worker Thread (`QThread`):</strong> ทำงานเบื้องหลัง คอยรันคำสั่ง <code>rclpy.spin_once()</code> เมื่อมีภาพกล้องหรือสถานะหุ่นยนต์ส่งเข้ามา จะส่งผ่าน <strong>`pyqtSignal`</strong> ข้ามเธรดมาสะกิดให้ Main Thread วาดภาพใหม่ได้อย่างลื่นไหล 100% โดยไม่มีการค้าง</li>
</ol>

<h2 class="section-header">บทที่ 6: ตรรกะภารกิจ 3 เฟส และการหลบหลีกสิ่งกีดขวาง</h2>

<h3 class="sub-header">6.1 ตรรกะภารกิจ 3 เฟส (3-Phase Mission Execution)</h3>
<p>
เพื่อตอบสนองต่อโจทย์การทำงานอัตโนมัติจริงในสนาม ระบบได้นำเสนอตรรกะ 3 เฟสสมบูรณ์แบบ:
</p>
<div class="callout callout-warning">
    <div class="callout-title">📋 ลำดับการทำงาน 3 เฟส</div>
    <ol>
        <li><strong>Phase 1 (Clear Obstacles):</strong> ตรวจหาก้อนบล็อกที่เป็นสิ่งกีดขวางในช่องที่ไม่ได้ถูกเลือกเป็นเป้าหมาย จากนั้นสั่งให้แขนกลไปดูดบล็อกเหล่านั้นย้ายไปวางพักไว้ที่ช่อง <strong>Feeder 1..4</strong> ทางฝั่งซ้าย</li>
        <li><strong>Phase 2 (Stack Goal):</strong> สั่งแขนกลไปดูดบล็อกเป้าหมายที่เลือกไว้ตามลำดับ (#1, #2, #3, #4) นำมาวางซ้อนกันในแนวดิ่งที่ช่อง <strong>Center Goal [1, 1]</strong> โดยล็อกไว้สูงสุด 4 ชั้น (ความสูงจะเพิ่มขึ้นเป็น Z = 30.0, 55.0, 80.0, 105.0 มม.)</li>
        <li><strong>Phase 3 (Restore Obstacles):</strong> เมื่อวางซ้อนเป้าหมายเสร็จสิ้น แขนกลจะไปดูดบล็อกสิ่งกีดขวางจากช่อง Feeder กลับมาวางคืนยังตำแหน่งเดิมของมันในตารางกริดอย่างแม่นยำ</li>
    </ol>
</div>

<h3 class="sub-header">6.2 ระบบป้องกันการชนเสา Goal (Goal Collision Avoidance)</h3>
<p>
เมื่อบล็อกซ้อนกัน 4 ชั้น เสาเป้าหมายจะสูงถึง 130 มม. หากแขนกลบินตรง ๆ ระหว่างช่อง Feeder (ทางซ้าย Y = +79 มม.) กับช่องตารางแถวขวา (Y = -35 มม.) เส้นทางบินตรงจะตัดผ่านกึ่งกลางเสา Goal พอดี ทำให้ชนเสาล้มทันที!
</p>
<p>
<strong>อัลกอริทึมการหลบหลีก (Path Detour Planning):</strong>
</p>
<ul>
    <li>กำหนดพื้นที่กระบอกหวงห้าม (Keepout Cylinder) รัศมี 38.0 มม. รอบจุดศูนย์กลาง Goal (176.0, 0.0)</li>
    <li>ก่อนบิน ฟังก์ชัน <code>_point_to_segment_dist()</code> จะคำนวณระยะทางจากเส้นทางบินตรงไปยังจุดศูนย์กลาง Goal</li>
    <li>หากพบว่าระยะทางสั้นกว่า 38.0 มม. (จะชนเสา) ระบบจะแทรก <strong>จุดเลี้ยวหลบ (Detour Waypoint)</strong> อัตโนมัติ:
        <ul>
            <li><strong>North Corridor Bypass:</strong> อ้อมขึ้นด้านบนผ่านพิกัด X = 222.0 มม. (เหนือแถว 0)</li>
            <li><strong>South Corridor Bypass:</strong> อ้อมลงด้านล่างผ่านพิกัด X = 132.0 มม. (ใต้แถว 2 ใกล้ฐานหุ่นยนต์)</li>
        </ul>
    </li>
    <li><strong>Safe Vertical Clearance:</strong> เมื่อเริ่มมีบล็อกวางซ้อนบน Goal ระดับความสูงบินข้ามสนามทั้งหมดจะถูกยกขึ้นสู่ Z = 142.0 มม. (สูงกว่าเสา 4 ชั้นอย่างปลอดภัย) และการลง/ขึ้นที่เสา Goal จะเป็นแนวดิ่ง 90° เสมอ</li>
</ul>

<div class="chapter-break"></div>

<h2 class="section-header">บทที่ 7: คู่มือการใช้งานหน้าต่างโปรแกรม (UI Walkthrough)</h2>

<h3 class="sub-header">7.1 หน้าจอภารกิจ (Stacking Mission Tab)</h3>
<p>แถบเมนูหลักสำหรับควบคุมภารกิจอัตโนมัติ 3 เฟส:</p>
<div class="figure">
    <img src="data:image/png;base64,__B64_MISSION__" alt="Stacking Mission UI">
    <div class="figure-caption">รูปที่ 1: หน้าจอหลัก Stacking Mission แสดงภาพกล้องสด, ตารางกริด 3x3 พร้อมการกำหนด Feeder และตารางแผนการทำงาน 3 เฟส</div>
</div>
<ul>
    <li><strong>ปุ่ม `↻ Auto 1..4 (Goal)`:</strong> กำหนด 4 บล็อกแรกเป็น Goal ตามเข็มนาฬิกา และล้างช่องที่เหลือ</li>
    <li><strong>ปุ่ม `↻ Auto All (4 Goal + 4 Obs)`:</strong> กำหนด 4 บล็อกเป็น Goal และอีก 4 บล็อกเป็นสิ่งกีดขวางส่งไป Feeder 1..4 ทันที</li>
    <li><strong>ปุ่ม `🧹 Auto Obs`:</strong> กวาดบล็อกที่เหลือที่ตรวจพบสี ส่งไปลงช่อง Feeder ที่ว่างให้อัตโนมัติ</li>
    <li><strong>ตาราง MISSION EXECUTION PLAN:</strong> แสดงขั้นตอนทั้ง 3 เฟสอย่างละเอียด (แถบสีส้ม = Phase 1 Clear, แถบสีฟ้า = Phase 2 Stack, แถบสีเขียว = Phase 3 Restore)</li>
    <li><strong>ปุ่ม `▶ START MISSION (Clear ➔ Stack ➔ Restore)`:</strong> ส่งคำสั่งเริ่มทำงานอัตโนมัติครบวงจร</li>
</ul>

<div class="chapter-break"></div>

<h3 class="sub-header">7.2 หน้าจอควบคุมด้วยตนเอง (Manual Control Tab)</h3>
<p>แถบเมนูสำหรับทดสอบการทำงานของแขนกล จ๊อกกิ้งมือ และสั่งงานเครื่องมือปลายแขน:</p>
<div class="figure">
    <img src="data:image/png;base64,__B64_MANUAL__" alt="Manual Control UI">
    <div class="figure-caption">รูปที่ 2: หน้าจอ Manual Control แสดงแผงปุ่ม Quick Presets, Cartesian Jogging, Tool Control และ Direct Position</div>
</div>
<ul>
    <li><strong>Quick Presets:</strong> บินไปยังจุดมาตรฐานทันที (`Home`, `Hover` Z=80mm, `Drop-off` Z=30mm, `Zero R`)</li>
    <li><strong>Cartesian Jog:</strong> ปุ่มทิศทางปรับตำแหน่งแกน X, Y, Z, R เลือกขนาดก้าวได้ (1mm, 5mm, 10mm, 50mm)</li>
    <li><strong>Tool Control:</strong> ปุ่มทดสอบเปิด/ปิดปั๊มลมดูด (`SUCTION`) และสั่งหนีบ/คลายมือจับ (`GRIP` / `RELEASE`)</li>
    <li><strong>Direct Position:</strong> พิมพ์พิกัด X, Y, Z, R ที่ต้องการ แล้วกด `🚀 Move To` หรือกด `📥 Copy Pose` เพื่อดึงพิกัดปัจจุบันมาใส่</li>
</ul>

<div class="chapter-break"></div>

<h3 class="sub-header">7.3 หน้าจอบันทึกพิกัดตำแหน่ง (Teach Positions Tab)</h3>
<p>เมนูพิเศษสำหรับบันทึกพิกัดทางกายภาพของแต่ละช่อง เสา Goal และ Feeder ลงในไฟล์ Configuration:</p>
<div class="figure">
    <img src="data:image/png;base64,__B64_TEACH__" alt="Teach Positions UI">
    <div class="figure-caption">รูปที่ 3: หน้าจอ Teach Positions สำหรับสอนจำพิกัดแต่ละช่องเพื่อใช้งานในโหมด Vision Bypass</div>
</div>
<ul>
    <li>ใช้จ๊อกกิ้งมือขยับหัวดูดให้แตะตรงกลางบล็อกหรือช่องเป้าหมาย</li>
    <li>กดปุ่ม <strong>`📍 Teach`</strong> เพื่อบันทึกพิกัดปัจจุบันเข้าตาราง</li>
    <li>กดปุ่ม <strong>`🚀 Go To`</strong> เพื่อทดสอบให้แขนกลบินไปหาตำแหน่งนั้น</li>
    <li>กดปุ่ม <strong>`💾 Save All Positions to YAML`</strong> เพื่อบันทึกลงไฟล์ <code>dobot_ui.yaml</code> ถาวร ทำให้ระบบทำงานต่อได้ทันทีแม้กล้องจะใช้งานไม่ได้</li>
</ul>

<h2 class="section-header">บทที่ 8: คำสั่งเริ่มต้นใช้งานและการแก้ไขปัญหา</h2>

<h3 class="sub-header">8.1 คำสั่งคอมไพล์และเปิดระบบ (Quick Start)</h3>
<pre><code># 1. โหลด Environment และคอมไพล์แพ็กเกจ
cd /home/thxncdzch/dobot_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

# 2. เปิดระบบทั้งหมดพร้อมกันด้วย Launch File (กล้อง + ตัวควบคุมแขนกล + GUI)
ros2 launch dobot_v2 dobot_system.launch.py

# หรือเปิดเฉพาะ GUI ในโหมดจำลอง (Mock Simulation Mode โดยไม่ต้องต่อฮาร์ดแวร์จริง)
ros2 launch Dobot_UI dobot_ui.launch.py mock:=true
</code></pre>

<h3 class="sub-header">8.2 ปัญหาที่พบบ่อยและวิธีแก้ไข (Troubleshooting)</h3>
<div class="callout callout-warning">
    <div class="callout-title">⚠️ ปัญหาการเชื่อมต่อ USB Serial บน Linux</div>
    หากต่อ Dobot แล้วขึ้น Error ไม่สามารถเปิดพอร์ต <code>/dev/ttyUSB0</code> ได้ เกิดจากสิทธิ์ผู้ใช้ Linux:
    <pre><code>sudo usermod -a -G dialout $USER
sudo chmod 666 /dev/ttyUSB0
# จากนั้น Logout ออกและ Login ใหม่อีกครั้ง</code></pre>
</div>

<div class="callout">
    <div class="callout-title">💡 ปัญหากล้องค้างหรือขึ้น Device Busy</div>
    หากกล้องเปิดไม่ติด ให้กดปุ่ม <strong>`🔄 Reset Detection Node`</strong> บนแถบด้านบนของ GUI โปรแกรมจะทำการตัดโปรเซสเดิมและเปิดใหม่อัตโนมัติใน 0.5 วินาที
</div>

<hr>
<p style="text-align: center; color: #64748b; font-size: 9pt; margin-top: 20px;">
    จัดทำโดย: Thanadech (Google Deepmind Pair-Programming Assistant - Antigravity) • กันยายน 2026
</p>
"""

EN_BODY = """
<h1 class="doc-title">Dobot Magician Robot System: ROS 2, OpenCV, pydobot2 & PyQt Full Guide</h1>
<h2 class="doc-subtitle">Autonomous Pick-and-Place, Multi-Color Segmentation, 3-Phase Mission Execution & Collision Avoidance (From Scratch)</h2>

<div class="meta-box">
    <div><strong>Author / Architect:</strong> Thanadech (Google Deepmind Pair-Programming Assistant)</div>
    <div><strong>Operating System:</strong> Ubuntu Linux 22.04 LTS / ROS 2 Humble</div>
    <div><strong>Release Date:</strong> September 2026</div>
</div>

<div class="callout callout-success">
    <div class="callout-title">🎯 Guide Objective</div>
    This comprehensive documentation is tailored for students, engineers, and researchers starting with zero robotics or ROS 2 background. It explains every concept from the ground up: communication middleware, perspective computer vision, robot kinematics, asynchronous GUI design, 3-phase automated obstacle clearance, and goal collision avoidance.
</div>

<h2 class="section-header">Table of Contents</h2>
<ul>
    <li><strong>Chapter 1:</strong> System Overview & Physical Field Geometry</li>
    <li><strong>Chapter 2:</strong> ROS 2 Fundamentals from Scratch (Nodes, Topics, Messages)</li>
    <li><strong>Chapter 3:</strong> Computer Vision Pipeline with OpenCV (V4L2, HSV, Morphology, Homography)</li>
    <li><strong>Chapter 4:</strong> Dobot Magician Control with pydobot2 (UART, Cartesian PTP, End-Effectors)</li>
    <li><strong>Chapter 5:</strong> GUI Architecture with PyQt (Event Loop, Signals & Slots, Thread-Safe RosBridge)</li>
    <li><strong>Chapter 6:</strong> 3-Phase Mission Execution & Goal Collision Avoidance</li>
    <li><strong>Chapter 7:</strong> UI Dashboard Walkthrough with Screenshots</li>
    <li><strong>Chapter 8:</strong> Build, Execution & Troubleshooting Guide</li>
</ul>

<div class="chapter-break"></div>

<h2 class="section-header">Chapter 1: System Overview & Physical Field Geometry</h2>

<h3 class="sub-header">1.1 Physical Layout & Coordinate Frame</h3>
<p>
The operational setup is configured on an international standard A4 sheet (210 x 297 mm) with four core spatial landmarks:
</p>
<ol>
    <li><strong>Dobot Magician Robot Base:</strong> Mounted at field origin coordinates (X = 105.0 mm, Y = 270.0 mm).</li>
    <li><strong>3x3 Pallet Grid:</strong> An outer bounding footprint of 114.5 x 114.5 mm with a 35.0 mm cell pitch. The 8 outer grid cells host colored cubes (Red, Yellow, Green, Blue, Orange, Purple, Cyan).</li>
    <li><strong>Center Goal Cell [1, 1]:</strong> The central drop target where selected cubes are vertically stacked (strictly locked to a 4-block maximum ceiling).</li>
    <li><strong>4 Feeder Slots (Feeder 1 to 4):</strong> Situated on the left perimeter strip (Y ~ +79.3 mm). Marked with green rings, these act as designated holding stations for obstacle cubes.</li>
</ol>

<pre>
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
</pre>

<h3 class="sub-header">1.2 Workspace Architecture (dobot_ws)</h3>
<p>The workspace separates concerns into modular ROS 2 packages:</p>
<ul>
    <li><code>dobot_v2</code>: Core vision processing node, perspective transform math, hardware serial driver, and 3-phase trajectory sequencer.</li>
    <li><code>Dobot_UI</code>: Rich interactive PyQt dashboard providing camera streaming, live robot status telemetry, mission sequencing, and manual Cartesian jogging.</li>
</ul>

<h2 class="section-header">Chapter 2: ROS 2 Fundamentals from Scratch</h2>

<h3 class="sub-header">2.1 What is ROS 2?</h3>
<p>
<strong>ROS 2 (Robot Operating System 2)</strong> is not an OS like Windows or Ubuntu; it is a distributed robotics software middleware. Built on the industrial <strong>DDS (Data Distribution Service)</strong> standard, ROS 2 enables separate programs (processes) to exchange data, synchronize clocks, and coordinate complex robotic tasks across multiple threads, processes, and network nodes seamlessly.
</p>

<h3 class="sub-header">2.2 Core ROS 2 Primitives</h3>

<h4>1. Nodes (`rclpy.node.Node`)</h4>
<p>
A Node is an independent executable process responsible for a single task:
</p>
<ul>
    <li><code>detection_node</code>: Captures webcam frames, segments cubes, and publishes detected metric coordinates.</li>
    <li><code>dobot_controller</code>: Communicates over serial with the Dobot arm, manages safety limits, and executes trajectories.</li>
    <li><code>dobot_ui_node</code>: Renders the GUI interface and transmits operator commands.</li>
</ul>

<h4>2. Topics & Publisher-Subscriber Pattern</h4>
<p>
Topics provide unidirectional, asynchronous streaming data channels. A Publisher broadcasts messages without knowing who is listening, and Subscribers trigger callback functions whenever a new message arrives.
</p>

<table>
    <thead>
        <tr>
            <th>Topic Name</th>
            <th>Message Type</th>
            <th>Publisher</th>
            <th>Subscriber</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>/detected_objects</code></td>
            <td><code>std_msgs/msg/String</code> (JSON)</td>
            <td><code>detection_node</code></td>
            <td><code>Dobot_UI</code>, <code>dobot_controller</code></td>
            <td>Real-time metric coordinates (X, Y, Z), colors, and cell assignments.</td>
        </tr>
        <tr>
            <td><code>/detected_objects_image/compressed</code></td>
            <td><code>sensor_msgs/msg/CompressedImage</code></td>
            <td><code>detection_node</code></td>
            <td><code>Dobot_UI</code></td>
            <td>Low-latency compressed JPEG stream rendered in the GUI viewer.</td>
        </tr>
        <tr>
            <td><code>/dobot_status</code></td>
            <td><code>std_msgs/msg/String</code> (JSON)</td>
            <td><code>dobot_controller</code></td>
            <td><code>Dobot_UI</code></td>
            <td>State telemetry: X, Y, Z, R Cartesian pose, suction status, connection state.</td>
        </tr>
        <tr>
            <td><code>/dobot_ui_cmd</code></td>
            <td><code>std_msgs/msg/String</code> (JSON)</td>
            <td><code>Dobot_UI</code></td>
            <td><code>dobot_controller</code></td>
            <td>Control messages: mission dispatch, manual jog, homing, emergency stop.</td>
        </tr>
    </tbody>
</table>

<div class="chapter-break"></div>

<h2 class="section-header">Chapter 3: Computer Vision Pipeline with OpenCV</h2>

<h3 class="sub-header">3.1 Camera Capture & V4L2 Video Streaming</h3>
<p>
On Linux, USB webcams interface via the Video4Linux2 (<code>cv2.CAP_V4L2</code>) kernel driver. Using hardware MJPG decoding enables low-latency streaming at 640 x 480 resolution and 30 FPS without taxing the CPU:
</p>
<pre><code>import cv2

cap = cv2.VideoCapture('/dev/video0', cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
ret, frame = cap.read() # Output is a BGR NumPy array
</code></pre>

<h3 class="sub-header">3.2 Why HSV is Superior to RGB/BGR for Color Segmentation</h3>
<p>
Standard cameras output images in <strong>BGR (Blue, Green, Red)</strong>. In BGR, illumination changes (shadows, daylight shifts, overhead flickering) simultaneously alter all three color channels, making thresholding unstable.
</p>
<p>
In contrast, <strong>HSV (Hue, Saturation, Value)</strong> isolates chromaticity from illumination:
</p>
<ul>
    <li><strong>H (Hue [0..180]):</strong> Encodes the pure spectral color independent of light intensity (e.g. Green is always ~35..85 regardless of room lighting).</li>
    <li><strong>S (Saturation [0..255]):</strong> Quantifies color purity, distinguishing vivid cube colors from white paper and highlights.</li>
    <li><strong>V (Value [0..255]):</strong> Quantifies luminance, allowing dark shadows to be filtered out cleanly.</li>
</ul>

<h3 class="sub-header">3.3 Color Masking & Morphological Noise Filtering</h3>
<p>
We apply <code>cv2.inRange()</code> to produce binary masks, followed by morphological opening to eliminate salt-and-pepper noise:
</p>
<pre><code># Convert BGR to HSV
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

# Define HSV boundaries for Green
lower_green = np.array([35, 80, 70])
upper_green = np.array([85, 255, 255])
mask = cv2.inRange(hsv, lower_green, upper_green)

# Morphological opening (Erosion followed by Dilation) removes noise
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
</code></pre>

<h3 class="sub-header">3.4 Metric Perspective Homography</h3>
<p>
Because the overhead camera views the table at an oblique angle, perspective keystoning distorts distances. We compute a 3x3 Homography transform matrix:
</p>
<ol>
    <li>Detect the 4 outer corner coordinates of the grid in image pixel space (u, v).</li>
    <li>Define target metric dimensions: a square 114.5 x 114.5 mm planar grid.</li>
    <li>Calculate the matrix: <code>cv2.getPerspectiveTransform(src_pts, dst_pts)</code>.</li>
    <li>Multiply any detected pixel centroid (u, v) by this homography matrix to obtain table-space millimeters (gx, gy), and map directly into Dobot robot base coordinates (rx, ry, rz)!</li>
</ol>

<div class="chapter-break"></div>

<h2 class="section-header">Chapter 4: Dobot Magician Control with pydobot2</h2>

<h3 class="sub-header">4.1 Serial UART Protocol</h3>
<p>
The Dobot Magician communicates via a USB-to-UART serial interface at <strong>115200 bps</strong>. The protocol transmits structured binary packets:
<code>Header (0xAA 0xAA) | Length | Command ID | Payload | Checksum</code>. The <code>pydobot2</code> library encapsulates this protocol into thread-safe Python methods.
</p>

<h3 class="sub-header">4.2 Cartesian Workspace Limits</h3>
<div class="callout">
    <div class="callout-title">📐 Dobot Magician Working Envelope</div>
    <ul>
        <li><strong>X (mm):</strong> Forward/backward extension. Safe limits: 100.0 mm to 330.0 mm.</li>
        <li><strong>Y (mm):</strong> Lateral left/right rotation. Limits: -250.0 mm to +250.0 mm.</li>
        <li><strong>Z (mm):</strong> Vertical elevation. Limits: -60.0 mm to +160.0 mm.</li>
        <li><strong>R (deg):</strong> End-effector wrist orientation. Limits: -180.0° to +180.0°.</li>
    </ul>
</div>

<h3 class="sub-header">4.3 PTP Motion Modes: MOVJ vs MOVL</h3>
<ul>
    <li><strong><code>MOVJ_XYZ</code> (Joint Movement):</strong> All joints interpolate simultaneously. The arm swings in a smooth, high-speed arc. Used for open transit between field waypoints.</li>
    <li><strong><code>MOVL_XYZ</code> (Linear Movement):</strong> The end-effector moves strictly along a Cartesian straight line. Crucial for picking up cubes vertically (downward 90°) and rising clear of neighbors without lateral collisions.</li>
</ul>

<pre><code>from pydobot import Dobot
from pydobot.dobot import MODE_PTP

device = Dobot(port='/dev/ttyUSB0')
device.speed(velocity=150.0, acceleration=150.0)

# Move above cube at hover height (Joint interpolation)
device.move_to(200.0, 0.0, 80.0, 0.0, mode=MODE_PTP.MOVJ_XYZ)

# Descend straight down to pick cube (Linear interpolation)
device.suck(True)
device.move_to(200.0, 0.0, 12.5, 0.0, mode=MODE_PTP.MOVL_XYZ)
</code></pre>

<h2 class="section-header">Chapter 5: GUI Architecture with PyQt</h2>

<h3 class="sub-header">5.1 Event Loop & Thread Decoupling</h3>
<p>
PyQt runs an internal <strong>Event Loop</strong> that processes user inputs and repaints the screen. Running ROS 2 subscription loops (<code>rclpy.spin()</code>) on this main thread would cause the UI to freeze and stop responding.
</p>
<p>
<strong>The Solution:</strong> We isolate ROS 2 communication into a dedicated background worker thread, <code>RosBridge(QThread)</code>:
</p>
<ol>
    <li><strong>Main UI Thread:</strong> Listens for mouse clicks, manages layouts, and renders Qt widgets.</li>
    <li><strong>Worker Thread (`RosBridge`):</strong> Continuously calls <code>rclpy.spin_once()</code> in the background. Incoming image frames and status JSONs are emitted across threads via thread-safe <strong>`pyqtSignal`</strong> instances, keeping the GUI 100% responsive.</li>
</ol>

<h2 class="section-header">Chapter 6: 3-Phase Mission Execution & Collision Avoidance</h2>

<h3 class="sub-header">6.1 3-Phase Automated Mission Workflow</h3>
<div class="callout callout-warning">
    <div class="callout-title">📋 3-Phase Mission Architecture</div>
    <ol>
        <li><strong>Phase 1 (Clear Obstacles):</strong> Non-goal cubes located in the grid are picked and cleared to <strong>Feeder Slots 1..4</strong> on the left.</li>
        <li><strong>Phase 2 (Stack Goal):</strong> Target cubes are picked in sequence (#1..#4) and vertically stacked at <strong>Center Goal [1, 1]</strong> up to a strict 4-block limit (Z = 30.0, 55.0, 80.0, 105.0 mm).</li>
        <li><strong>Phase 3 (Restore Obstacles):</strong> Once goal stacking finishes, all obstacle cubes in the feeders are returned to their original grid slots.</li>
    </ol>
</div>

<h3 class="sub-header">6.2 Goal Collision Avoidance System</h3>
<p>
When 4 cubes are stacked at Goal [1, 1], the tower reaches 130 mm tall. A straight-line trajectory between a feeder (Y = +79 mm) and a right-column cell (Y = -35 mm) would slice directly through the center goal, toppling the tower.
</p>
<p>
<strong>Intelligent Detour & Clearance Trajectory:</strong>
</p>
<ul>
    <li>A cylindrical Keepout Zone (R = 38.0 mm) is established around Goal (176.0, 0.0).</li>
    <li><code>_point_to_segment_dist()</code> evaluates candidate straight trajectories against this keepout cylinder.</li>
    <li>If a collision is detected, <code>_plan_safe_transit()</code> inserts a perimeter corridor detour waypoint:
        <ul>
            <li><strong>North Corridor Bypass:</strong> Detours around the top perimeter via X = 222.0 mm.</li>
            <li><strong>South Corridor Bypass:</strong> Detours around the bottom perimeter via X = 132.0 mm.</li>
        </ul>
    </li>
    <li><strong>Elevated Vertical Clearance:</strong> Whenever cubes exist on the goal, transit elevation is automatically increased to Z_transit = max(hover_z, 142.0 mm), safely clearing the 130 mm tower.</li>
</ul>

<div class="chapter-break"></div>

<h2 class="section-header">Chapter 7: UI Dashboard Walkthrough with Screenshots</h2>

<h3 class="sub-header">7.1 Stacking Mission Tab</h3>
<p>Primary dashboard for configuring the 3-phase mission, assigning goal and obstacle roles, and executing autonomous stacking:</p>
<div class="figure">
    <img src="data:image/png;base64,__B64_MISSION__" alt="Stacking Mission UI">
    <div class="figure-caption">Figure 1: Stacking Mission Tab featuring live camera feed, 3x3 grid assignment cards with feeder routing, and 3-phase execution table</div>
</div>
<ul>
    <li><strong>`↻ Auto 1..4 (Goal)` Button:</strong> Assigns orders #1 to #4 clockwise to Goal and clears remaining cells.</li>
    <li><strong>`↻ Auto All (4 Goal + 4 Obs)` Button:</strong> Assigns 4 Goal cubes (#1..#4) and routes remaining 4 cubes to Feeders 1..4.</li>
    <li><strong>`🧹 Auto Obs` Button:</strong> Automatically routes unassigned colored cells to available feeder slots.</li>
    <li><strong>Execution Plan Table:</strong> Displays color-coded task phases (Orange = Clear, Sky Blue = Stack, Teal = Restore).</li>
    <li><strong>`▶ START MISSION (Clear ➔ Stack ➔ Restore)` Button:</strong> Dispatches the mission to the controller node.</li>
</ul>

<div class="chapter-break"></div>

<h3 class="sub-header">7.2 Manual Control Tab</h3>
<p>Manual jogging and tool verification panel for setup and fine adjustments:</p>
<div class="figure">
    <img src="data:image/png;base64,__B64_MANUAL__" alt="Manual Control UI">
    <div class="figure-caption">Figure 2: Manual Control Tab with Quick Presets, Cartesian Jogging D-Pad, Tool End-Effector toggles, and Direct Position inputs</div>
</div>
<ul>
    <li><strong>Quick Presets:</strong> Instant positioning to `Home`, `Hover` (Z=80mm), `Drop-off` (Z=30mm), or `Zero R`.</li>
    <li><strong>Cartesian Jog:</strong> Directional buttons for X, Y, Z, R with selectable step sizes (1mm, 5mm, 10mm, 50mm).</li>
    <li><strong>Tool Control:</strong> Dedicated toggles for suction cup pump (`SUCTION`) and gripper action (`GRIP` / `RELEASE`).</li>
    <li><strong>Direct Position:</strong> Precision input fields for X, Y, Z, R coordinates with `Copy Pose` and `Move To`.</li>
</ul>

<div class="chapter-break"></div>

<h3 class="sub-header">7.3 Teach Positions Tab (Vision Bypass)</h3>
<p>Calibration interface for manually storing physical coordinates of each cell, the center goal, and feeders:</p>
<div class="figure">
    <img src="data:image/png;base64,__B64_TEACH__" alt="Teach Positions UI">
    <div class="figure-caption">Figure 3: Teach Positions Tab for capturing and testing custom coordinates, saved directly to dobot_ui.yaml</div>
</div>
<ul>
    <li>Jog the robot tip to touch the center of a desired cell or feeder.</li>
    <li>Click <strong>`📍 Teach`</strong> in that cell's row to record live telemetry coordinates.</li>
    <li>Click <strong>`🚀 Go To`</strong> to verify repeatable positioning.</li>
    <li>Click <strong>`💾 Save All Positions to YAML`</strong> to persist coordinates, enabling operation even if the camera is occluded or broken.</li>
</ul>

<h2 class="section-header">Chapter 8: Build, Execution & Troubleshooting Guide</h2>

<h3 class="sub-header">8.1 Build & Launch Commands</h3>
<pre><code># 1. Source ROS 2 Humble and build workspace
cd /home/thxncdzch/dobot_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

# 2. Launch full system (Vision + Controller + GUI)
ros2 launch dobot_v2 dobot_system.launch.py

# Or launch GUI in Mock Simulation Mode (no physical robot required)
ros2 launch Dobot_UI dobot_ui.launch.py mock:=true
</code></pre>

<h3 class="sub-header">8.2 Troubleshooting & FAQ</h3>
<div class="callout callout-warning">
    <div class="callout-title">⚠️ USB Serial Permissions on Linux</div>
    If the controller reports <code>Permission denied: '/dev/ttyUSB0'</code>:
    <pre><code>sudo usermod -a -G dialout $USER
sudo chmod 666 /dev/ttyUSB0
# Log out and log back in for group changes to take effect</code></pre>
</div>

<div class="callout">
    <div class="callout-title">💡 Camera Video Node Reset</div>
    If the video stream freezes or reports <code>Device Busy</code>, click the <strong>`🔄 Reset Detection Node`</strong> button in the UI toolbar to cleanly restart the vision process in 0.5s.
</div>

<hr>
<p style="text-align: center; color: #64748b; font-size: 9pt; margin-top: 20px;">
    Author: Thanadech (Google Deepmind Pair-Programming Assistant - Antigravity) • September 2026
</p>
"""


def build_html(body: str, title: str, lang: str) -> str:
    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{CSS}
</style>
</head>
<body>
{body}
</body>
</html>"""
    html = html.replace("__B64_MISSION__", b64_mission)
    html = html.replace("__B64_MANUAL__", b64_manual)
    html = html.replace("__B64_TEACH__", b64_teach)
    return html


def main():
    print("Generating standalone Thai and English documents...")

    # 1. Thai HTML & PDF
    th_html = build_html(TH_BODY, "คู่มือระบบควบคุมแขนกล Dobot Magician", "th")
    th_html_path = os.path.join(DOCS_DIR, "DOBOT_MAGACIAN_TUTORIAL_TH.html")
    th_pdf_path = os.path.join(DOCS_DIR, "DOBOT_MAGACIAN_TUTORIAL_TH.pdf")

    with open(th_html_path, "w", encoding="utf-8") as f:
        f.write(th_html)
    print(f"Wrote {th_html_path}")

    cmd_th = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={th_pdf_path}",
        th_html_path,
    ]
    subprocess.run(cmd_th, check=True)
    print(f"Generated {th_pdf_path} (Size: {os.path.getsize(th_pdf_path)} bytes)")

    # 2. English HTML & PDF
    en_html = build_html(
        EN_BODY,
        "Dobot Magician Robot System: ROS 2, OpenCV, pydobot2 & PyQt Full"
        " Guide",
        "en",
    )
    en_html_path = os.path.join(DOCS_DIR, "DOBOT_MAGACIAN_TUTORIAL_EN.html")
    en_pdf_path = os.path.join(DOCS_DIR, "DOBOT_MAGACIAN_TUTORIAL_EN.pdf")

    with open(en_html_path, "w", encoding="utf-8") as f:
        f.write(en_html)
    print(f"Wrote {en_html_path}")

    cmd_en = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={en_pdf_path}",
        en_html_path,
    ]
    subprocess.run(cmd_en, check=True)
    print(f"Generated {en_pdf_path} (Size: {os.path.getsize(en_pdf_path)} bytes)")

    print("\nALL PDF AND HTML FILES GENERATED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
