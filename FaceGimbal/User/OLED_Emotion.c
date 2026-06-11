#include "OLED_Emotion.h"
#include "OLED_Function.h"
#include "OLED_IIC_Config.h"
#include "protocol.h"

/* 引入全局控制链变量 (已在 gimbal_ctrl.c 中定义) */
extern uint32_t s_timeout_counter;
extern uint8_t g_current_mode;

/**
 * @brief 在显存缓冲区快速绘制一个实心矩形（加入最高级别的物理内存越界保护）
 */
static void OLED_DrawFilledRect(int x, int y, int w, int h, uint8_t color) 
{
    // 严格限幅：你的 ScreenBuffer 大小是 [8][128]
    int start_x = (x < 0) ? 0 : (x >= 128 ? 127 : x);
    int end_x   = (x + w < 0) ? 0 : (x + w > 128 ? 128 : x + w);
    int start_y = (y < 0) ? 0 : (y >= 64 ? 63 : y);
    int end_y   = (y + h < 0) ? 0 : (y + h > 64 ? 64 : y + h);

    for (int i = start_x; i < end_x; i++) {
        for (int j = start_y; j < end_y; j++) {
            OLED_SetPixel(i, j, color); 
        }
    }
}

/* ==================== 像素几何眼造型库 ==================== */
static void Draw_Eye_Normal(void) 
{
    OLED_DrawFilledRect(28, 20, 18, 26, 1); 
    OLED_DrawFilledRect(82, 20, 18, 26, 1); 
}

static void Draw_Eye_Closed(void) 
{
    OLED_DrawFilledRect(24, 32, 24, 4, 1);  
    OLED_DrawFilledRect(80, 32, 24, 4, 1);  
}

static void Draw_Eye_Focus(void) 
{
    OLED_DrawFilledRect(28, 20, 18, 26, 1);
    OLED_DrawFilledRect(30, 22, 14, 22, 0);
    OLED_DrawFilledRect(35, 29, 4, 8, 1);    
    
    OLED_DrawFilledRect(82, 20, 18, 26, 1);
    OLED_DrawFilledRect(84, 22, 14, 22, 0);
    OLED_DrawFilledRect(89, 29, 4, 8, 1);    
}

static void Draw_Eye_Smile(void) 
{
    OLED_DrawFilledRect(22, 34, 8, 4, 1);
    OLED_DrawFilledRect(28, 28, 8, 4, 1);
    OLED_DrawFilledRect(34, 34, 8, 4, 1);
    
    OLED_DrawFilledRect(72, 34, 8, 4, 1);
    OLED_DrawFilledRect(78, 28, 8, 4, 1);
    OLED_DrawFilledRect(84, 34, 8, 4, 1);
}

static void Draw_Eye_Panic(void)
{
    OLED_DrawFilledRect(24, 16, 26, 32, 1);
    OLED_DrawFilledRect(26, 18, 22, 28, 0);
    OLED_DrawFilledRect(35, 30, 4, 4, 1);
    
    OLED_DrawFilledRect(78, 16, 26, 32, 1);
    OLED_DrawFilledRect(89, 30, 4, 4, 1);
}

/**
 * @brief 表情系统初始化
 */
void Robot_Emotion_Init(void)
{
    OLED_ON();          // 发送 0xAF 唤醒 SSD1306 硬件面板
    OLED_ClearRAM();    // 彻底排空显存
    Draw_Eye_Normal();  // 开机强制塞入大眼睛，给用户亮屏反馈
    OLED_RefreshRAM();  // 强行推向物理屏幕
}

/**
 * @brief 表情状态机核心更新函数
 */
void Robot_Emotion_Update(void)
{
    static uint32_t blink_timer = 0;
    static uint8_t is_blinking = 0;

    // 1. 优先度判断：无视指令，如果超时直接画一条线睡觉
    if (s_timeout_counter >= 50)  
    {
        OLED_ClearRAM();
        Draw_Eye_Closed();
        OLED_RefreshRAM();
        return;
    }

    // 2. 清空当前缓冲区
    OLED_ClearRAM(); 

    // 3. 跨模态决策树并轨映射
    switch (g_current_mode) 
    {
        case 0x01: // MODE_TRACK (YOLO人脸追踪)
            Draw_Eye_Focus(); 
            break;
            
        case 0x04: // 愉快互动
            Draw_Eye_Smile(); 
            break;
            
        case 0x05: // Panic 应激
            Draw_Eye_Panic(); 
            break;
            
        case 0x03: // MODE_HOME
            Draw_Eye_Closed(); 
            break;
            
        case 0x02: // MODE_LOCK
        default:   
            /* 智能仿生眨眼时序 */
            if (!is_blinking) 
            {
                if (HAL_GetTick() - blink_timer > 4000) {
                    is_blinking = 1;
                    blink_timer = HAL_GetTick();
                }
                Draw_Eye_Normal(); 
            } 
            else 
            {
                if (HAL_GetTick() - blink_timer > 120) {
                    is_blinking = 0;
                    blink_timer = HAL_GetTick();
                }
                Draw_Eye_Closed(); 
            }
            break;
    }

    // 4. 将最终帧送入硬件物理屏幕
    OLED_RefreshRAM(); 
}
