/**
 * ************************************************************************
 * 
 * @file OLED_IIC_Config.c
 * @author zxr
 * @brief IIC??????OLED???????
 * 
 * ************************************************************************
 * @copyright Copyright (c) 2024 zxr 
 * ************************************************************************
 */
#include "OLED_IIC_Config.h"
#include "i2c.h"


unsigned char  ScreenBuffer[SCREEN_PAGE_NUM][SCREEN_COLUMN];//?????????



/**
* @brief  ?OLED????????byte???
* @param  addr:?????
* @param  data:??????
* @retval ?
*/
void I2C_WriteByte(uint8_t addr, uint8_t data)
{
	extern I2C_HandleTypeDef hi2c2;
	HAL_I2C_Mem_Write(&hi2c2, OLED_ADDRESS, addr, I2C_MEMADD_SIZE_8BIT, &data, 1, 10);
}

/**
 * ************************************************************************
 * @brief ?????
 * @param[in] cmd  ?????
 * ************************************************************************
 */
void WriteCmd(unsigned char cmd)
{
	I2C_WriteByte(0x00, cmd);
}

/**
 * ************************************************************************
 * @brief ?????
 * @param[in] dat  ?????
 * ************************************************************************
 */
void WriteDat(unsigned char dat)
{
	I2C_WriteByte(0x40, dat);
}

/**
 * ************************************************************************
 * @brief ??OLED
 * ************************************************************************
 */
void OLED_ON(void)
{
	WriteCmd(0X8D);  //?????
	WriteCmd(0X14);  //?????
	WriteCmd(0XAF);  //OLED??
}

/**
 * ************************************************************************
 * @brief ??OLED
 * ************************************************************************
 */
void OLED_OFF(void)
{
	WriteCmd(0X8D);  //?????
	WriteCmd(0X10);  //?????
	WriteCmd(0XAE);  //OLED??
}

/**
 * ************************************************************************
 * @brief OLED????
 * ************************************************************************
 */
void OLED_CLS(void)//??
{
	unsigned char m,n;
	for(m=0;m<8;m++)
	{
		WriteCmd(0xb0+m);	//page0-page1
		WriteCmd(0x00);		//low column start address
		WriteCmd(0x10);		//high column start address
		for(n=0;n<128;n++)
		{
			WriteDat(0x00);
		}
	}
}

/**
 * ************************************************************************
 * @brief OLED?????
 * ************************************************************************
 */
void OLED_Init(void)
{
	WriteCmd(0xAE); //????
	WriteCmd(0x20);	//????????
	WriteCmd(0x10);	
	WriteCmd(0xb0);	//?????????????,0-7
	WriteCmd(0xc8);	//??COM??????
	WriteCmd(0x00); //-??????
	WriteCmd(0x10); //-??????
	WriteCmd(0x40); //-???????
	WriteCmd(0x81); //??????????
	WriteCmd(0xff); //???? 0x00~0xff
	WriteCmd(0xa1); //???????0?127
	WriteCmd(0xa6); //??????
	WriteCmd(0xa8); 
	WriteCmd(0x3F); //
	WriteCmd(0xa4); //0xa4,????RAM??;0xa5,????RAM??
	WriteCmd(0xd3); //??????
	WriteCmd(0x00); //???
	WriteCmd(0xd5); //--set display clock divide ratio/oscillator frequency
	WriteCmd(0xf0); //--set divide ratio
	WriteCmd(0xd9); //--set pre-charge period
	WriteCmd(0x22); //
	WriteCmd(0xda); //--set com pins hardware configuration
	WriteCmd(0x12);
	WriteCmd(0xdb); //--set vcomh
	WriteCmd(0x20); //0x20,0.77xVcc
	WriteCmd(0x8d); //??DC-DC??
	WriteCmd(0x14); //
	WriteCmd(0xaf); //--turn on oled panel
	OLED_CLS();
}

/**
 * ************************************************************************
 * @brief ???????
 * ************************************************************************
 */
void OLED_RefreshRAM(void)
{
    // 【终极时序调优】：只刷新 Page 2 ~ Page 5 (对应垂直 Y 轴 16 到 48 像素区间，这是眼睛的主要活动带)
    // 顶部的 Page 0,1 和底部的 Page 6,7 极少变动，开机刷清一次即可，日常不参与高频循环刷新
    for(unsigned short int m = 2; m <= 5; m++)
    {
        WriteCmd(0xb0 + m); // 设置页地址
        WriteCmd(0x00);     // 设置列低地址
        WriteCmd(0x10);     // 设置列高地址
        
        // 采用高速连续内存传输或直接发送数据
        for(unsigned short int n = 0; n < SCREEN_COLUMN; n++)
        {
            WriteDat(ScreenBuffer[m][n]);
        }
    }
}

/**
 * ************************************************************************
 * @brief ???????
 * ************************************************************************
 */
void OLED_ClearRAM(void)
{
	for(unsigned short int m = 0; m < SCREEN_ROW/8; m++)
	{
		for(unsigned short int n = 0; n < SCREEN_COLUMN; n++)
		{
			ScreenBuffer[m][n] = 0x00;
		}
	}
}


void OLED_SetPixel(signed short int x, signed short int y, unsigned char set_pixel)
{ 
	if (x >= 0 && x < SCREEN_COLUMN && y >= 0 && y < SCREEN_ROW) {
		if(set_pixel){
				ScreenBuffer[y/8][x] |= (0x01 << (y%8));
		}  
		else{
				ScreenBuffer[y/8][x] &= ~(0x01 << (y%8));
		}
	}
}

/**
 * ************************************************************************
 * @brief ????????
 * 
 * @param[in] mode  ??
 * 					?	ON	0xA7	????
 *  				?	OFF	0xA6	?????,??????
 * 
 * ************************************************************************
 */
void OLED_DisplayMode(unsigned char mode)
{
	WriteCmd(mode);
}


void OLED_IntensityControl(unsigned char intensity)
{
	WriteCmd(0x81);
	WriteCmd(intensity);
}

void OLED_Shift(unsigned char shift_num)
{
	for(unsigned char i = 0; i < shift_num; i++)
		{
			WriteCmd(0xd3);//??????,??????
			WriteCmd(i);//???
			HAL_Delay(10);//????
		}
}

void OLED_HorizontalShift(unsigned char start_page,unsigned char end_page,unsigned char direction)
{
	WriteCmd(0x2e);  //????

	WriteCmd(direction);//??????
	WriteCmd(0x00);//??????,???0x00
	WriteCmd(start_page);//???????
	WriteCmd(0x05);//??????????????????
	WriteCmd(end_page);//???????
	WriteCmd(0x00);//??????,???0x00
	WriteCmd(0xff);//??????,???0xff

	WriteCmd(0x2f);
}
