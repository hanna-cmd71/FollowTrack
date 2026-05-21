#include "main.h"
#include "pid.h"
#include "math.h"

#define LimitMax(input, max)   \
    {                          \
        if (input > max)       \
        {                      \
            input = max;       \
        }                      \
        else if (input < -max) \
        {                      \
            input = -max;      \
        }                      \
    }
void PID_init(PID_t *pid, uint8_t mode, float PID[3], float max_out, float max_iout)
{
	if(pid == NULL || PID == NULL)
	{
		return;
	}
	pid->mode = mode;
	pid->Kp = PID[0];
	pid->Ki = PID[1];
	pid->Kd = PID[2];
	pid->max_out = max_out;
	pid->max_iout = max_iout;
	pid->Dbuf[0] = pid->Dbuf[1] = pid->Dbuf[2] = 0.0f;
	pid->error[0] = pid->error[1] = pid->error[2] = pid->Pout = pid->Iout = pid->Dout = 0.0f;
}

float PID_caluate(PID_t *pid, float ref, float set)
{
	if(pid == NULL )
	{
		return 0.0f;
	}
	pid->error[2] = pid->error[1];
	pid->error[1] = pid->error[0];
	pid->set = set;
	pid->fdb = ref;
	pid->error[0] = set - ref;
	if (pid->mode == PID_POSITION)
  {
     pid->Pout = pid->Kp * pid->error[0];
     pid->Iout += pid->Ki * pid->error[0];
     pid->Dbuf[2] = pid->Dbuf[1];
     pid->Dbuf[1] = pid->Dbuf[0];
     pid->Dbuf[0] = (pid->error[0] - pid->error[1]);
     pid->Dout = pid->Kd * pid->Dbuf[0];
     LimitMax(pid->Iout, pid->max_iout);
     pid->out = pid->Pout + pid->Iout + pid->Dout;
     LimitMax(pid->out, pid->max_out);
	}
	else if (pid->mode == PID_DELTA)
  {
      pid->Pout = pid->Kp * (pid->error[0] - pid->error[1]);
      pid->Iout = pid->Ki * pid->error[0];
      pid->Dbuf[2] = pid->Dbuf[1];
      pid->Dbuf[1] = pid->Dbuf[0];
      pid->Dbuf[0] = (pid->error[0] - 2.0f * pid->error[1] + pid->error[2]);
      pid->Dout = pid->Kd * pid->Dbuf[0];
      pid->out += pid->Pout + pid->Iout + pid->Dout;
  		LimitMax(pid->out, pid->max_out);
  }
    return pid->out;
}

void PID_clear(PID_t *pid)
{
    if (pid == NULL)
    {
        return;
    }

    pid->error[0] = pid->error[1] = pid->error[2] = 0.0f;
    pid->Dbuf[0] = pid->Dbuf[1] = pid->Dbuf[2] = 0.0f;
    pid->out = pid->Pout = pid->Iout = pid->Dout = 0.0f;
    pid->fdb = pid->set = 0.0f;
}	

