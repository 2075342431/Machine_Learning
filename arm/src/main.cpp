#include <Arduino.h>
#include "RobotArm.h"

// 设置为 0 使用自定义串口协议进行数据采集，设置为 1 使用 micro-ROS
#define USE_MICROROS 0

// 实例化机械臂对象 (底座24, 大臂62, 小臂40, 末端20)
RobotArm arm(24.0, 62.0, 40.0, 20.0);

#if USE_MICROROS
#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <sensor_msgs/msg/joint_state.h>

rcl_subscription_t subscriber;
sensor_msgs__msg__JointState msg;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

double pos_data[6];
rosidl_runtime_c__String name_data[6];
char name_buffers[6][20];

void subscription_callback(const void *msgin) {
    const sensor_msgs__msg__JointState *msg_in = (const sensor_msgs__msg__JointState *)msgin;
    double ordered_pos[4] = {0.0, 0.0, 0.0, 0.0};
    bool joint_found[4] = {false, false, false, false};

    for (uint32_t i = 0; i < msg_in->name.size; i++) {
        const char* name = msg_in->name.data[i].data;
        if (strcmp(name, "Joint1") == 0) { ordered_pos[0] = msg_in->position.data[i]; joint_found[0] = true; }
        else if (strcmp(name, "Joint2") == 0) { ordered_pos[1] = msg_in->position.data[i]; joint_found[1] = true; }
        else if (strcmp(name, "Joint3") == 0) { ordered_pos[2] = msg_in->position.data[i]; joint_found[2] = true; }
        else if (strcmp(name, "Joint4") == 0) { ordered_pos[3] = msg_in->position.data[i]; joint_found[3] = true; }
    }

    if (joint_found[0] && joint_found[1] && joint_found[2] && joint_found[3]) {
        arm.setJoints(ordered_pos, 4);
    }
}
#endif

// 自定义串口协议处理 (Phase 1 & 2)
// 帧格式: [0xFF, float1, float2, float3, checksum, 0xFE]
void handle_custom_serial() {
    static uint8_t buffer[15];
    static int index = 0;

    // 关键优化：循环读取所有可用字节，但只保留最近的一个完整帧
    while (Serial.available()) {
        uint8_t c = Serial.read();
        
        if (index == 0 && c != 0xFF) continue; 
        
        buffer[index++] = c;

        if (index == 15) {
            if (buffer[14] == 0xFE) {
                uint8_t sum = 0;
                for (int i = 1; i < 13; i++) sum += buffer[i];
                
                if (sum == buffer[13]) {
                    float angles[3];
                    memcpy(angles, &buffer[1], 12);

                    double rads[4] = {0.0, (double)angles[0], (double)angles[1], (double)angles[2]};
                    arm.setJoints(rads, 4);
                    
                    // 发送 ACK 信号告知上位机已处理完毕，可以发下一帧
                    Serial.write(0x06); 
                }
            }
            index = 0;
        }
    }
}

void setup() {
    // 提高波特率到 921600
    Serial.begin(921600);
    
    arm.begin();
    arm.goHome();

#if USE_MICROROS
    set_microros_serial_transports(Serial);
    // ... micro-ros init ...
    msg.position.data = pos_data;
    msg.position.capacity = 6;
    msg.name.data = name_data;
    msg.name.capacity = 6;
    for (int i = 0; i < 6; i++) {
        msg.name.data[i].data = name_buffers[i];
        msg.name.data[i].capacity = 20;
    }
    allocator = rcl_get_default_allocator();
    rclc_support_init(&support, 0, NULL, &allocator);
    rclc_node_init_default(&node, "micro_twin_arm", "", &support);
    rclc_subscription_init_default(&subscriber, &node,
                                   ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState), "joint_states");
    rclc_executor_init(&executor, &support.context, 1, &allocator);
    rclc_executor_add_subscription(&executor, &subscriber, &msg, &subscription_callback, ON_NEW_DATA);
#endif
}

void loop() {
#if USE_MICROROS
    rclc_executor_spin_some(&executor, RCL_MS_TO_NS(1));
#else
    handle_custom_serial();
#endif
}
