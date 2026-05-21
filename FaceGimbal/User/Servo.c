#include "servo.h"
//80度初始位置
//yaw限位0-180
//pitch限位40-180
void Servo_Init(Servo_t* servo, TIM_HandleTypeDef* htim, uint32_t channel, 
                float minAngle, float maxAngle) 
{
    servo->htim = htim;
    servo->channel = channel;
    
    
    servo->minAngle = minAngle;
    servo->maxAngle = maxAngle;
    servo->minPulse = 50;  
    servo->maxPulse = 250; 
    servo->current_Angle =180.0f;

    HAL_TIM_PWM_Start(servo->htim, servo->channel);

}

void Set_Angle(Servo_t* servo, float target) 
{
    if (target < servo->minAngle) target = servo->minAngle;
    if (target > servo->maxAngle) target = servo->maxAngle;
    servo->target_Angle = target;
    servo->current_Angle = target;
    //Pulse = MinP + (CurrentA - MinA) * (MaxP - MinP) / (MaxA - MinA)
    float pulse_float = (float)servo->minPulse + (servo->current_Angle - servo->minAngle) * (float)(servo->maxPulse - servo->minPulse) / (servo->maxAngle - servo->minAngle);
    uint32_t CCR_val = (uint32_t)roundf(pulse_float);
    __HAL_TIM_SET_COMPARE(servo->htim, servo->channel, CCR_val);
}




