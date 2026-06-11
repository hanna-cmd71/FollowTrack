"""core/messenger.py"""
import struct
import serial

class SerialMessenger:
    def __init__(self, port: str = 'COM10', baudrate: int = 115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0, write_timeout=0)
            self.ser.set_buffer_size(rx_size=1024, tx_size=1024) # 显式加大系统缓冲区
            self.ser.flush()
            print(f"INFO: Hardware serial port {port} non-blocking configuration complete.")
        except serial.SerialException as e:
            print(f"ERROR: Serial initialization failed on {port}: {e}")
            self.ser = None

    def send_target_offset(self, mode: int, dx: int, dy: int):
        if self.ser and self.ser.is_open:
            try:
                dx = int(max(min(dx, 32767), -32768))
                dy = int(max(min(dy, 32767), -32768))
                
                packet = struct.pack('<BbhhB', 0x5A, mode, dx, dy, 0xED)
                self.ser.write(packet)
            except (serial.SerialException, serial.SerialTimeoutException):

                pass

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("INFO: Serial interface successfully disconnected.")