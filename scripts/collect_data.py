import cv2
import mediapipe as mp
import serial
import struct
import time
import os
import csv
import uuid
import math

# --- 配置区 ---
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 921600
DATA_DIR = '/home/kk/Desktop/Machine_Learning/data'
IMG_DIR = os.path.join(DATA_DIR, 'images')
LABEL_FILE = os.path.join(DATA_DIR, 'labels.csv')

# 确保目录存在
os.makedirs(IMG_DIR, exist_ok=True)

# 串口初始化
try:
    # 增加超时时间，防止阻塞
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.05)
    time.sleep(2)
    print(f"Serial connected: {SERIAL_PORT}")
except:
    print("Serial not connected, running in simulation mode.")
    ser = None

def send_angles(a1, a2, a3):
    if ser:
        try:
            float_data = struct.pack('<fff', float(a1), float(a2), float(a3))
            checksum = sum(float_data) & 0xFF
            frame = struct.pack('<B', 0xFF) + float_data + struct.pack('<BB', checksum, 0xFE)
            ser.write(frame)
            ser.flush() # 确保数据立即发出
        except Exception as e:
            print(f"Serial send error: {e}")

# MediaPipe 初始化
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5, # 降低阈值以提高灵敏度
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

def map_value(val, in_min, in_max, out_min, out_max):
    return (val - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def main():
    cap = cv2.VideoCapture(0)
    # 降低分辨率以提高帧率和降低处理延迟
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    recording = False
    count = 0
    file_exists = os.path.isfile(LABEL_FILE)
    
    print("\n--- Data Collection Started (Optimized) ---")
    print("Controls: [SPACE] Start/Stop Recording, [ESC] Quit")
    
    last_send_time = 0
    
    with open(LABEL_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['image_path', 'angle1', 'angle2', 'angle3'])

        while cap.isOpened():
            success, image = cap.read()
            if not success: break

            t_start = time.time()
            image = cv2.flip(image, 1)
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)
            
            a1, a2, a3 = 0.0, 0.0, 0.0
            fist_degree = 0.0
            ratio = 0.0

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # 1. 获取关键点
                    wrist = hand_landmarks.landmark[0]
                    palm_base = hand_landmarks.landmark[9]
                    tips = [hand_landmarks.landmark[i] for i in [8, 12, 16, 20]]
                    
                    # 2. 计算比例
                    palm_length = math.sqrt((palm_base.x - wrist.x)**2 + (palm_base.y - wrist.y)**2 + (palm_base.z - wrist.z)**2)
                    avg_tip_dist = sum(math.sqrt((t.x - wrist.x)**2 + (t.y - wrist.y)**2 + (t.z - wrist.z)**2) for t in tips) / 4.0
                    ratio = avg_tip_dist / (palm_length + 1e-6)
                    
                    # 3. 握拳判定逻辑 (优化阈值)
                    # 张开手通常 ratio > 1.8，握拳通常 ratio < 1.3
                    OPEN_LIMIT = 1.8
                    CLOSE_LIMIT = 1.2
                    
                    if ratio >= OPEN_LIMIT:
                        fist_degree = 0.0
                    elif ratio <= CLOSE_LIMIT:
                        fist_degree = 1.0
                    else:
                        fist_degree = map_value(ratio, OPEN_LIMIT, CLOSE_LIMIT, 0.0, 1.0)
                    
                    # 4. 角度映射 (去除空间位置偏移)
                    a1 = fist_degree * 0.5
                    a2 = fist_degree * math.pi
                    a3 = fist_degree * math.pi
                    
                    mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            else:
                # 【关键：无手时强制归零】
                a1, a2, a3 = 0.0, 0.0, 0.0

            # 5. 限制串口发送频率 (约 30Hz) 防止堵塞
            curr_time = time.time()
            if curr_time - last_send_time > 0.033:
                send_angles(a1, a2, a3)
                last_send_time = curr_time

            # 6. 录制逻辑
            if recording and results.multi_hand_landmarks:
                img_name = f"{uuid.uuid4()}.jpg"
                img_path = os.path.join(IMG_DIR, img_name)
                cv2.imwrite(img_path, cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
                writer.writerow([img_name, a1, a2, a3])
                f.flush()
                count += 1

            # 显示调试信息
            fps = 1.0 / (time.time() - t_start + 1e-6)
            status_color = (0, 0, 255) if recording else (0, 255, 0)
            status_text = f"REC ({count})" if recording else "IDLE"
            
            cv2.putText(image, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
            cv2.putText(image, f"Fist: {fist_degree:.2f} (Ratio: {ratio:.2f})", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            cv2.putText(image, f"FPS: {fps:.1f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            cv2.imshow('Data Collector', image)

            key = cv2.waitKey(1) & 0xFF
            if key == 27: break
            elif key == 32: recording = not recording

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
