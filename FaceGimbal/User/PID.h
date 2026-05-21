#ifndef __PID_H__
#define __PID_H__
#include "main.h"
enum PID_MODE
{
		PID_POSITION = 0,
		PID_DELTA
};

typedef struct 
{
	uint8_t mode;
	float Kp;
	float Ki;
	float Kd;
	
	float max_out;
	float max_iout;
	
	float set;
	float fdb;
	
	float out;
  float Pout;
  float Iout;
  float Dout;
  float Dbuf[3];  
  float error[3]; 
}PID_t;

extern void PID_init(PID_t *pid, uint8_t mode, float PID[3], float max_out, float max_iout);
extern float PID_caluate(PID_t *pid, float ref, float set);
extern void PID_clear(PID_t *pid);

#endif
