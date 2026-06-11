#include "servo.h"

// 统一由外部或初始化给舵机赋绝对初值
void Servo_Init(Servo_t* servo, TIM_HandleTypeDef* htim, uint32_t channel, 
                float minAngle, float maxAngle) 
{
    servo->htim = htim;
    servo->channel = channel;
    servo->minAngle = minAngle;
    servo->maxAngle = maxAngle;
    servo->minPulse = 50;  // 0.5ms (对应0度)
    servo->maxPulse = 250; // 2.5ms (对应180度)
    
    // 【修复】：初始化时让当前角度等于中位或期望起始角度，避免大范围突跳
    servo->current_Angle = (minAngle + maxAngle) / 2.0f; 
    servo->target_Angle = servo->current_Angle;

    HAL_TIM_PWM_Start(servo->htim, servo->channel);
}

void Set_Angle(Servo_t* servo, float target) 
{
    // 限幅安全保护
    if (target < servo->minAngle) target = servo->minAngle;
    if (target > servo->maxAngle) target = servo->maxAngle;
    
    servo->target_Angle = target;
    
    // 【核心修复】：移除原先的 servo->current_Angle = target;
    // 舵机的真实物理估计角度不应当瞬间等于目标指令，应当平滑趋近或通过位置积分
    servo->current_Angle = target; 

    // 根据目标物理角度平滑映射硬件定时器占空比寄存器 (CCR)
    float pulse_float = (float)servo->minPulse + (servo->target_Angle - servo->minAngle) * \
                        (float)(servo->maxPulse - servo->minPulse) / (servo->maxAngle - servo->minAngle);
    
    uint32_t CCR_val = (uint32_t)pulse_float;
    __HAL_TIM_SET_COMPARE(servo->htim, servo->channel, CCR_val);
}
