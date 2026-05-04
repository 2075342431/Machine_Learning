#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
import cv2
import mediapipe as mp

class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')
        
        # 创建发布者，话题名: /hand_landmarks
        self.publisher_ = self.create_publisher(Float32MultiArray, '/hand_landmarks', 10)
        
        # 初始化摄像头和 MediaPipe
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.mp_hands = mp.solutions.hands.Hands(
            max_num_hands=1, 
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # 设置定时器，大约 30Hz 执行一次
        self.timer = self.create_timer(1.0 / 30.0, self.timer_callback)
        self.get_logger().info("📷 视觉节点已启动，正在发布 /hand_landmarks 话题...")

    def timer_callback(self):
        success, image = self.cap.read()
        if not success:
            self.get_logger().warning("无法读取摄像头画面！")
            return

        image = cv2.flip(image, 1)
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.mp_hands.process(img_rgb)

        msg = Float32MultiArray()

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            features = []
            # 提取 63 个点的特征
            for lm in hand_landmarks.landmark:
                features.extend([lm.x, lm.y, lm.z])
            msg.data = features # 装载 63 个浮点数
            
            # 在画面上画线方便调试
            self.mp_draw.draw_landmarks(image, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS)
        else:
            msg.data = [] # 没手时发布空数组，作为安全信号

        # 发布话题
        self.publisher_.publish(msg)

        # 显示调试画面 (在服务器上运行如果不需要界面可以注释掉这两行)
        cv2.imshow("Vision Node Debug", image)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cap.release()
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()