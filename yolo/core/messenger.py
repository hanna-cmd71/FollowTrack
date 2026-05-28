"""    自定义协议结构说明: 0x5A(帧头) + mode(1字节有符号整型) + 
        dx(2字节有符号小端整型) + dy(2字节有符号小端整型) + 0xED(帧尾)
    Args:
        mode: 决策模式码。
        dx: 水平像素偏置量。
        dy: 垂直像素偏置量。
"""
import struct
import serial


class SerialMessenger:

    def __init__(self, port: str = 'COM10', baudrate: int = 115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0.01)
            self.ser.flush()
            print(f"INFO: Hardware serial port {port} configuration complete.")
        except serial.SerialException as e:
            print(f"ERROR: Serial initialization failed on {port}: {e}")
            self.ser = None

    def send_target_offset(self, mode: int, dx: int, dy: int):

        if self.ser and self.ser.is_open:
            try:
                packet = struct.pack('<BbhhB', 0x5A, mode, dx, dy, 0xED)
                self.ser.write(packet)
            except serial.SerialException as e:
                print(f"WARNING: Serial payload dispatch exception: {e}")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("INFO: Serial interface successfully disconnected.")