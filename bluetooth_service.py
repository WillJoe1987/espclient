from bluetooth import BLE

def start_bluetooth_service():
    ble = BLE()
    print(ble.active(True))

    def on_rx(v):
        print("Received data:", v.decode('utf-8'))

    ble.irq(lambda event, data: on_rx(data) if event == 2 else None)  # 2: RX event

    service_uuid = "0000180D-0000-1000-8000-00805F9B34FB"
    char_uuid = "0000180D-0000-1000-8000-00805F9B34FB"
    ble.gatts_register_services(
        (service_uuid, [(char_uuid, 0x02 | 0x08)])  # 0x02: Read, 0x08: Write
    )

    # 修复关键字参数问题，使用 gap_advertise 设置设备名称
    adv_data = b'\x02\x01\x06\x0b\x09ESP32_BLE'  # 广播数据包
    ble.gap_advertise(100,adv_data)

    print("Bluetooth service started. Waiting for connections...")
    while True:
        pass  # Keep the service running

if __name__ == "__main__":
    start_bluetooth_service()