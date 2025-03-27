import machine
import esp32
import urequests
import time
from wificonnections import do_connect
import socket
import struct
import ubinascii
# 配置I2S引脚
i2s = machine.I2S(
    0,
    sck=machine.Pin(14),  # 改为 GPIO 14
    ws=machine.Pin(15),   # 改为 GPIO 15
    sd=machine.Pin(13),   # 改为 GPIO 13
    mode=machine.I2S.RX,  # 接收模式
    bits=32,              # 每个样本16位tre
    format=machine.I2S.MONO,  # 单声道
    rate=16000,           # 采样率16kHz
    ibuf=20000,            # 缓冲区大小
    
)
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.setblocking(False)  # 非阻塞模式

# ====================
DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode('utf-8')  # 基于芯片ID生成设备唯一标识
SERVER_IP = '1.14.96.238'  # 服务端IP
SERVER_PORT = 7676
MAGIC_NUMBER = 0xA1B2C3D4     # 与服务端一致的魔数
AUDIO_FORMAT = "!I16sH"       # 协议头格式: 魔数(4B) + 设备ID(16B) + 数据长度(2B)
# ====================

def move_bit(value):
    mv = value - 32768
    value = mv.to_bytes(2, 'little', True)

def parse_audio_buffer(buf):
    samples = []
    for i in range(0, len(buf), 4):
        raw = int.from_bytes(buf[i:i+4], 'little')
        raw24 = raw & 0x00FFFFFF
        signed = raw24 if raw24 < 0x800000 else raw24 - 0x01000000
        scaled = signed >> 8  # 24bit→16bit（右移8位）
        samples.append(scaled)
    
    # 返回16-bit有符号值列表（非字节流！）
    return samples

def read_audio():
    while True:
        try:
            buffer = bytearray(1024)  # 创建一个 1024 字节的缓冲区
            interval_ms = int((1024 / 32000) * 1000) # 计算缓冲区数据的时间间隔
            i2s.readinto(buffer)     # 将数据读取到缓冲区中
            samples = parse_audio_buffer(buffer)
            samples = remove_dc_offset(samples) 
            analyze_audio(samples)
            packet = build_packet(samples)
            # 3. 发送UDP包
            udp_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
            # 4. 控制发送速率（约interval_msms间隔）
            time.sleep_ms(interval_ms)
        except OSError as e:
            if e.errno == 11:  # EAGAIN, 非阻塞模式下无数据
                pass
            else:
                print("Send Error:", e)
        except KeyboardInterrupt:
            break

def upload_audio(audio_data):
    url = "http://1.14.96.238/audio/upload"
    headers = {'Content-Type': 'application/octet-stream'}
    try:
        response = urequests.post(url, data=audio_data, headers=headers)
        print("Upload response:", response.status_code)
        response.close()
    except Exception as e:
        print("Error uploading audio data:", e)

def unsigned_to_signed(value, bits):
    # 将无符号整数转换为有符号整数
    if value >= (1 << (bits - 1)):
        value -= (1 << bits)
    return value

def remove_dc_offset(samples):  # 输入为列表
    dc_offset = sum(samples) // len(samples)
    return [s - dc_offset for s in samples]  # 返回列表

# ====================
# ADPCM编码器（简化版）
# ====================
class ADPCMEncoder:
    
    def __init__(self):
        self.prev_sample = 0
        self.index = 0
        
    def encode(self, samples):  # 接收数值列表而非字节流
        encoded = bytearray()
        for sample in samples:
            # 简化ADPCM编码（实际应使用标准算法）
            delta = sample - self.prev_sample
            code = min(15, max(0, (abs(delta) >> 4)))
            if delta < 0:
                code |= 0x10
            encoded.append(code)
            self.prev_sample = sample
        return bytes(encoded)
    
encoder = ADPCMEncoder()

# ====================
# 协议封装函数
# ====================
def build_packet(raw_audio):
    # 1. 音频压缩
    compressed = encoder.encode(raw_audio)
    
    # 2. 构造协议头 - 修复设备ID填充方式
    device_id_bytes = DEVICE_ID.encode('utf-8')
    if len(device_id_bytes) > 16:
        device_id_bytes = device_id_bytes[:16]
    else:
        device_id_bytes = device_id_bytes + b'\x00' * (16 - len(device_id_bytes))
    
    header = struct.pack(
        AUDIO_FORMAT,
        MAGIC_NUMBER,
        device_id_bytes,  # 已正确填充到16字节
        len(compressed)
    )
    # 3. 合并包头和音频数据
    return header + compressed

def analyze_audio(samples):
    print(f"Min: {min(samples)}, Max: {max(samples)}, Avg: {sum(samples)//len(samples)}")

if __name__ == "__main__":
    if do_connect():
        print("Wi-Fi已连接，开始音频流传输...")
        read_audio()
