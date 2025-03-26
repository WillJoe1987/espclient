def parse_audio_buffer(buf):
    samples = []
    for i in range(0, len(buf), 4):
        # 组合32bit值
        b0, b1, b2, b3 = buf[i], buf[i+1], buf[i+2], buf[i+3]
        raw_32bit = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)
        
        # 提取24bit
        raw_24bit = raw_32bit & 0x00FFFFFF
        
        # 补码转换
        signed = raw_24bit if raw_24bit < 0x800000 else raw_24bit - 0x1000000
        
        # 精确缩放（修正负数计算）
        if signed >= 0:
            scaled = (signed * 127 + 16383) // 32767  # 正数：32767→127
        else:
            scaled = -((-signed * 127 + 16383) // 32767)  # 负数：-32768→-128
        
        # 限幅
        final = max(min(scaled, 127), -128)
        samples.append(final)
    
    return bytearray([s & 0xFF for s in samples])

def test_parser():
    test_cases = [
        ([0,0,128,255], -128),    # -32768 → -128
        ([255,127,0,0], 127),     # 32767 → 127
        ([0,64,0,0], 64),         # 16384 → 64
        ([1,0,128,255], -127),    # -32767 → -127
        ([0,0,0,0], 0)            # 0 → 0
    ]
    
    for data, expected in test_cases:
        result = int.from_bytes(
            parse_audio_buffer(bytearray(data))[:1], 
            'little', 
            True
        )
        print(f"输入: {data} | 结果: {result} | 期望: {expected} | {'✓' if result == expected else '✗'}")
test_parser()