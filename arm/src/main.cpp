#include <micro_ros_platformio.h>
#include <Arduino.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <sensor_msgs/msg/joint_state.h>
#include "RobotArm.h"

// 实例化机械臂对象 (底座24, 大臂62, 小臂40, 末端20)
RobotArm arm(24.0, 62.0, 40.0, 20.0);

// micro-ROS 变量
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
    
    // 临时存储排序后的关节角度
    double ordered_pos[4] = {0.0, 0.0, 0.0, 0.0};
    bool joint_found[4] = {false, false, false, false};

    // 遍历消息中的关节名称，匹配到对应的索引
    for (uint32_t i = 0; i < msg_in->name.size; i++) {
        const char* name = msg_in->name.data[i].data;
        if (strcmp(name, "Joint1") == 0) {
            ordered_pos[0] = msg_in->position.data[i];
            joint_found[0] = true;
        } else if (strcmp(name, "Joint2") == 0) {
            ordered_pos[1] = msg_in->position.data[i];
            joint_found[1] = true;
        } else if (strcmp(name, "Joint3") == 0) {
            ordered_pos[2] = msg_in->position.data[i];
            joint_found[2] = true;
        } else if (strcmp(name, "Joint4") == 0) {
            ordered_pos[3] = msg_in->position.data[i];
            joint_found[3] = true;
        }
    }

    // 只有当接收到完整的 4 个关节数据时才执行控制命令
    if (joint_found[0] && joint_found[1] && joint_found[2] && joint_found[3]) {
        arm.setJoints(ordered_pos, 4);
    }
}

void setup() {
    Serial.begin(921600);
    set_microros_serial_transports(Serial);

    // 初始化机械臂
    arm.begin();
    arm.goHome();

    // micro-ROS 内存预分配
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
}

void loop() {
    rclc_executor_spin_some(&executor, RCL_MS_TO_NS(1));
}
