import cv2
import mediapipe as mp
import csv
import os

# --- 配置区 ---
DATA_FILE = 'hand_gestures.csv' # 收集到的数据都存在这一个表格里

def main():
    # 1. 初始化 MediaPipe
    mp_hands = mp.solutions.hands
    # 注意：录制数据时可以稍微提高一点 confidence 阈值，保证录进去的都是高质量骨架
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
    mp_draw = mp.solutions.drawing_utils

    # 2. 初始化摄像头
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    file_exists = os.path.isfile(DATA_FILE)
    
    # 计数器，用于在屏幕上显示录制了多少条
    counts = {'open': 0, 'fist': 0, 'half': 0}

    print("\n=== 神经网络数据采集工具启动 ===")
    print("请将手放在画面中，然后长按键盘上的字母键录制：")
    print(" [O] 键 -> 录制 '张开' (标签: 0.0)")
    print(" [C] 键 -> 录制 '握拳' (标签: 1.0)")
    print(" [H] 键 -> 录制 '半握拳' (标签: 0.5)")
    print(" [Q] 或 [ESC] -> 退出并保存\n")

    with open(DATA_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        
        # 如果是新文件，写入表头 (x0, y0, z0, ..., x20, y20, z20, label)
        if not file_exists:
            header = []
            for i in range(21):
                header.extend([f'x{i}', f'y{i}', f'z{i}'])
            header.append('label')
            writer.writerow(header)

        while cap.isOpened():
            success, image = cap.read()
            if not success: break

            image = cv2.flip(image, 1)
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)
            
            features = [] # 用于存放 63 个坐标的空列表

            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # 【核心逻辑】：提取 21 个点的 x, y, z 并展平 (Flatten)
                for lm in hand_landmarks.landmark:
                    features.extend([lm.x, lm.y, lm.z])
                    
            # 3. 屏幕 UI 显示状态
            cv2.putText(image, f"Open (O): {counts['open']}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(image, f"Half (H): {counts['half']}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(image, f"Fist (C): {counts['fist']}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.imshow('Data Collection', image)

            # 4. 按键监听与标签打分逻辑
            key = cv2.waitKey(1) & 0xFF
            
            if key in [27, ord('q')]: # 退出
                break
            # 只有在画面中检测到手 (features不为空) 时才允许录制
            elif len(features) == 63: 
                label = None
                if key == ord('o'):
                    label = 0.0
                    counts['open'] += 1
                elif key == ord('c'):
                    label = 1.0
                    counts['fist'] += 1
                elif key == ord('h'):
                    label = 0.5
                    counts['half'] += 1

                # 如果按下了有效键，就把 63个特征 + 1个标签 存入 CSV
                if label is not None:
                    row_data = features + [label] # 列表拼接，变成 64 个元素
                    writer.writerow(row_data)
                    f.flush() # 强制写入硬盘，防止崩溃丢失数据

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n录制完成！共收集 {sum(counts.values())} 条特征数据。已保存至 {DATA_FILE}")

if __name__ == "__main__":
    main()