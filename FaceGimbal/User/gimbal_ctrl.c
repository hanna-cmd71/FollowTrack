#include "gimbal_ctrl.h"
#include "protocol.h"
#include "PID.h"
#include "Servo.h"
#include <math.h>

#define YAW_START 80.0f
#define PITCH_START 120.0f
#define TIMEOUT_THRESHOLD 50

// 全局变量
float filtered_dx = 0.0f;
float filtered_dy = 0.0f;
float yaw_adj = 0.0f;
float pitch_adj = 0.0f;
const float alpha = 0.40f; 

uint32_t s_timeout_counter = 0; 
uint8_t g_current_mode = MODE_TRACK;  

// 内部状态维护
static float s_wiggle_phase = 0.0f;
static uint8_t s_last_run_mode = 0xFF;

void Gimbal_Control_Loop(void)
{
    VisionPacket_t v;
    
    if(Protocol_Update(&v)) {
        s_timeout_counter = 0;
        
        // 【防突跳】：模式切换时清理积分项
        if (v.mode != s_last_run_mode) {
            PID_clear(&pid_yaw);
            PID_clear(&pid_pitch);
            if (v.mode == 0x04) s_wiggle_phase = 0.0f;
        }
        s_last_run_mode = v.mode;
        g_current_mode = v.mode;

        switch(g_current_mode) {
            
            case 0x04: { // Happy模式：禁用PID，强制正弦摆动
                s_wiggle_phase += 0.2f; 
                float wiggle = 8.0f * sinf(s_wiggle_phase);
                
                Set_Angle(&servo_yaw, YAW_START + wiggle); 
                Set_Angle(&servo_pitch, PITCH_START);
                
                if (s_wiggle_phase > 12.56f) s_wiggle_phase = 0.0f;
                break;
            }
                
            case 0x05: { // Panic模式
                Set_Angle(&servo_yaw, YAW_START + ((v.x_offset > 0) ? -20.0f : 20.0f));
                Set_Angle(&servo_pitch, PITCH_START + 15.0f);
                break;
            }

            case MODE_TRACK: { // 追踪模式
                filtered_dx = alpha * (float)v.x_offset + (1.0f - alpha) * filtered_dx;
                filtered_dy = alpha * (float)v.y_offset + (1.0f - alpha) * filtered_dy;
                
                yaw_adj = PID_caluate(&pid_yaw, 0, filtered_dx);
                pitch_adj = PID_caluate(&pid_pitch, 0, filtered_dy);
                
                /* 【核心修正点】：
                   如果云台追踪方向反了，请在这里将下面的 `-` 改为 `+`
                   或者将 `+` 改为 `-`。根据实际测试结果，二选一。 */
                Set_Angle(&servo_yaw, servo_yaw.current_Angle - yaw_adj);
                Set_Angle(&servo_pitch, servo_pitch.current_Angle - pitch_adj);
                break;
            }
            
            case MODE_HOME: { // 归位模式
                float yaw_err = YAW_START - servo_yaw.current_Angle;
                float pitch_err = PITCH_START - servo_pitch.current_Angle;
                
                // 使用比例归位，平滑回到中心
                Set_Angle(&servo_yaw, servo_yaw.current_Angle + (yaw_err * 0.05f));
                Set_Angle(&servo_pitch, servo_pitch.current_Angle + (pitch_err * 0.05f));
                break;
            }
                
            case MODE_LOCK: { // 锁定模式
                PID_clear(&pid_yaw);
                PID_clear(&pid_pitch);
                break;
            }
                
            default:
                break;
        }
    }
    else {
        s_timeout_counter++;
    }
}
