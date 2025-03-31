import ubinascii
import machine
import network
import socket
import time
from machine import I2S, Pin
from wificonnections import do_connect
import struct

# 配置参数
DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode('utf-8')  # 基于芯片ID生成设备唯一标识
SERVER_IP = '1.14.96.238'  # 服务端IP
SERVER_PORT = 7676
MAGIC_NUMBER = 0xA1B2C3D4     # 与服务端一致的魔数
AUDIO_FORMAT = "!I16sH"       # 协议头格式: 魔数(4B) + 设备ID(16B) + 数据长度(2B)

# 音频配置
SAMPLE_RATE_IN_HZ = 16000
SAMPLE_SIZE_IN_BITS = 16
BUFFER_LENGTH_IN_BYTES = 1024  # 每次发送的音频数据长度
SAMPLES_PER_BUFFER = BUFFER_LENGTH_IN_BYTES // (SAMPLE_SIZE_IN_BITS // 8)
interval_ms = int((SAMPLES_PER_BUFFER / SAMPLE_RATE_IN_HZ) * 1000)

def setup_mic():
    i2s = I2S(
        0,
        sck=Pin(14),
        ws=Pin(15),
        sd=Pin(13),
        mode=I2S.RX,  # 接收模式
        bits=SAMPLE_SIZE_IN_BITS,
        format=I2S.MONO,
        rate=SAMPLE_RATE_IN_HZ,
        ibuf=BUFFER_LENGTH_IN_BYTES * 2
    )
    return i2s

def create_packet(audio_data):
    # 确保音频数据是字节类型
    if not isinstance(audio_data, (bytes, bytearray)):
        print(f"错误：音频数据类型不正确 {type(audio_data)}")
        audio_data = bytearray()
        
    # 设备ID处理
    dev_id = DEVICE_ID.encode('utf-8')[:16]
    dev_id = dev_id + b'\x00'*(16-len(dev_id))
    
    try:
        # 创建数据包头
        header = struct.pack(AUDIO_FORMAT, MAGIC_NUMBER, dev_id, len(audio_data))
        # 合并头部和音频数据
        return header + audio_data
    except Exception as e:
        print(f"创建数据包错误: {e}")
        return bytearray()

def process_audio(raw_data):
    # 确保输入是字节类型
    if not isinstance(raw_data, (bytes, bytearray)):
        print(f"警告：输入类型不正确 {type(raw_data)}")
        return bytearray()
        
    # 将字节流转换为数字
    try:
        fmt = f'<{len(raw_data)//2}h'
        samples = list(struct.unpack(fmt, raw_data))
    except struct.error as e:
        print(f"解包错误: {e}, 数据长度: {len(raw_data)}")
        return bytearray()
    
    # 1. 移除直流偏移（消除电流音）
    dc_offset = sum(samples) // len(samples) if samples else 0
    samples = [x - dc_offset for x in samples]
    
    # 2. 动态增益控制（提升音量）
    max_val = max((abs(x) for x in samples), default=1)
    if max_val > 100:  # 只有当信号足够强时才进行增益调整
        gain = min(5, 32767 // max_val)  # 限制最大增益
        samples = [min(32767, max(-32768, int(x * gain))) for x in samples]
    
    # 3. 简单低通滤波（抑制高频噪声）
    filtered = []
    prev = 0
    alpha = 20 # 滤波系数
    for x in samples:
        new_val = (prev * (100 - alpha) + x * alpha) // 100
        filtered.append(max(-32768, min(32767, new_val)))  # 钳位
        prev = filtered[-1]
    
    # 返回字节数组
    try:
        return bytearray(struct.pack(f'<{len(filtered)}h', *filtered))
    except struct.error as e:
        print(f"打包错误: {e}")
        return bytearray()

def main():
    mic = udp_socket = None
    packet_count = 0
    start_time = time.ticks_ms()
    
    try:
        mic = setup_mic()
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        audio_buffer = bytearray(BUFFER_LENGTH_IN_BYTES)
        
        print(f"音频流开始传输 (间隔: {interval_ms}ms)")
        while True:
            try:
                num_bytes_read = mic.readinto(audio_buffer)
                if num_bytes_read > 0:
                    # 复制部分缓冲区以避免修改原始数据
                    processed_audio = process_audio(bytes(audio_buffer[:num_bytes_read]))
                    if processed_audio:
                        packet = create_packet(processed_audio)
                        udp_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
                        packet_count += 1
                        
                        if packet_count % 100 == 0:
                            elapsed = time.ticks_diff(time.ticks_ms(), start_time)/1000
                            print(f"已发送 {packet_count} 个数据包 ({elapsed:.1f}秒)")
                
                time.sleep_ms(max(1, interval_ms))
                
            except OSError as e:
                print(f"error: {e}")
                time.sleep(1)
                if not network.WLAN(network.STA_IF).isconnected():
                    do_connect()
                    
    except KeyboardInterrupt:
        print("user cancel")
    finally:
        if mic: mic.deinit()
        if udp_socket: udp_socket.close()
        print(f"total pack: {packet_count}")

if __name__ == "__main__":
    if do_connect():
        main()