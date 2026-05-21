#include "main.h"
#include "vofa.h"
#include "string.h"
#include "usart.h"

void VOFA_JustFloat(float *data, uint8_t num) {
    
    static uint8_t send_buf[32]; 
    uint8_t data_len = num * sizeof(float);
    
   
    memcpy(send_buf, (uint8_t *)data, data_len);
    
    //0x00 0x00 0x80 0x7F
    send_buf[data_len] = 0x00;
    send_buf[data_len+1] = 0x00;
    send_buf[data_len+2] = 0x80;
    send_buf[data_len+3] = 0x7F;
    
    
    HAL_UART_Transmit(&huart2, send_buf, data_len + 4, 10);
}
