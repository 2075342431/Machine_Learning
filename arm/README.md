    1 # 3-Axis Robot Arm Visual Intention Parsing System (3轴机械臂视觉运动意图解析系统)
    2
    3 ## 📌 项目简介 (Project Overview)
    4 本项目旨在探索和实现一种基于**计算机视觉**和**深度学习**的机械臂控制方案。我们并非使用传统的逆运动学或遥控器，而是让机械臂直接“看懂”人类的手部姿态，并根据手势的意图（如张开、握拳）实时做出相应的物理反馈。
    5
    6 系统目前已实现极低延迟的物理链路，并通过“采集-训练-部署”的完整闭环，展示了从**规则驱动 (Rule-based)** 到**数据驱动 (Data-driven)** 的范式转变。
    7
    8 ## 🎯 核心特性 (Key Features)
    9 1. **零延迟通信架构**: 
   10    - ESP32 固件采用了“贪婪消费者 (Greedy Consumer)”模式的自定义高速串口协议。
   11    - 彻底解决了传统流控中常见的“缓冲区膨胀 (Buffer Bloat)”导致的秒级延迟问题，实现了 30Hz 的无缝视觉伺服跟随。
   12 2. **直观的意图映射 (Fist-to-Curl)**:
   13    - 抛弃了反直觉的坐标映射，创新性地采用“握拳开合度 (Fist Degree)”作为控制核心。
   14    - 手掌完全张开时，机械臂自动回零 (2048位) 保持绝对竖直；手掌握紧时，机械臂平滑卷曲 180 度。
   15 3. **端到端深度学习 (End-to-End Deep Learning)**:
   16    - 支持抛弃中间件 (MediaPipe)，直接使用轻量级卷积神经网络 (ResNet18) 将原始摄像头像素翻译为 3 个关节角度。
   17
   18 ## 📂 目录结构 (Directory Structure)
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

## 🚀 运行指南 (How to Run)
```
   1 ### 阶段 1：底层测试与固件烧录
   2 使用 PlatformIO 将 `arm/` 目录下的代码烧录至 ESP32。
   3
   4 ### 阶段 2：自动化数据采集
   5 确保摄像头和串口已连接。运行采集脚本，在镜头前演示从张开到握拳的各种姿态，按下 `Space` 键开始/停止录制。
  python3 scripts/collect_data.py

   1
   2 ### 阶段 3：神经网络训练
   3 当 `data/` 目录下收集到数千张图片后，启动 PyTorch 训练程序。
  python3 train/train.py

    1 训练结束后，最佳模型权重将保存为 `train/best_model.pth`。
    2
    3 ### 阶段 4：纯视觉推理部署 (ROS2)
    4 加载训练好的 `.pth` 模型，不再依赖 MediaPipe 提取骨架，直接将摄像头画面输入 CNN 获得机械臂控制角度，实现端到端的 AI 意图解析。
    5
    6 ## 🛠️ 技术栈 (Tech Stack)
    7 - **硬件**: ESP32, 3x STS Bus Servos, USB Camera
    8 - **下位机**: C++, PlatformIO, Arduino Framework
    9 - **视觉处理**: OpenCV, MediaPipe
   10 - **机器学习**: PyTorch, TorchVision (ResNet18)
