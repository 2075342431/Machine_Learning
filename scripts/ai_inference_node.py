import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, JointState
from cv_bridge import CvBridge
import cv2
import torch
from torchvision import models, transforms
from PIL import Image as PILImage
import os

# --- 配置区 ---
MODEL_PATH = '/home/kk/Desktop/Machine_Learning/train/best_model.pth'
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class AIInferenceNode(Node):
    def __init__(self):
        super().__init__('ai_inference_node')
        
        # ROS2 通信
        self.subscription = self.create_subscription(Image, 'camera_image', self.image_callback, 10)
        self.publisher = self.create_publisher(JointState, 'joint_states', 10)
        self.bridge = CvBridge()

        # 加载模型
        self.model = models.resnet18(weights=None)
        self.model.fc = torch.nn.Linear(self.model.fc.in_features, 3)
        
        if os.path.exists(MODEL_PATH):
            self.model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
            self.get_logger().info(f"Model loaded from {MODEL_PATH}")
        else:
            self.get_logger().error(f"Model NOT found at {MODEL_PATH}!")
            
        self.model.to(DEVICE)
        self.model.eval()

        # 图像预处理
        self.transform = transforms.Compose([
            transforms.Resize((112, 112)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def image_callback(self, msg):
        # 1. 转换图像
        cv_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        pil_img = PILImage.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
        input_tensor = self.transform(pil_img).unsqueeze(0).to(DEVICE)

        # 2. 推理
        with torch.no_grad():
            outputs = self.model(input_tensor)
            angles = outputs.squeeze().cpu().numpy()

        # 3. 发布 JointState
        joint_msg = JointState()
        joint_msg.header.stamp = self.get_clock().now().to_msg()
        # 对应 ESP32 中的 4 个关节 (Joint1 固定为 0)
        joint_msg.name = ['Joint1', 'Joint2', 'Joint3', 'Joint4']
        joint_msg.position = [0.0, float(angles[0]), float(angles[1]), float(angles[2])]
        
        self.publisher.publish(joint_msg)
        # self.get_logger().info(f"Predicted Angles: {angles}")

def main(args=None):
    rclpy.init(args=args)
    node = AIInferenceNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
