#ifndef __SERVO_H__
#define __SERVO_H__

#include "main.h"
#include <math.h>

typedef struct
{
    TIM_HandleTypeDef* htim;   
    uint32_t channel;          
    float current_Angle;       
    float target_Angle;                      
    float minAngle;            
    float maxAngle;            
    uint32_t minPulse;         
    uint32_t maxPulse;         
} Servo_t;
// 初始化舵机
extern void Servo_Init(Servo_t* servo, TIM_HandleTypeDef* htim, uint32_t channel, float minAngle, float maxAngle);
// 设置舵机目标角度
extern void Set_Angle(Servo_t* servo, float target);



#endif
