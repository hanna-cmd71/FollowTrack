#include "protocol.h"
#include <string.h>

static uint8_t g_rx_buffer[PROTOCOL_RX_BUF_SIZE];
static VisionPacket_t g_packet_temp;
static volatile uint8_t g_is_data_ready = 0;

void Protocol_Init(UART_HandleTypeDef* huart) {
    g_is_data_ready = 0;
    __HAL_UART_ENABLE_IT(huart, UART_IT_IDLE);
    HAL_UART_Receive_DMA(huart, g_rx_buffer, PROTOCOL_RX_BUF_SIZE);
}

void Protocol_IdleHandler(UART_HandleTypeDef* huart) {
    if (__HAL_UART_GET_FLAG(huart, UART_FLAG_IDLE) != RESET) {
        __HAL_UART_CLEAR_IDLEFLAG(huart);
        
        // 1. 停止当前 DMA 传输，计算收到的总物理字节数
        HAL_UART_DMAStop(huart);
        uint16_t current_len = PROTOCOL_RX_BUF_SIZE - __HAL_DMA_GET_COUNTER(huart->hdmarx);
        const size_t packet_size = sizeof(VisionPacket_t); // 7 字节

        // 2. 健壮性自适应检索：如果缓冲区积压了多帧，从后往前搜寻最新的一副有效物理包
        if (current_len >= packet_size) {
            for (int i = (int)current_len - (int)packet_size; i >= 0; i--) {
                // 扫描包头包尾边界
                if (g_rx_buffer[i] == 0x5A && g_rx_buffer[i + packet_size - 1] == 0xED) {
                    memcpy(&g_packet_temp, &g_rx_buffer[i], packet_size);
                    g_is_data_ready = 1; // 标记新数据就绪
                    break;               // 捕获到最新帧，立刻退出搜索
                }
            }
        }

        // 3. 彻底清空缓冲区，重新开启下一次高效 DMA 循环接收
        memset(g_rx_buffer, 0, PROTOCOL_RX_BUF_SIZE);
        HAL_UART_Receive_DMA(huart, g_rx_buffer, PROTOCOL_RX_BUF_SIZE);
    }
}

uint8_t Protocol_Update(VisionPacket_t* out_packet) {
    if (g_is_data_ready) {
        __disable_irq(); // 临界区保护，防止读取时被空闲中断改写
        memcpy(out_packet, &g_packet_temp, sizeof(VisionPacket_t));
        g_is_data_ready = 0;
        __enable_irq();
        return 1;
    }
    return 0;
}
