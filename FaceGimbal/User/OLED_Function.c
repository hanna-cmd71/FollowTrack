#include "OLED_Function.h"
#include "OLED_Front.h"


void OLED_ShowStr(signed short int x, signed short int y, unsigned char ch[], unsigned char TextSize)
{ 
	if (x >= 0 && x < SCREEN_COLUMN && y >= 0 && y < SCREEN_ROW) 
	{
		int32_t c = 0;
		unsigned char j = 0;
	
		switch(TextSize)
		{
			case 1:
			{
				while(ch[j] != '\0')
				{
					c = ch[j] - 32;
					if(c < 0)	//????
						break;
					
					if(x >= 125 || (127-x < 6))//?????????:21????,????,??? || ?????6????????,????
					{
						x = 0;
						y += 8;//????
						if(63 - y < 8)	// ???????????
							break;
					}
					for(unsigned char m = 0; m < 6; m++)
					{
						for(unsigned char n = 0; n < 8; n++)
						{
							OLED_SetPixel(x+m, y+n, (F6x8[c][m] >> n) & 0x01);
						}
					}
					x += 6;
					j++;
				}
			}break;
			case 2:
			{
				while(ch[j] != '\0')
				{
					c = ch[j] - 32;
					if(c < 0)	//????
						break;
					
					if(x >= 127 || (127-x < 8))//16???? || ?????8????????,????
					{
						x = 0;
						y += 16;//????
						if(63 - y < 16)	// ???????????
							break;
					}
					for(unsigned char m = 0; m < 2; m++)
					{
						for(unsigned char n = 0; n < 8; n++)
						{
							for(unsigned char i = 0; i < 8; i++)
							{
								OLED_SetPixel(x+n, y+i+m*8, (F8X16[c][n+m*8] >> i) & 0x01);
							}
						}	
					}
					x += 8;
					j++;
				}
			}break;
		}
	}
	OLED_RefreshRAM();
}


void OLED_ShowChinese(signed short int x, signed short int y, unsigned char* ch)
{
	if (x >= 0 && x < SCREEN_COLUMN && y >= 0 && y < SCREEN_ROW) {
		int32_t  len = 0,offset = sizeof(F16x16_CN[0].index);
		
		while(ch[len] != '\0')
		{
			if(x >= 127 || (127-x < 16))//8?????||?????16????????,????
			{
				x = 0;
				y += 16;
				if(63 - y < 16)	// ???????????
					break;
			}
					
			//?????????????????
			for(unsigned char i = 0; i < sizeof(F16x16_CN)/sizeof(GB2312_CN); i++)
			{
				if(((F16x16_CN[i].index[0] == ch[len]) && (F16x16_CN[i].index[1] == ch[len+1]))){
						for(unsigned char m = 0; m < 2; m++)	//?
						{
							for(unsigned char n = 0; n < 16; n++) // ?
							{
								for(unsigned char j = 0; j < 8; j++)	// ?
								{
									OLED_SetPixel(x+n, y+j+m*8, (F16x16_CN[i].encoder[n+m*16] >> j) & 0x01);
								}
							}
						}			
						x += 16;
						len += offset;
						break;
				}
				else if(F16x16_CN[i].index[0] == ch[len] && ch[len] == 0x20){
					for(unsigned char m = 0; m < 2; m++)
					{
						for(unsigned char n = 0; n < 16; n++)
						{
							for(unsigned char j = 0; j < 8; j++)
							{
								OLED_SetPixel(x+n, y+j+m*8, (F16x16_CN[i].encoder[n+m*16] >> j) & 0x01);
							}								
						}	
					}			
					x += 16; 
					len++;
					break;
				}
			}
		}
	}
	OLED_RefreshRAM();
}



void OLED_ShowBMP(signed short int x0,signed short int y0,signed short int L,signed short int H,const unsigned char BMP[])
{
	if (x0 >= 0 && x0 < SCREEN_COLUMN && x0+L <= SCREEN_ROW &&\
		y0 >= 0 && y0 < SCREEN_COLUMN && y0+H <= SCREEN_ROW) {
		
		unsigned char *p = (unsigned char *)BMP;
		for(signed short int y = y0; y < y0+H; y+=8)
		{
			for(signed short int x = x0; x < x0+L; x++)
			{
				for(signed short int i = 0; i < 8; i++)
				{
					OLED_SetPixel(x, y+i, ((*p) >> i) & 0x01);
				}
				p++;
			}
		}
	}

	OLED_RefreshRAM();
}
