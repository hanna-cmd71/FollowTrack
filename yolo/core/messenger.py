import struct
import serial

class SerialMessenger:
    """管理向上位机/下位机发送打包状态控制数据的物理通信链路类。"""

    def __init__(self, port: str = 'COM10', baudrate: int = 115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0, write_timeout=0)
            self.ser.set_buffer_size(rx_size=1024, tx_size=1024)
            self.ser.flush()
            print(f"INFO: Hardware serial port {port} non-blocking configuration complete.")
        except serial.SerialException as e:
            print(f"ERROR: Serial initialization failed on {port}: {e}")
            self.ser = None

    def send_target_offset(self, mode: int, dx: int, dy: int):
        if self.ser and self.ser.is_open:
            try:
                # 动态范围有符号 16 位整型严格溢出截断
                dx = int(max(min(dx, 32767), -32768))
                dy = int(max(min(dy, 32767), -32768))
                
                # 字节流打包对齐：[帧头0x5A(1B), 模式(1B), 偏差dx(2B), 偏差dy(2B), 帧尾0xED(1B)] -> 小端对齐 7 字节
                packet = struct.pack('<BbhhB', 0x5A, mode, dx, dy, 0xED)
                self.ser.write(packet)
            except (serial.SerialException, serial.SerialTimeoutException):
                pass

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("INFO: Serial interface successfully disconnected.")