#ifndef __GIMBAL_CTRL_H__
#define __GIMBAL_CTRL_H__

#include "PID.h"
#include "Servo.h"

extern PID_t pid_yaw;
extern PID_t pid_pitch;
extern Servo_t servo_yaw;
extern Servo_t servo_pitch;

void Gimbal_Control_Loop(void);

#endif 
