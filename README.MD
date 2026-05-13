# 3-Axis Robot Arm Visual Intention Parsing System

## (三轴机械臂视觉运动意图解析系统)

<div align="center">
  <img src="https://img.shields.io/badge/Platform-ESP32-blue?style=for-the-badge" alt="Platform"/>
  <img src="https://img.shields.io/badge/Framework-PyTorch-red?style=for-the-badge" alt="Framework"/>
  <img src="https://img.shields.io/badge/Framework-ROS2_Humble-darkgreen?style=for-the-badge" alt="ROS2"/>
  <img src="https://img.shields.io/badge/Runtime-ONNX_Runtime-lightgrey?style=for-the-badge" alt="ONNX"/>
  <img src="https://img.shields.io/badge/Language-C++-green?style=for-the-badge" alt="Language"/>
  <img src="https://img.shields.io/badge/Language-Python-yellow?style=for-the-badge" alt="Language"/>
</div>

---

## 项目简介 (Project Overview)

本项目实现了一套**端到端的计算机视觉机械臂控制系统**。不同于传统的逆运动学遥控或示教器方案，该系统让机械臂直接"看懂"人类手部姿态，并根据手势意图（手掌张开/握拳）实时做出物理响应。

系统涵盖**数据采集 → 模型训练 → 模型转换 → 推理部署**的完整闭环，支持两种推理范式：
- **规则驱动 (Rule-based)**：MediaPipe 提取手部 21 个关键点 → 轻量全连接网络 (FistNet) 回归握拳开合度 → 运动学映射
- **数据驱动 (Data-driven)**：原始摄像头像素直接输入 ResNet18 卷积网络 → 端到端输出 3 个关节角度

通信层同时支持**自定义高速串口协议**和 **ROS 2 + micro-ROS** 两种架构，下位机采用 ESP32 + PlatformIO，具备逆运动学求解、工作空间约束、PID 控制等完整机器人基础能力。

---

## 核心特性 (Key Features)

### 1. 零延迟通信架构
- ESP32 固件采用**"贪婪消费者 (Greedy Consumer)"**模式的自定义高速串口协议
- 帧格式：`[0xFF | float×3 (12B) | checksum | 0xFE]`，波特率 921600
- 每次只执行缓冲区中**最新一帧**，丢弃中间过时帧，从根本上解决了传统流控中"缓冲区膨胀 (Buffer Bloat)"导致的秒级延迟
- 配合上位机 30Hz 定时发送，实现无缝视觉伺服跟随

### 2. 直觉化意图映射 (Fist-to-Curl)
- 抛弃反直觉的笛卡尔坐标映射，以**握拳开合度 (Fist Degree, 0.0 ~ 1.0)** 作为唯一控制量
- `0.0`（手掌完全张开）→ 机械臂自动回零位 (2048)，保持竖直
- `1.0`（完全握拳）→ 机械臂平滑卷曲至最大幅度
- `0.5`（半握拳）→ 映射到中间姿态，过渡自然

### 3. 端到端深度学习推理
- **FistNet**（全连接回归器）：63 维手部关键点坐标 → 1 维握拳开合度，80 epoch 训练，MSE Loss < 0.01
- **ResNet18**（卷积神经网络）：224×224 原始画面 → 3 个关节角度，完全绕过 MediaPipe 中间件
- 支持 PyTorch → ONNX 模型导出，可部署至 ONNX Runtime 获得更低推理延迟
- 内置 EMA 指数平滑滤波器，消除预测抖动，保证机械臂运动平滑

### 4. 完整的机器人运动学
- 4 自由度串联机械臂的正运动学 (FK) 与逆运动学 (IK) 求解
- 工作空间自动检测与边界趋近 (clamping)，避免奇异位形
- 支持两种 IK 算法：标准几何法 `moveTo()` 和带边界容错的 `moveTo_2()`
- 关节空间 → 舵机脉宽/位置的完整映射链

### 5. ROS 2 + micro-ROS 全栈通信
- **ROS 2 Humble** 节点化架构：摄像头节点、视觉特征节点、AI 推理节点
- **micro-ROS** 桥接 ESP32 与 PC 端 ROS 2 网络
- 标准化话题：`/hand_landmarks` (Float32MultiArray), `/camera_image` (Image), `/joint_states` (JointState), `/servo_targets` (Float32MultiArray)
- 支持 micro-ROS Agent 作为 DDS-XRCE 中间件

---

## 技术栈 (Tech Stack)

| 类别 | 技术/工具 |
| :--- | :--- |
| **硬件** | ESP32-WROOM, 3× STS Bus Servo (ID 12/14/15), 1× PWM Base Servo, USB Camera |
| **下位机固件** | C++17, PlatformIO, Arduino Framework, micro-ROS (rclc) |
| **舵机驱动** | SCServo (STS 总线舵机), ESP32Servo (PWM 舵机) |
| **视觉处理** | OpenCV, MediaPipe Hands (21-landmark model) |
| **深度学习** | PyTorch, TorchVision (ResNet18), ONNX Runtime |
| **机器人框架** | ROS 2 Humble (rclpy), micro-ROS (rmw_microxrcedds) |
| **通信协议** | 自定义高速串口帧协议 (921600 baud), DDS-XRCE |
| **可视化** | Matplotlib 3D 实时姿态显示, RViz (ROS 2) |
| **数值计算** | NumPy, Pandas |

---

## 系统架构 (System Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                        PC 端 (Ubuntu 22.04)                  │
│                                                              │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────────┐   │
│  │ Camera   │──▶│ Vision Node  │──▶│ Inference Node     │   │
│  │ (USB)    │   │ (MediaPipe   │   │ (FistNet / ONNX    │   │
│  │          │   │  + ROS2)     │   │  + EMA Filter)     │   │
│  └──────────┘   └──────┬───────┘   └────────┬───────────┘   │
│                        │                      │               │
│                        ▼                      ▼               │
│               /hand_landmarks         /servo_targets          │
│              (Float32MultiArray)    (Float32MultiArray)       │
│                        │                      │               │
│                        └──────────┬───────────┘               │
│                                   ▼                           │
│                          ┌────────────────┐                   │
│                          │ micro-ROS Agent│                   │
│                          │  (DDS-XRCE)    │                   │
│                          └───────┬────────┘                   │
└──────────────────────────────────┼────────────────────────────┘
                                   │ Serial (921600 baud)
                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                     ESP32 下位机                              │
│                                                              │
│  ┌──────────────────┐    ┌───────────────────────────────┐   │
│  │ Serial Receiver  │    │ micro-ROS Subscription        │   │
│  │ (Greedy Consumer)│    │ (joint_states callback)       │   │
│  └───────┬──────────┘    └───────────────┬───────────────┘   │
│          │                               │                    │
│          └───────────────┬───────────────┘                    │
│                          ▼                                    │
│                 ┌─────────────────┐                           │
│                 │   RobotArm      │                           │
│                 │  (IK + FK +     │                           │
│                 │   Servo Driver) │                           │
│                 └────────┬────────┘                           │
│                          │                                    │
│          ┌───────────────┼───────────────┐                    │
│          ▼               ▼               ▼                    │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐                │
│   │ Base     │   │ STS ID12 │   │ STS ID14 │                │
│   │ (PWM)    │   │ (Bus 1)  │   │ (Bus 2)  │  ...           │
│   └──────────┘   └──────────┘   └──────────┘                │
└──────────────────────────────────────────────────────────────┘
```

---

## 目录结构 (Directory Structure)

```text
Machine_Learning/
│
├── arm/                          # ESP32 下位机固件 (PlatformIO)
│   ├── platformio.ini            # 平台配置 (espressif32, micro-ROS)
│   ├── src/
│   │   ├── main.cpp              # 主固件: 高速串口 + micro-ROS 订阅 + 舵机控制
│   │   └── guanbo.cpp            # 舵机 ID 探测与 EPROM 校准工具 (已注释)
│   ├── lib/
│   │   ├── RobotArm/
│   │   │   ├── RobotArm.h        # 机械臂类声明 (FK, IK, 舵机映射)
│   │   │   └── RobotArm.cpp      # 运动学求解、正逆解、舵机控制实现
│   │   └── PidController/
│   │       ├── PidController.h   # PID 控制器类声明 (备用)
│   │       └── PidController.cpp # PID 实现
│   └── tools/
│       └── visualize.py          # 3D 实时位姿可视化 (Matplotlib)
│
├── scripts/                      # Python 运行脚本
│   ├── collect_data.py           # MediaPipe 数据采集器 (按键录制 63 维特征)
│   ├── test_serial.py            # 自定义串口协议测试 (手动输入角度)
│   ├── text.py                   # [ROS2] 推理节点：ONNX 推理 + EMA 滤波 + 运动学映射
│   ├── camera_node.py            # [ROS2] 摄像头发布节点 (sensor_msgs/Image)
│   ├── ai_inference_node.py      # [ROS2] ResNet18 端到端推理节点 (Image→JointState)
│   └── hand_gestures.csv         # 采集的手部关键点数据集
│
├── train/                        # 深度学习训练模块 (PyTorch)
│   ├── train.py                  # FistNet 全连接网络训练 + 训练/验证曲线 + 误差分析
│   ├── dataset.py                # ArmDataset 类 (图像→3 角度回归) + DataLoader
│   ├── text.py                   # [ROS2] ONNX 推理节点副本 (部署用)
│   ├── PyTorch_to_ONNX.py        # 模型格式转换: .pth → .onnx
│   ├── fist_model.pth            # 训练好的 FistNet 权重
│   ├── fist_model.onnx           # 导出的 ONNX 模型
│   ├── professional_report_charts.png  # 训练分析三联图
│   └── training_results.png      # 训练结果图
│
├── ros2_ws/                      # ROS 2 工作空间
│   ├── src/arm_control_pkg/      # ROS 2 Python 包
│   │   ├── package.xml           # 包描述
│   │   ├── setup.py              # 安装与节点注册
│   │   └── setup.cfg             # 包配置
│   ├── models/
│   │   └── fist_model.onnx       # 部署用的 ONNX 模型副本
│   ├── build/                    # colcon 构建输出
│   ├── install/                  # colcon 安装输出
│   └── log/                      # 构建日志
│
├── micro_ros/                    # micro-ROS Agent 工作空间
│   ├── src/
│   │   ├── micro_ros_msgs/       # micro-ROS 消息定义
│   │   └── micro-ROS-Agent/      # XRCE-DDS Agent 源码
│   ├── build/                    # colcon 构建输出
│   ├── install/                  # 安装产物 (含 libmicroxrcedds_agent)
│   └── log/                      # 构建日志
│
├── .venv/                        # Python 虚拟环境
├── .vscode/                      # VS Code 配置
├── .gitignore                    # Git 忽略规则
└── README.MD                     # 本文件
```

---

## 快速开始 (Quick Start)

### 1. 环境要求

| 组件 | 版本/说明 |
| :--- | :--- |
| 操作系统 | Ubuntu 22.04 |
| Python | 3.8+ (推荐 3.10) |
| ROS 2 | Humble Hawksbill |
| PlatformIO | 最新版 (CLI 或 VS Code 插件) |
| 硬件 | ESP32 开发板, USB 摄像头, STS 舵机 ×3, PWM 舵机 ×1 |

### 2. 安装依赖

```bash
# Python 依赖
pip install opencv-python mediapipe torch torchvision numpy pyserial pandas \
            matplotlib pillow onnxruntime

# ROS 2 相关 (需要先安装 ROS 2 Humble)
pip install rclpy std_msgs sensor_msgs cv_bridge
```

### 3. 编译与烧录 ESP32 固件

```bash
cd arm/
platformio run --target upload
```

关键配置 (`platformio.ini`)：
- 平台：`espressif32`，开发板：`esp32dev`
- 传输方式：`serial` (micro-ROS)，波特率 921600
- 依赖：`micro_ros_platformio` (Gitee 镜像), `SCServo`, `ESP32Servo`

固件上电后：舵机自动归零 (2048)，底层以 "贪婪消费者" 模式监听串口，或通过 micro-ROS 订阅 `/joint_states` 话题。

### 4. 数据采集

```bash
python3 scripts/collect_data.py
```

按键说明：
- **长按 O 键** → 录制 "手掌张开" (标签 0.0)
- **长按 C 键** → 录制 "握拳" (标签 1.0)
- **长按 H 键** → 录制 "半握拳" (标签 0.5)
- **Q / ESC** → 退出并保存至 `hand_gestures.csv`

### 5. 训练模型

```bash
python3 train/train.py
```

训练流程：
- 从 CSV 加载 63 维手部关键点特征
- 80/20 随机划分训练集/验证集
- 80 个 epoch，Adam 优化器 (lr=0.005)，MSE Loss
- 每 10 个 epoch 输出训练/验证损失
- 自动生成三联分析图：学习曲线 + 预测散点 + 误差分布
- 输出 `fist_model.pth` 权重文件

### 6. 模型转换 (可选)

```bash
python3 train/PyTorch_to_ONNX.py
```

导出 `fist_model.onnx` 供 ONNX Runtime 部署使用，输入名 `hand_landmarks` (63 维)，输出名 `fist_degree` (1 维)。

### 7. 推理部署

**方式 A：ROS 2 链路（完整 Pipeline）**

```bash
# 终端 1：启动 micro-ROS Agent
cd micro_ros/
source install/setup.bash
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0

# 终端 2：启动摄像头节点
python3 scripts/camera_node.py

# 终端 3：启动 AI 推理节点 (ResNet18)
python3 scripts/ai_inference_node.py
```

**方式 B：自定义串口直连（低延迟）**

```bash
# 终端 1：启动数据采集/视觉推理 (MediaPipe + FistNet)
python3 scripts/collect_data.py  # 或使用 text.py (ONNX 推理)

# 终端 2：手动发送角度测试
python3 scripts/test_serial.py
```

---

## 通信协议 (Communication Protocol)

### 自定义高速串口帧

| 字段 | 偏移 | 大小 | 描述 |
| :--- | :--- | :--- | :--- |
| Header | 0 | 1 B | `0xFF` 帧头 |
| Angle 1 | 1 | 4 B | 关节 1 弧度 (float32, little-endian) |
| Angle 2 | 5 | 4 B | 关节 2 弧度 |
| Angle 3 | 9 | 4 B | 关节 3 弧度 |
| Checksum | 13 | 1 B | 前 12 字节累加和取低 8 位 |
| Footer | 14 | 1 B | `0xFE` 帧尾 |

- 波特率：**921600**
- 帧总长：**15 字节**
- ESP32 收到合法帧后回传心跳字节 `0x06`

### ROS 2 话题一览

| 话题 | 类型 | 方向 | 描述 |
| :--- | :--- | :--- | :--- |
| `/hand_landmarks` | Float32MultiArray | Vision → Inference | 63 维手部关键点 (x,y,z × 21) |
| `/camera_image` | Image | Camera → AI | 原始摄像头画面 (BGR8) |
| `/joint_states` | JointState | PC → ESP32 | 目标关节角度 (4 个关节) |
| `/servo_targets` | Float32MultiArray | Inference → micro-ROS | 舵机目标弧度 (3 轴) |

---

## 机器学习模型 (ML Models)

### FistNet（全连接回归器）

```
Input (63) → Linear(63→64) → ReLU → Linear(64→32) → ReLU → Linear(32→1) → Sigmoid
```

- 用途：将 MediaPipe 提取的 21 个手部关键点 (63 维坐标) 回归为握拳开合度 (0.0 ~ 1.0)
- 损失函数：MSE Loss
- 优化器：Adam (lr=0.005)
- 训练轮数：80 epochs
- 输入归一化：关键点坐标已在 [0, 1] 范围内 (相对于画面尺寸)
- 输出：Sigmoid 确保输出在 [0, 1]

### ResNet18（端到端回归器）

- Backbone：TorchVision ResNet18 (weights=None, 从头训练)
- 修改：`fc` 层替换为 `Linear(512 → 3)`，直接输出 3 个关节角度
- 输入：112×112 RGB 图像，经过 ImageNet 标准化
- 用途：绕过 MediaPipe，直接从原始像素预测关节角度

---

## 控制链路详解 (Control Pipeline)

```
摄像头 (30 FPS)
  │
  ├── [路径 A: 规则驱动]
  │   MediaPipe Hands → 21 landmarks (63 坐标)
  │   → FistNet 回归 → 握拳开合度 [0, 1]
  │   → 线性映射 → 关节弧度
  │   → EMA 滤波 (α=0.15)
  │   → 安全限幅 (Clamp)
  │   → 串口/micro-ROS → ESP32
  │
  └── [路径 B: 端到端]
      Resize(112×112) + Normalize
      → ResNet18 推理
      → 3 关节角度
      → JointState 发布
      → micro-ROS → ESP32
                                    │
                                    ▼
                            ESP32 固件
                     ┌──────────────────┐
                     │ Greedy Consumer   │  ← 只取最新帧
                     │ 或 micro-ROS sub  │
                     └────────┬─────────┘
                              ▼
                     ┌──────────────────┐
                     │ radToSTS()       │  ← 弧度 → 舵机位
                     │ radToPWM()       │  ← 弧度 → PWM
                     └────────┬─────────┘
                              ▼
                     舵机执行 (1500 速度, 20 加速度)
```

---

## 机械臂参数 (Arm Specifications)

| 参数 | 值 | 说明 |
| :--- | :--- | :--- |
| L1 (基座高度) | 24.0 mm | Base → Shoulder 垂直偏移 |
| L2 (大臂) | 62.0 mm | Shoulder → Elbow |
| L3 (小臂) | 40.0 mm | Elbow → Wrist |
| L4 (末端) | 20.0 mm | Wrist → End-Effector |
| Base Servo | PWM (500–2500 μs) | GPIO 15, 0°–180° |
| STS ID 12 | Bus 1 (GPIO 4, 5) | 关节 2 |
| STS ID 14 | Bus 2 (GPIO 14, 16) | 关节 4 |
| STS ID 15 | Bus 2 (GPIO 17, 16) | 关节 3 |
| 舵机速度 | 1500 | STS WritePosEx 速度参数 |
| 舵机加速度 | 20 | STS WritePosEx 加速度参数 |

---

## 开发路线图 (Roadmap)

- [x] Phase 1：ESP32 固件与自定义高速串口协议
- [x] Phase 2：MediaPipe 数据采集与 FistNet 训练
- [x] Phase 3：PyTorch → ONNX 模型转换与部署
- [x] Phase 4：ROS 2 节点化架构 (Camera + Vision + Inference)
- [x] Phase 5：micro-ROS 桥接 ESP32 与 ROS 2 网络
- [x] Phase 6：ResNet18 端到端视觉推理
- [ ] Phase 7：MoveIt 2 路径规划与避障
- [ ] Phase 8：手眼标定 (Hand-Eye Calibration)
- [ ] Phase 9：轨迹录制与回放 (Teaching & Playback)
- [ ] Phase 10：Gazebo / RViz 数字孪生仿真

---

## 故障排查 (Troubleshooting)

| 症状 | 可能原因 | 解决方法 |
| :--- | :--- | :--- |
| 舵机不响应 | 串口未连接或波特率不匹配 | 检查 `/dev/ttyUSB0` 权限，确认波特率 921600 |
| 舵机抖动/过冲 | 速度/加速度过高 | 降低 `WritePosEx` 速度参数 (当前 1500) |
| 视觉识别不稳定 | 光照不足或背景干扰 | 提高 `min_detection_confidence` 至 0.7+ |
| 串口延迟大 | 未启用 Greedy Consumer 模式 | 确认固件中 `handle_custom_serial_fast()` 被调用 |
| ONNX 推理报错 | 模型路径错误 | 检查 `fist_model.onnx` 是否在当前工作目录 |
| micro-ROS 连接失败 | Agent 未启动或串口被占用 | 先关闭串口监视器，再启动 Agent |
| 训练 Loss 不收敛 | 数据量不足或标签噪声 | 确保每种手势至少录制 300+ 条，检查 CSV 标签 |
