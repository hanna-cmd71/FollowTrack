#include "protocol.h"
#include <string.h>

/// 协议模块实现
static uint8_t g_rx_buffer[PROTOCOL_RX_BUF_SIZE];
static VisionPacket_t g_packet_temp;
static volatile uint8_t g_is_data_ready = 0;
/**
 * @brief 初始化协议通信模块
 * 
 * 该函数用于初始化UART通信协议，配置DMA接收和空闲中断
 * 
 * @param huart 指向UART句柄结构体的指针，用于指定要初始化的UART外设
 * @return 无返回值
 */
void Protocol_Init(UART_HandleTypeDef* huart) {
  g_is_data_ready = 0;
  __HAL_UART_ENABLE_IT(huart, UART_IT_IDLE);
  HAL_UART_Receive_DMA(huart, g_rx_buffer, PROTOCOL_RX_BUF_SIZE);
}
/**
 * @brief UART空闲中断处理函数，用于处理接收完成的数据包
 * 
 * 该函数在UART检测到总线空闲时被调用，主要功能包括：
 * 1. 检测并清除空闲标志位
 * 2. 停止DMA传输并计算接收到的数据长度
 * 3. 验证数据包的完整性（长度、包头、包尾）
 * 4. 将有效的数据包复制到临时缓冲区
 * 5. 重新启动DMA接收
 * 
 * @param huart UART句柄指针，指向要处理的UART外设实例
 * @return 无返回值
 */
void Protocol_IdleHandler(UART_HandleTypeDef* huart) {
  if (__HAL_UART_GET_FLAG(huart, UART_FLAG_IDLE) != RESET) {
    __HAL_UART_CLEAR_IDLEFLAG(huart);
    HAL_UART_DMAStop(huart);

    uint16_t current_len = PROTOCOL_RX_BUF_SIZE - __HAL_DMA_GET_COUNTER(huart->hdmarx);
    const size_t packet_size = sizeof(VisionPacket_t);

    // 严格校验包长度、包头和包尾
    if (current_len == packet_size && 
        g_rx_buffer[0] == 0x5A && 
        g_rx_buffer[packet_size - 1] == 0xED) {
      memcpy(&g_packet_temp, g_rx_buffer, packet_size);
      g_is_data_ready = 1;
    }

    HAL_UART_Receive_DMA(huart, g_rx_buffer, PROTOCOL_RX_BUF_SIZE);
  }
}
/**
 * @brief 更新快照数据到输出包
 * 
 * 该函数将全局临时数据包复制到输出包中，并标记数据为已处理状态
 * 
 * @param[out] out_packet 指向VisionPacket结构体的指针，用于接收更新的数据快照
 * @return uint8_t 返回操作结果，1表示成功更新，0表示无可用数据
 */
uint8_t Protocol_Update(VisionPacket_t* out_packet) {
  if (g_is_data_ready) {
    memcpy(out_packet, &g_packet_temp, sizeof(VisionPacket_t));
    g_is_data_ready = 0;
    return 1;
  }
  return 0;
}
