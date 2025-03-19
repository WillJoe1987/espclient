import machine
import esp32
import ustruct
import urequests
import time
from wificonnections import do_connect



# 配置I2S引脚
i2s = machine.I2S(
    0,
    sck=machine.Pin(17),  # 时钟引脚
    ws=machine.Pin(18),   # 帧选择引脚
    sd=machine.Pin(16),   # 数据引脚
    mode=machine.I2S.RX,  # 接收模式
    bits=16,              # 每个样本16位
    format=machine.I2S.MONO,  # 单声道
    rate=16000,           # 采样率16kHz
    ibuf=20000            # 缓冲区大小
)

def read_audio():
    audio_data = bytearray(1024)
    start_time = time.time()
    collected_data = bytearray()  # 用于存储 10 秒的数据
    while True:
        try:
            num_bytes_read = i2s.readinto(audio_data)
            if num_bytes_read > 0:
                # 累积音频数据
                collected_data.extend(audio_data[:num_bytes_read])
                elapsed_time = time.time() - start_time
                print(f"Collecting audio... ({elapsed_time:.1f}s elapsed)")
                
                # 如果已收集 10 秒的数据，上传并重置计时器
                if elapsed_time >= 10:
                    upload_audio(collected_data)
                    collected_data = bytearray()
                    start_time = time.time()
        except Exception as e:
            print("Error reading audio data:", e)

def read_audio():
    audio_data = bytearray(1024)
    while True:
        try:
            num_bytes_read = i2s.readinto(audio_data)
            if num_bytes_read > 0:
                print(f"Uploading {num_bytes_read} bytes of audio data...")
                upload_audio(audio_data[:num_bytes_read])  # 上传当前块数据
        except Exception as e:
            print("Error reading audio data:", e)

def upload_audio(audio_data):
    url = "http://1.14.96.238/audio/upload"
    headers = {'Content-Type': 'application/octet-stream'}
    try:
        response = urequests.post(url, data=audio_data, headers=headers)
        print("Upload response:", response.status_code)
        response.close()
    except Exception as e:
        print("Error uploading audio data:", e)

if __name__ == "__main__":
    if do_connect():
        read_audio()
