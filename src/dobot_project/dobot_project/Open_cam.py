#!/usr/bin/env python3
import time
import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class USBCamNode(Node):
    def __init__(self):
        super().__init__('usb_cam_node')

        self.dev = self.declare_parameter('device_id', 0).value
        self.width = self.declare_parameter('width', 640).value
        self.height = self.declare_parameter('height', 480).value
        self.fps = self.declare_parameter('fps', 30.0).value
        self.frame_id = self.declare_parameter('frame_id', 'camera_frame').value

        self.pub = self.create_publisher(Image, 'image_raw', qos_profile_sensor_data)

        self.msg = Image()
        self.msg.header.frame_id = str(self.frame_id)
        self.msg.encoding = 'bgr8'
        self.msg.is_bigendian = 0

        self.cap = None
        self._open_camera()

    def _open_camera(self):
        if self.cap is not None:
            self.cap.release()
            time.sleep(0.2)

        dev = int(self.dev) if str(self.dev).isdigit() else self.dev
        self.cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # KEY FIX: read timeout in milliseconds (OpenCV >= 4.5.3)
        self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000)
        self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)

        self.get_logger().info(f'Camera opened on {self.dev}')

    def run(self):
        consecutive_failures = 0
        while rclpy.ok():
            ret, frame = self.cap.read()

            if not ret:
                consecutive_failures += 1
                self.get_logger().warn(f'Frame read failed ({consecutive_failures})')
                if consecutive_failures >= 10:
                    self.get_logger().error('Too many failures, reopening camera')
                    self._open_camera()
                    consecutive_failures = 0
                time.sleep(0.05)
                rclpy.spin_once(self, timeout_sec=0)
                continue

            consecutive_failures = 0
            self.msg.header.stamp = self.get_clock().now().to_msg()
            self.msg.height, self.msg.width, _ = frame.shape
            self.msg.step = self.msg.width * 3
            self.msg.data = frame.tobytes()
            self.pub.publish(self.msg)
            rclpy.spin_once(self, timeout_sec=0)


def main(args=None):
    rclpy.init(args=args)
    node = USBCamNode()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        if node.cap is not None:
            node.cap.release()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()