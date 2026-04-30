# 3-Axis Robot Arm Visual Intention Parsing System
## (3轴机械臂视觉运动意图解析系统)

<div align="center">
  <img src="https://img.shields.io/badge/Platform-ESP32-blue?style=for-the-badge" alt="Platform"/>
  <img src="https://img.shields.io/badge/Framework-PyTorch-red?style=for-the-badge" alt="Framework"/>
  <img src="https://img.shields.io/badge/Language-C++-green?style=for-the-badge" alt="Language"/>
  <img src="https://img.shields.io/badge/Language-Python-yellow?style=for-the-badge" alt="Language"/>
</div>

## 📌 项目简介 (Project Overview)

本项目旨在探索和实现一种基于**计算机视觉**和**深度学习**的机械臂控制方案。我们摒弃传统的逆运动学解算或遥控器手动控制，让机械臂直接“看懂”人类的手部姿态，并根据手势意图（如张开、握拳）实时做出相应的物理反馈。

系统目前已实现极低延迟的物理链路，并通过“采集-训练-部署”的完整闭环，展示了从**规则驱动 (Rule-based)** 到**数据驱动 (Data-driven)** 的范式转变。

## 🎯 核心特性 (Key Features)

1. **零延迟通信架构**
   - ESP32 固件采用了“贪婪消费者 (Greedy Consumer)”模式的自定义高速串口协议。
   - 彻底解决了传统流控中常见的“缓冲区膨胀 (Buffer Bloat)”导致的秒级延迟问题，实现了 **30Hz** 的无缝视觉伺服跟随。

2. **直观的意图映射 (Fist-to-Curl)**
   - 抛弃反直觉的坐标映射，创新性地采用**“握拳开合度 (Fist Degree)”**作为控制核心。
   - **手掌完全张开**时：机械臂自动回零 (2048位)，保持绝对竖直。
   - **手掌握紧**时：机械臂平滑卷曲 180 度。

3. **端到端深度学习 (End-to-End Deep Learning)**
   - 支持抛弃中间件 (MediaPipe)，直接使用轻量级卷积神经网络 (**ResNet18**) 将原始摄像头像素翻译为 3 个关节角度。
   - 实现了从图像输入到电机控制信号的端到端推理。

## 📂 目录结构 (Directory Structure)

```text
Machine_Learning/
├── arm/                  # ESP32 下位机固件 (PlatformIO)
│   ├── src/main.cpp      # 高速串口通信与伺服控制逻辑
│   └── lib/RobotArm/     # 机械臂底层驱动库 (SCServo / ESP32Servo)
├── scripts/              # Python 运行脚本
│   ├── collect_data.py   # 基于 MediaPipe 的低延迟数据采集器
│   ├── test_serial.py    # 串口通信测试脚本
│   ├── camera_node.py    # [Phase 4] ROS2 摄像头发布节点
│   └── ai_inference_node.py # [Phase 4] ROS2 AI 推理节点
├── train/                # 机器学习训练模块 (PyTorch)
│   ├── dataset.py        # Dataset 类与图像预处理
│   └── train.py          # ResNet18 模型训练与评估脚本
├── data/                 # 数据存储目录 (已在 .gitignore 中忽略)
│   ├── raw/              # 原始采集图片
│   └── processed/        # 预处理后的数据集
└── models/               # 训练生成的模型权重 (已在 .gitignore 中忽略)
    └── best_model.pth    # 最佳模型权重
  
## 🛠️ 技术栈 (Tech Stack)

| 类别 | 技术/工具 |
| :--- | :--- |
| **硬件** | ESP32, 3x STS Bus Servos, USB Camera |
| **下位机** | C++, PlatformIO, Arduino Framework |
| **视觉处理** | OpenCV, MediaPipe |
| **机器学习** | PyTorch, TorchVision (ResNet18) |
| **通信协议** | Custom High-Speed Serial Protocol, ROS2 (Phase 4) |

## 🚀 快速开始 (Quick Start)

### 1. 环境准备

确保已安装 Python 3.8+ 和 PlatformIO IDE。

安装 Python 依赖：

```bash
pip install opencv-python mediapipe torch torchvision numpy pyserial