#ifndef __PROTOCOL_H_
#define __PROTOCOL_H_

#include "main.h"

// 接收缓冲区大小
#define PROTOCOL_RX_BUF_SIZE 128
typedef enum {
	MODE_IDLE = 0x00,
	MODE_TRACK = 0x01,
	MODE_LOCK = 0x02,
	MODE_HOME = 0x03,
	MODE_HAPPY = 0x04,
	MODE_PANIC = 0x05

}GimbalMode_t;

typedef struct {
  uint8_t header;    // 固定 0x5A
	uint8_t mode;
  int16_t x_offset;  
  int16_t y_offset;  
  uint8_t tail;      // 固定 0xED
} __attribute__((packed))VisionPacket_t;
/**
 * @brief 初始化协议模块
 *
 * @param huart 串口句柄
 */
void Protocol_Init(UART_HandleTypeDef* huart);
void Protocol_IdleHandler(UART_HandleTypeDef* huart);
uint8_t Protocol_Update(VisionPacket_t* out_packet);

#endif  
