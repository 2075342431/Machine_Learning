#include <Arduino.h>
#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <sensor_msgs/msg/joint_state.h>
#include "RobotArm.h"

#define USE_MICROROS 1

RobotArm arm(24.0, 62.0, 40.0, 20.0);

#if USE_MICROROS
// ... micro-ros headers and vars ... (kept for compatibility)
rcl_subscription_t subscriber;
sensor_msgs__msg__JointState joint_msg;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

// 消息缓冲区
double pos_data[6];
rosidl_runtime_c__String name_data[6];
char name_buffers[6][20];

// 接收关节指令
void subscription_callback(const void *msgin)
{
    const sensor_msgs__msg__JointState *msg = (const sensor_msgs__msg__JointState *)msgin;

    double j1 = 0, j2 = 0, j3 = 0;
    bool got1 = false, got2 = false, got3 = false;

    for (uint32_t i = 0; i < msg->name.size; i++)
    {
        if (!strcmp(msg->name.data[i].data, "Joint1"))
        {
            j1 = msg->position.data[i];
            got1 = true;
        }
        if (!strcmp(msg->name.data[i].data, "Joint2"))
        {
            j2 = msg->position.data[i];
            got2 = true;
        }
        if (!strcmp(msg->name.data[i].data, "Joint3"))
        {
            j3 = msg->position.data[i];
            got3 = true;
        }
    }

    if (got1 && got2 && got3)
    {
        // 严格按照你原来的格式：[0, j1, j2, j3]
        double rads[4] = {0.0, j1, j2, j3};
        arm.setJoints(rads, 4);
    }
}
#endif

// 增强型串口解析：只保留最新的完整帧
void handle_custom_serial_fast() {
    static uint8_t buffer[15];
    static int index = 0;
    bool found_new_frame = false;
    float latest_angles[3];

    // 【核心优化】只要串口有数据，就一直读到空为止
    while (Serial.available() > 0) {
        uint8_t c = Serial.read();
        
        if (index == 0 && c != 0xFF) continue;
        buffer[index++] = c;

        if (index == 15) {
            if (buffer[14] == 0xFE) {
                uint8_t sum = 0;
                for (int i = 1; i < 13; i++) sum += buffer[i];
                if (sum == buffer[13]) {
                    // 解析出角度，但先不执行，存入临时变量
                    memcpy(latest_angles, &buffer[1], 12);
                    found_new_frame = true; 
                }
            }
            index = 0;
        }
    }

    // 【核心优化】读完缓冲区所有内容后，只执行最后一帧
    if (found_new_frame) {
        double rads[4] = {0.0, (double)latest_angles[0], (double)latest_angles[1], (double)latest_angles[2]};
        arm.setJoints(rads, 4);
        // 回传一个心跳，告诉上位机我已经清空了一次缓冲区
        Serial.write(0x06);
    }
}

void setup() {
    Serial.begin(921600);
    set_microros_serial_transports(Serial);
    // 关键：将 ESP32 串口缓冲区调大，或者通过读取逻辑快速清空
    arm.begin();
    arm.goHome();

#if USE_MICROROS
    // 初始化消息
    joint_msg.position.data = pos_data;
    joint_msg.position.capacity = 6;
    joint_msg.name.data = name_data;
    joint_msg.name.capacity = 6;
    for (int i = 0; i < 6; i++)
    {
        joint_msg.name.data[i].data = name_buffers[i];
        joint_msg.name.data[i].capacity = 20;
    }

    allocator = rcl_get_default_allocator();
    rclc_support_init(&support, 0, NULL, &allocator);
    rclc_node_init_default(&node, "arm_node", "", &support);

    rclc_subscription_init_default(
        &subscriber,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
        "joint_states");

    rclc_executor_init(&executor, &support.context, 1, &allocator);
    rclc_executor_add_subscription(&executor, &subscriber, &joint_msg, &subscription_callback, ON_NEW_DATA);
#endif
}

void loop()
{
#if USE_MICROROS
    rclc_executor_spin_some(&executor, RCL_MS_TO_NS(1));
#else
    handle_custom_serial_fast();
#endif
}
