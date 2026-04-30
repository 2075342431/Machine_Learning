import serial
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import re
import threading
import sys

# 配置串口 (根据实际情况修改端口和波特率)
SERIAL_PORT = '/dev/ttyUSB0' # Linux通常是 /dev/ttyUSB0 或 /dev/ttyACM0
BAUD_RATE = 921600

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
except Exception as e:
    print(f"Error opening serial port: {e}")
    sys.exit(1)

plt.ion()
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

def update_plot(points):
    ax.clear()
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    
    # 画骨架
    ax.plot(xs, ys, zs, 'ro-', linewidth=2, markersize=5)
    
    # 画关节
    ax.scatter(xs, ys, zs, c='b', marker='o')
    
    # 设置范围 (根据机械臂长度调整)
    limit = 200
    ax.set_xlim([-limit, limit])
    ax.set_ylim([-limit, limit])
    ax.set_zlim([0, limit])
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Robot Arm 3D Visualization')
    
    plt.draw()
    plt.pause(0.01)

def serial_reader():
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("VIS:"):
                try:
                    # 格式: VIS:x0,y0,z0|x1,y1,z1|...
                    data = line[4:]
                    point_strs = data.split('|')
                    points = []
                    for ps in point_strs:
                        coords = [float(c) for c in ps.split(',')]
                        points.append(coords)
                    update_plot(points)
                except Exception as e:
                    print(f"Parse error: {e} in line: {line}")
            else:
                if line:
                    print(f"ESP32: {line}")

# 启动串口读取线程
thread = threading.Thread(target=serial_reader, daemon=True)
thread.start()

print("Visualization Ready.")
print("Commands: M x y z [alpha]")
print("Example: M 100 0 100 0")

try:
    while True:
        cmd = input("Enter Command: ")
        if cmd:
            ser.write((cmd + '\n').encode())
except KeyboardInterrupt:
    print("Exiting...")
    ser.close()
