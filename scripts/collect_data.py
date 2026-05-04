import cv2
import mediapipe as mp
import serial
import struct
import time
import os
import csv
import uuid
import math

# --- 1. 信号处理模块 (底层核心) ---
class EMAFilter:
    """一阶指数平滑滤波器，用于消除高频视觉噪声"""
    def __init__(self, alpha=0.2):
        self.alpha = alpha
        self.current_value = None

    def update(self, new_value):
        if self.current_value is None:
            self.current_value = new_value
        else:
            self.current_value = self.alpha * new_value + (1 - self.alpha) * self.current_value
        return self.current_value

# --- 2. 硬件控制模块 (执行层) ---
class RobotArmController:
    """机械臂串口通信与安全管理"""
    def __init__(self, port, baud_rate, send_interval=0.033):
        self.send_interval = send_interval
        self.last_send_time = 0
        self.ser = None
        
        try:
            self.ser = serial.Serial(port, baud_rate, timeout=0.05)
            time.sleep(2)
            print(f"[HW] Serial connected: {port}")
        except Exception as e:
            print(f"[HW] Serial NOT connected. Simulation mode. Error: {e}")

    def _clamp(self, val, min_val, max_val):
        """安全限幅，防止舵机物理干涉或超调损坏"""
        return max(min_val, min(val, max_val))

    def send_angles(self, a1, a2, a3):
        # 1. 频率控制：防止串口堵塞
        curr_time = time.time()
        if curr_time - self.last_send_time < self.send_interval:
            return
        
        # 2. 硬件安全限幅 (假设你的协议接受 0~pi，请根据实际物理极限修改)
        safe_a1 = self._clamp(a1, 0.0, math.pi)
        safe_a2 = self._clamp(a2, 0.0, math.pi)
        safe_a3 = self._clamp(a3, 0.0, math.pi)

        if self.ser:
            try:
                float_data = struct.pack('<fff', float(safe_a1), float(safe_a2), float(safe_a3))
                checksum = sum(float_data) & 0xFF
                frame = struct.pack('<B', 0xFF) + float_data + struct.pack('<BB', checksum, 0xFE)
                self.ser.write(frame)
                self.ser.flush()
            except Exception as e:
                print(f"[HW] Serial TX error: {e}")
                
        self.last_send_time = curr_time

# --- 3. 主程序逻辑 (串联各个层) ---
def map_value(val, in_min, in_max, out_min, out_max):
    return (val - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def main():
    # 初始化模块
    arm = RobotArmController('/dev/ttyUSB0', 921600, send_interval=0.033)
    fist_filter = EMAFilter(alpha=0.15) # alpha越小越平滑，但延迟越大。0.15是个不错的平衡点
    
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6)
    mp_draw = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("\n--- Pipeline Started ---")
    
    while cap.isOpened():
        success, image = cap.read()
        if not success: break

        t_start = time.time()
        image = cv2.flip(image, 1)
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)
        
        target_fist_degree = 0.0 # 默认张开
        
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0] # 取第一只手
            
            # --- 视觉感知与特征提取 ---
            wrist = hand_landmarks.landmark[0]
            palm_base = hand_landmarks.landmark[9]
            tips = [hand_landmarks.landmark[i] for i in [8, 12, 16, 20]]
            
            palm_length = math.sqrt((palm_base.x - wrist.x)**2 + (palm_base.y - wrist.y)**2 + (palm_base.z - wrist.z)**2)
            avg_tip_dist = sum(math.sqrt((t.x - wrist.x)**2 + (t.y - wrist.y)**2 + (t.z - wrist.z)**2) for t in tips) / 4.0
            ratio = avg_tip_dist / (palm_length + 1e-6)
            
            # --- 意图解算 ---
            OPEN_LIMIT, CLOSE_LIMIT = 1.8, 0.7
            if ratio >= OPEN_LIMIT:
                raw_fist = 0.0
            elif ratio <= CLOSE_LIMIT:
                raw_fist = 1.0
            else:
                raw_fist = map_value(ratio, OPEN_LIMIT, CLOSE_LIMIT, 0.0, 1.0)
                
            target_fist_degree = raw_fist
            mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        
        # --- 信号滤波 (最关键的一步) ---
        # 无论有没有检测到手，都让滤波器持续工作。没手时 target 为 0，机械臂会平滑归零，而不是瞬间抽搐。
        smooth_fist = fist_filter.update(target_fist_degree)
        
        # --- 运动学映射 ---
        a1 = smooth_fist * 0.5
        a2 = smooth_fist * math.pi
        a3 = smooth_fist * math.pi
        
        # --- 硬件执行 ---
        arm.send_angles(a1, a2, a3)

        # --- 屏幕刷新 ---
        fps = 1.0 / (time.time() - t_start + 1e-6)
        cv2.putText(image, f"Smooth Fist: {smooth_fist:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(image, f"FPS: {fps:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.imshow('Robot Arm Pipeline', image)

        if cv2.waitKey(1) & 0xFF == 27: 
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()