
from machine import SPI, Pin
import time

# 定义8x8字体点阵
FONT_8x8 = {
    'H': [0x82, 0x82, 0x82, 0xFE, 0x82, 0x82, 0x82, 0x00],
    'E': [0xFE, 0x80, 0x80, 0xFC, 0x80, 0x80, 0xFE, 0x00],
    'L': [0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0xFE, 0x00],
    'O': [0x7C, 0x82, 0x82, 0x82, 0x82, 0x82, 0x7C, 0x00],
}

# ST7789 显示屏驱动类（保持不变）
class ST7789:
    def __init__(self, spi, dc, cs, rst, width=240, height=240):
        self.spi = spi
        self.dc = dc
        self.cs = cs
        self.rst = rst
        self.width = width
        self.height = height
        self.init_display()

    def init_display(self):
        self.rst.value(1)
        time.sleep_ms(50)
        self.rst.value(0)
        time.sleep_ms(50)
        self.rst.value(1)
        time.sleep_ms(150)

        # 关键初始化命令
        self._write_cmd(0x36)
        self._write_data(bytes([0x00]))  # 横屏模式
        self._write_cmd(0x3A)
        self._write_data(bytes([0x55]))  # RGB565
        self._write_cmd(0xB2)
        self._write_data(bytes([0x0C, 0x0C, 0x00, 0x33, 0x33]))
        self._write_cmd(0xB7)
        self._write_data(bytes([0x35]))
        self._write_cmd(0x11)
        time.sleep_ms(120)
        self._write_cmd(0x29)
        time.sleep_ms(50)
        

    def _write_cmd(self, cmd):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytes([cmd]))
        self.cs.value(1)

    def _write_data(self, data):
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(data)
        self.cs.value(1)

    def fill(self, color):
        self.set_window(0, 0, self.width - 1, self.height - 1)
        color_bytes = bytes([color & 0xFF, (color >> 8) & 0xFF])
        self.dc.value(1)
        self.cs.value(0)
        for _ in range(self.width * self.height):
            self.spi.write(color_bytes)
        self.cs.value(1)

    def set_window(self, x0, y0, x1, y1):
        self._write_cmd(0x2A)
        self._write_data(bytes([(x0 >> 8) & 0xFF, x0 & 0xFF, (x1 >> 8) & 0xFF, x1 & 0xFF]))
        self._write_cmd(0x2B)
        self._write_data(bytes([(y0 >> 8) & 0xFF, y0 & 0xFF, (y1 >> 8) & 0xFF, y1 & 0xFF]))
        self._write_cmd(0x2C)

    def draw_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.set_window(x, y, x, y)
            self._write_data(bytes([(color >> 8) & 0xFF, color & 0xFF]))  # 修正此处
    
    def draw_text(self, text, x, y, color):
        print(f"Drawing text: {text} at ({x}, {y}) with color {color:#06X}")
        for char in text:
            if char not in FONT_8x8:
                continue
            char_data = FONT_8x8[char]
            for row in range(8):
                line = char_data[row]
                for col in range(8):
                    if line & (0b10000000 >> col):
                        self.draw_pixel(x + col, y + row, color)
            x += 8

# 主程序
def main():
    try:
        bl = Pin(4, Pin.OUT, value=1)  # 背光控制
        spi = SPI(1, baudrate=10000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(19))
        dc = Pin(16, Pin.OUT)
        cs = Pin(5, Pin.OUT)
        rst = Pin(17, Pin.OUT)
        
        
        display = ST7789(spi, dc, cs, rst)
        
        # 测试纯红、纯绿、纯蓝
        display.fill(0x001F)  # 预期红色 → 实际显示？
        time.sleep(1)
        display.fill(0x07E0)  # 预期绿色 → 实际显示？
        time.sleep(1)
        display.fill(0x001F)  # 预期蓝色 → 实际显示黄色
        time.sleep(1)
        display.draw_text("HELLO", 10, 10, 0x001F)  # 红色文字  
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()