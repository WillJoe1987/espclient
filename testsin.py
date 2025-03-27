import math
import time
import struct
from machine import I2S, Pin

def generate_test_tone():
    """生成440Hz正弦波测试信号"""
    tone_freq = 440  # Hz
    amplitude = 30000  # 0-32767
    duration_ms = 1000
    samples = []
    
    for i in range(int(16000 * duration_ms / 1000)):
        val = int(amplitude * math.sin(2 * math.pi * tone_freq * i / 16000))
        samples.append(val)
    
    return struct.pack('<{}h'.format(len(samples)), *samples)

def test_with_fake_audio():
    i2s = I2S(0, mode=I2S.MASTER_RX, bits=16, rate=16000)
    test_data = generate_test_tone()
    
    try:
        while True:
            # 模拟I2S数据输入（替换实际readinto操作）
            fake_audio = test_data[:1024]  # 截取部分数据
            test_data = test_data[1024:] + test_data[:1024]  # 循环缓冲区
            
            # 这里替换原本的audio_buffer处理代码
            print("Sending test tone...")
            # 你的UDP发送代码...
            
            time.sleep_ms(32)
            
    finally:
        i2s.deinit()

# 使用示例
if __name__ == "__main__":
    # 先测试纯音生成
    with open('test.wav', 'wb') as f:
        f.write(generate_test_tone())  # 保存测试文件
    
    # 再运行模拟测试
    test_with_fake_audio()