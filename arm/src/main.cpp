#include <Arduino.h>
#include "RobotArm.h"

#define USE_MICROROS 0

RobotArm arm(24.0, 62.0, 40.0, 20.0);

#if USE_MICROROS
// ... micro-ros headers and vars ... (kept for compatibility)
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
    // 关键：将 ESP32 串口缓冲区调大，或者通过读取逻辑快速清空
    arm.begin();
    arm.goHome();
}

void loop() {
#if USE_MICROROS
    // rclc_executor_spin_some...
#else
    handle_custom_serial_fast();
#endif
    // 严禁在此处添加任何 delay()
}
