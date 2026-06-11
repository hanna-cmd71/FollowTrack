#include "gimbal_ctrl.h"
#include "protocol.h"
#include "PID.h"
#include "Servo.h"

#define YAW_START 80.0f
#define PITCH_START 120.0f
#define TIMEOUT_THRESHOLD 50

float filtered_dx = 0.0f;
float filtered_dy = 0.0f;
float yaw_adj = 0.0f;
float pitch_adj = 0.0f;
const float alpha = 0.40f; 

// ======= 【修复核心：定义供 OLED 使用的全局控制链变量】 =======
uint32_t s_timeout_counter = 0; // 删除了 static，使其变为全局变量
uint8_t g_current_mode = 0x02;  // 开机默认初始化为 MODE_LOCK (0x02)

void Gimbal_Control_Loop(void)
{
    VisionPacket_t v;
    if(Protocol_Update(&v)){
        s_timeout_counter = 0;
        
        // ======= 【关键同步】：把协议解析出来的实际模式实时同步给全局变量 =======
        g_current_mode = v.mode; 
        
        switch(v.mode){
            case MODE_TRACK: 
                filtered_dx = alpha * (float)v.x_offset + (1.0f - alpha) * filtered_dx;
                filtered_dy = alpha * (float)v.y_offset + (1.0f - alpha) * filtered_dy;
                
                if (fabsf(filtered_dx) < 1.0f) filtered_dx = 0.0f;
                if (fabsf(filtered_dy) < 1.0f) filtered_dy = 0.0f;
                
                yaw_adj = PID_caluate(&pid_yaw, filtered_dx, 0.0f);
                pitch_adj = PID_caluate(&pid_pitch, filtered_dy, 0.0f);
                
                Set_Angle(&servo_yaw, servo_yaw.current_Angle + yaw_adj);
                Set_Angle(&servo_pitch, servo_pitch.current_Angle + pitch_adj);
                break;
            
            case MODE_LOCK:
                PID_clear(&pid_yaw);
                PID_clear(&pid_pitch);
                break;
            
            case MODE_HOME:
                if (fabsf(servo_yaw.current_Angle - YAW_START) > 1.0f) {
                    float dir = (servo_yaw.current_Angle > YAW_START) ? -0.5f : 0.5f;
                    Set_Angle(&servo_yaw, servo_yaw.current_Angle + dir);
                } else {
                    Set_Angle(&servo_yaw, YAW_START);
                }
                
                if (fabsf(servo_pitch.current_Angle - PITCH_START) > 1.0f) {
                    float dir = (servo_pitch.current_Angle > PITCH_START) ? -0.5f : 0.5f;
                    Set_Angle(&servo_pitch, servo_pitch.current_Angle + dir);
                } else {
                    Set_Angle(&servo_pitch, PITCH_START);
                }
                break;
                
            default:
                break;
        }
    }
    else {
        s_timeout_counter++;
        if(s_timeout_counter > TIMEOUT_THRESHOLD) {
            s_timeout_counter = TIMEOUT_THRESHOLD;
            
            // ======= 【关键同步】：链路超时后，模式强制变更为回中或锁定，让 OLED 显示闭眼/眯眼 =======
            g_current_mode = MODE_LOCK; 
            
            PID_clear(&pid_yaw);
            PID_clear(&pid_pitch);
        }
    }
}
