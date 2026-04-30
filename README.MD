# 机器学习：3轴机械臂视觉运动意图解析系统

## 1. Background & Motivation (背景与动机)
本项目旨在开发一个基于端到端深度学习的机械臂视觉伺服系统。通过摄像头捕捉人手运动特征，利用轻量级卷积神经网络 (CNN) 直接回归出机械臂三个关节的目标角度。

- **现状**：工作区已具备基于 micro-ROS 的 4 轴机械臂控制基础。
- **挑战**：micro-ROS 在高频率图像流下可能存在串口拥塞或延迟抖动。
- **策略**：采用**分阶段解耦开发**。前期通过纯串口协议打通底层控制与数据采集，后期再集成至 ROS2 分布式架构，确保数据链路的稳定性与模型的纯粹性。

## 2. Scope & Impact (范围与影响)

### 涉及模块
| 模块/文件 | 变更内容 |
| :--- | :--- |
| [arm/src/main.cpp](file:///home/kk/Desktop/Machine_Learning/arm/src/main.cpp) | 暂时屏蔽 micro-ROS 逻辑；新增自定义串口解析状态机；仅控制 ID 12, 14, 15 的 STS 总线舵机。 |
| `arm/lib/RobotArm/` | 保持基座 PWM 舵机固定；封装统一的舵机角度下发接口。 |
| `scripts/` | 新增串口测试、MediaPipe 数据采集、PyTorch 训练推理脚本。 |
| `ros2_nodes/` | (第四阶段) 新增相机节点、AI 推理节点，恢复 micro-ROS 订阅。 |

### 影响评估
- **代码结构**：新增 `data/`, `train/`, `models/` 目录，需配置 `.gitignore` 忽略大型二进制文件。
- **硬件行为**：ESP32 在前三个阶段表现为“透明串口透传+本地执行”，第四阶段恢复为 ROS2 从节点。

## 3. Proposed Solution (技术方案)

采用 **V-Model (验证与确认模型)** 迭代开发：
1. **底层联通**：建立可靠的 Serial 通信协议。
2. **数据闭环**：构建 `<Image, Joint_Angles>` 同步数据集。
3. **模型训练**：训练 ResNet18/MobileNetV2 骨干网络。
4. **系统集成**：ROS2 节点封装与实机部署。

## 4. Implementation Plan (实施计划)

### 第一阶段：硬件链路与底层通信打通 (预计 2-3 天)
**目标**：实现 Ubuntu <-> ESP32 的低延迟、无丢包串口控制。

- **Step 1.1 [固件修改]**:
  - 在 [arm/src/main.cpp](file:///home/kk/Desktop/Machine_Learning/arm/src/main.cpp) 中通过宏 `#ifdef USE_SERIAL_CONTROL` 隔离 micro-ROS 代码。
  - 实现非阻塞串口接收缓冲区。
- **Step 1.2 [协议定义]**:
  - 定义二进制帧格式：`Header(0xAA) | Len | Cmd | Data(Payload) | Checksum | Tail(0x55)`。
  - Payload 包含 3 个 `int16_t` 角度值（单位：0.1度），范围映射需明确。
- **Step 1.3 [执行逻辑]**:
  - 解析成功后，调用 [RobotArm](file:///home/kk/Desktop/Machine_Learning/arm/lib/RobotArm/RobotArm.h#L16-L49) 接口更新 ID 12, 14, 15 舵机位置。
  - 增加看门狗机制：若 500ms 未收到新指令，保持当前位置或进入安全姿态。
- **Step 1.4 [上位机测试]**:
  - 编写 `scripts/test_serial.py`，验证发送指令与机械臂动作的一致性及时延 (<50ms)。

### 第二阶段：自动化数据采集系统建立 (预计 3-4 天)
**目标**：构建高质量、带噪声鲁棒性的训练数据集。

- **Step 2.1 [采集脚本]**:
  - `scripts/collect_data.py` 整合 OpenCV (图像获取) 与 MediaPipe Hands (关键点提取)。
- **Step 2.2 [角度映射]**:
  - 将手部关键点 $(x,y,z)$ 映射为机械臂逆运动学 (IK) 解算的角度参考值。
  - **关键优化**：增加边界限制检查，剔除奇异点数据；允许用户通过键盘微调角度并重新保存标签。
- **Step 2.3 [同步录制]**:
  - 按下空格键开始录制：
    - 图像：保存为 `data/images/img_XXXX.png` (分辨率统一缩放至 $224 \times 224$ 或 $112 \times 112$)。
    - 标签：追加写入 `data/labels.csv`，格式为 `filename, angle_1, angle_2, angle_3`。
- **Step 2.4 [数据清洗]**:
  - 编写脚本检查 CSV 与图片文件数量一致性，剔除模糊或手部丢失的帧。

### 第三阶段：PyTorch 神经网络训练 (预计 4-5 天)
**目标**：训练端到端回归模型，最小化预测角度与真实角度的 MSE。

- **Step 3.1 [数据集构建]**:
  - `train/dataset.py`: 继承 `torch.utils.data.Dataset`。
  - **预处理**: Image -> ToTensor -> Normalize (ImageNet 均值方差); Angles -> MinMax Scaling to $[-1, 1]$。
  - **增强**: RandomRotation, ColorJitter, HorizontalFlip (需注意翻转后角度的对称变换逻辑)。
- **Step 3.2 [模型架构]**:
  - 骨干网: `torchvision.models.mobilenet_v2(pretrained=True)` (兼顾速度与精度)。
  - 头部: 替换 Classifier 为 `Linear(1280, 3)`，激活函数使用 `Tanh` (配合归一化标签) 或无激活直接输出。
- **Step 3.3 [训练策略]**:
  - `train/train.py`: 使用 `MSELoss` + `AdamW` 优化器。
  - 引入 `ReduceLROnPlateau` 动态调整学习率。
  - 监控验证集 Loss，使用 Early Stopping 防止过拟合。
- **Step 3.4 [模型导出]**:
  - 保存最佳权重 `.pth`，并尝试转换为 ONNX 格式以便后续可能的加速推理。

### 第四阶段：ROS2 分布式部署与实机测试 (预计 3-4 天)
**目标**：实现低延迟的视觉伺服控制闭环。

- **Step 4.1 [固件恢复]**:
  - 启用 micro-ROS，订阅 `/joint_states` 话题。
- **Step 4.2 [相机节点]**:
  - `camera_node.py`: 发布 `sensor_msgs/Image`，设置 QoS 为 `BEST_EFFORT` 以降低带宽压力。
- **Step 4.3 [推理节点]**:
  - `ai_inference_node.py`:
    - 订阅图像，执行预处理 -> 模型推理 -> 后处理 (反归一化)。
    - 发布 `sensor_msgs/JointState`，QoS 设置为 `RELIABLE`。
    - **平滑处理**: 引入简易卡尔曼滤波或滑动平均窗口，抑制预测抖动。
- **Step 4.4 [联调]**:
  - 使用 `rqt_graph` 监控节点连接。
  - 实测端到端延迟 (Camera -> AI -> Motor)，目标 < 100ms。

## 5. Verification (验证标准)

| 阶段 | 验证项 | 成功标准 |
| :--- | :--- | :--- |
| Phase 1 | 串口通信 | 连续发送 1000 次指令，无丢包，机械臂响应延迟 < 50ms。 |
| Phase 2 | 数据集质量 | 收集 > 5000 组有效样本；CSV 与图片一一对应；角度分布覆盖工作空间 80% 以上。 |
| Phase 3 | 模型性能 | 验证集 MSE < 0.01 (归一化空间)；单张推理时间 < 20ms (CPU/GPU)。 |
| Phase 4 | 系统联动 | 手掌移动时，机械臂跟随平滑，无明显震荡或滞后 (>200ms)。 |

## 6. Risks & Mitigation (风险与应对)

- **风险 1：光照变化影响模型泛化能力**。
  - *应对*：在数据采集阶段涵盖不同光照条件；训练时加强 ColorJitter 增强。
- **风险 2：串口通信干扰**。
  - *应对*：使用屏蔽线；在协议层增加 CRC 校验；固件端增加重试机制。
- **风险 3：推理速度不足**。
  - *应对*：若 Jetson/PC 性能不足，考虑使用 TensorRT 加速或更换更轻量模型 (ShuffleNet)。

## 7. Migration & Rollback (迁移与回滚)

- **分支管理**: 所有开发在 `feature/ml-vision-control` 分支进行。
- **配置隔离**: 通过 CMake options 或宏定义切换 Serial/ROS 模式，避免代码硬编码冲突。
- **数据备份**: 定期备份 `data/` 和 `models/` 到外部存储，不纳入 Git 版本控制。