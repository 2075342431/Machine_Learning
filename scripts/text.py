import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

# 屏蔽 Qt 字体警告
import os
os.environ["QT_LOGGING_RULES"] = "qt.fonts.debug=false;qt.fonts.warning=false"

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')
        self.bridge = CvBridge()

        # 创建发布者
        self.publisher = self.create_publisher(Image, 'camera_image', 10)

        # 打开摄像头
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if self.cap.isOpened():
            self.get_logger().info("✅ 摄像头已成功打开！")
        else:
            self.get_logger().error("❌ 摄像头打开失败")

        # 定时循环
        self.timer = self.create_timer(0.03, self.timer_callback)

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        # 显示窗口
        cv2.imshow("Camera", frame)
        cv2.waitKey(1)

        # 发布图像（修复了函数名！）
        msg = self.bridge.cv2_to_imgmsg(frame, "bgr8")
        msg.header.stamp = self.get_clock().now().to_msg()
        self.publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.cap.release()
    cv2.destroyAllWindows()
    rclpy.shutdown()

if __name__ == '__main__':
    main()