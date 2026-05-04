#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
import onnxruntime as ort
import numpy as np
import math
import os
from ament_index_python.packages import get_package_share_directory

class EMAFilter:
    """一阶指数平滑滤波器"""
    def __init__(self, alpha=0.15):
        self.alpha = alpha
        self.current_value = 0.0

    def update(self, target_value):
        self.current_value = self.alpha * target_value + (1.0 - self.alpha) * self.current_value
        return self.current_value

class InferenceNode(Node):
    def __init__(self):
        super().__init__('inference_node')
        
        # 1. 订阅视觉特征话题
        self.subscription = self.create_subscription(
            Float32MultiArray, '/hand_landmarks', self.listener_callback, 10)
        
        # 2. 发布舵机控制话题 (给 Micro-ROS 听的)
        self.publisher_ = self.create_publisher(Float32MultiArray, '/servo_targets', 10)
        
        # 3. 加载 ONNX 模型
        # 请确保 fist_model.onnx 和这个 Python 文件在同一个运行目录下，或使用绝对路径
        # 动态获取 ROS 2 功能包的安装路径
        package_share_directory = get_package_share_directory('arm_control_pkg')
        model_path = os.path.join(package_share_directory, 'models', 'fist_model.onnx')

        if not os.path.exists(model_path):
            self.get_logger().error(f"找不到模型文件: {model_path}")
        else:
            self.session = ort.InferenceSession(model_path)
            self.input_name = self.session.get_inputs()[0].name
            self.get_logger().info("🧠 ONNX 神经网络模型加载成功！")

        # 4. 初始化状态与滤波器
        self.target_fist = 0.0 # 视觉识别到的原始意图
        self.filter = EMAFilter(alpha=0.15)
        
        # 5. 设置控制定时器 (30Hz 稳定输出给下位机)
        self.timer = self.create_timer(1.0 / 30.0, self.control_loop)
        self.get_logger().info("🚀 推理节点已启动，正在发布 /servo_targets ...")

    def listener_callback(self, msg):
        """当收到视觉节点发来的坐标时触发"""
        if len(msg.data) == 63:
            # 转换数据格式给神经网络
            input_data = np.array([msg.data], dtype=np.float32)
            
            # 执行推理
            prediction = self.session.run(None, {self.input_name: input_data})
            
            # 提取 0.0 ~ 1.0 的预测结果
            self.target_fist = float(prediction[0][0][0])
        else:
            # 没有检测到手（空数组），安全归零
            self.target_fist = 0.0

    def control_loop(self):
        """独立于视觉的控制循环，保证机械臂持续收到平滑指令"""
        # 1. 滤波平滑
        smooth_fist = self.filter.update(self.target_fist)
        
        # 2. 运动学解算 (将 0~1 的意图映射为具体弧度或角度)
        a1 = smooth_fist * 0.5
        a2 = smooth_fist * math.pi
        a3 = smooth_fist * math.pi
        
        # 3. 限制安全极限范围 (Clamp) - 请根据你的实际机械臂限制修改！
        a1 = max(0.0, min(a1, 1.57))  # 例如限制在 0 ~ 90度
        a2 = max(0.0, min(a2, 3.14))
        a3 = max(0.0, min(a3, 3.14))
        
        # 4. 发布给 Micro-ROS
        control_msg = Float32MultiArray()
        control_msg.data = [float(a1), float(a2), float(a3)]
        self.publisher_.publish(control_msg)

def main(args=None):
    rclpy.init(args=args)
    node = InferenceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()