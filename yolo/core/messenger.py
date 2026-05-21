"""串口通信模块，负责按照协议打包并发送数据到 STM32。"""

import struct
from typing import Optional
import serial


class SerialMessenger:
    """处理与下位机串口通信的类。"""

    def __init__(self, port: str = 'COM10', baudrate: int = 115200):
        """初始化并打开串口。

        Args:
            port: 串口号 (如 'COM10')。
            baudrate: 波特率。
        """
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0.01)
            self.ser.flush()
            print(f"INFO: Serial port {port} connected.")
        except serial.SerialException as e:
            print(f"ERROR: Could not open serial port {port}: {e}")
            self.ser = None

    def send_target_offset(self, mode: int, dx: int, dy: int):
        """打包并发送偏移量。

        协议格式: 0x5A (Header) + mode (int8) + dx (int16) + dy (int16) + 0xED (Tail)

        Args:
            dx: 水平偏差值。
            dy: 垂直偏差值。
            mode: 工作模式。
        """
        if self.ser and self.ser.is_open:
            try:
                # 使用小端模式打包数据: <BhhB
                packet = struct.pack('<BBhhB', 0x5A, mode, int(dx), int(dy), 0xED)
                self.ser.write(packet)
            except Exception as e:
                print(f"WARNING: Data transmission failed: {e}")

    def close(self):
        """关闭串口连接。"""
        if self.ser:
            self.ser.close()
            print("INFO: Serial connection closed.")
