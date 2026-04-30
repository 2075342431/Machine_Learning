import serial
import struct
import time
import sys

# 配置串口
SERIAL_PORT = '/dev/ttyUSB0' # 请根据实际情况修改，如 /dev/ttyACM0
BAUD_RATE = 921600

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # 等待 ESP32 重启
    print(f"Connected to {SERIAL_PORT} at {BAUD_RATE}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

def send_angles(a1, a2, a3):
    """
    发送 3 个角度到 ESP32
    帧格式: [0xFF, float1, float2, float3, checksum, 0xFE]
    """
    # 将 3 个 float 打包为 12 字节
    float_data = struct.pack('<fff', float(a1), float(a2), float(a3))
    
    # 计算校验和 (12 个字节的简单累加)
    checksum = sum(float_data) & 0xFF
    
    # 组装完整帧
    frame = struct.pack('<B', 0xFF) + float_data + struct.pack('<BB', checksum, 0xFE)
    
    ser.write(frame)
    # print(f"Sent: [{a1}, {a2}, {a3}] | Frame hex: {frame.hex().upper()}")

if __name__ == "__main__":
    print("Robot Arm Serial Tester (3-Axis)")
    print("Enter 3 angles separated by space (e.g., 0.0 0.5 -0.5), or 'q' to quit.")
    
    try:
        while True:
            user_input = input(">> ").strip()
            if user_input.lower() == 'q':
                break
            
            try:
                angles = [float(x) for x in user_input.split()]
                if len(angles) != 3:
                    print("Error: Please enter exactly 3 angles.")
                    continue
                
                send_angles(angles[0], angles[1], angles[2])
                
            except ValueError:
                print("Error: Invalid input. Please enter numbers.")
                
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        ser.close()
