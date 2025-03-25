import machine
import esp32
import urequests
import time
from wificonnections import do_connect
import socket  # 新增导入
import struct
import ubinascii
# 配置I2S引脚
i2s = machine.I2S(
    0,
    sck=machine.Pin(17),  # 时钟引脚
    ws=machine.Pin(18),   # 帧选择引脚
    sd=machine.Pin(16),   # 数据引脚
    mode=machine.I2S.RX,  # 接收模式
    bits=32,              # 每个样本16位tre
    format=machine.I2S.MONO,  # 单声道
    rate=16000,           # 采样率16kHz
    ibuf=20000            # 缓冲区大小
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
    mv = memoryview(buf)
    for i in range(0, len(mv), 4):
        chunk = mv[i:i+4]
        raw_value = int.from_bytes(chunk, 'little', False)
        raw_24bit = raw_value >> 8
        if raw_24bit & 0x00800000:
            signed_value = raw_24bit | 0xFF000000
        else:
            signed_value = raw_24bit & 0x00FFFFFF
        signed_value = signed_value - 0x1000000 if signed_value & 0x800000 else signed_value
        samples.append(signed_value)
    return bytearray([max(min(sample, 32767), -32768) & 0xFFFF for sample in samples])

def read_audio():
    while True:
        try:
            buffer = bytearray(1024)  # 创建一个 1024 字节的缓冲区
            interval_ms = int((1024 / 32000) * 1000) # 计算缓冲区数据的时间间隔
            i2s.readinto(buffer)     # 将数据读取到缓冲区中 # 2. 构造协议包
            buffer = parse_audio_buffer(buffer)
            # 确保数据长度是偶数
            if len(buffer) % 2 != 0:
                buffer += b'\x00'
            print(buffer[:20])
            buffer = remove_dc_offset(buffer) 
            analyze_audio(buffer)
            raw_audio = buffer       # 将缓冲区数据赋值给 raw_audio
            packet = build_packet(raw_audio)
            # print(packet)
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


#去直流偏移
def remove_dc_offset(pcm_data):
    if len(pcm_data) % 2 != 0:
        pcm_data += b'\x00'
    samples = [int.from_bytes(pcm_data[i:i+2], 'little', True) for i in range(0, len(pcm_data), 2)]
    dc_offset = sum(samples) // len(samples)
    adjusted_samples = []
    for sample in samples:
        adjusted = sample - dc_offset
        # 限幅至16位有符号整数范围
        adjusted = max(min(adjusted, 32767), -32768)
        adjusted_samples.append(adjusted)
    return b''.join([s.to_bytes(2, 'little', True) for s in adjusted_samples])
# ====================
# ADPCM编码器（简化版）
# ====================
class ADPCMEncoder:
    def __init__(self):
        self.index = 0
        self.prev_sample = 0

    def encode(self, pcm_data):
        # 手动实现步长为 2 的切片
        return bytes([pcm_data[i] >> 4 for i in range(0, len(pcm_data), 2)])

encoder = ADPCMEncoder()
# ====================
# 协议封装函数
# ====================
def build_packet(raw_audio):
    # 1. 音频压缩
    compressed = encoder.encode(raw_audio)
    
    # 2. 构造协议头
    header = struct.pack(
        AUDIO_FORMAT,
        MAGIC_NUMBER,
        (DEVICE_ID + '\x00' * (16 - len(DEVICE_ID))).encode('utf-8'),  # 手动填充到16字节
        len(raw_audio)
    )
    # 3. 合并包头和音频数据
    return header + raw_audio

#检查音频信号强度
def analyze_audio(buffer):
    samples = [int.from_bytes(buffer[i:i+2], 'little', True) for i in range(0, len(buffer), 2)]
    print(f"Min: {min(samples)}, Max: {max(samples)}, Avg: {sum(samples) // len(samples)}")
if __name__ == "__main__":
    if do_connect():
        read_audio()
