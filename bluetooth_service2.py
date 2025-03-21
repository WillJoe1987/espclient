import bluetooth
import struct
from micropython import const
from persist import get_device_id
import json
from wificonnections import do_connect
from boot import activate, check_for_new_version

# --- 手动定义广播数据函数 ---
def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None):
    payload = bytearray()
    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack('BB', len(value) + 1, adv_type) + value
    if name:
        _append(0x09, name.encode())
    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(0x03, b)
            elif len(b) == 4:
                _append(0x05, b)
            elif len(b) == 16:
                _append(0x07, b)
    return payload

# --- 蓝牙服务定义 ---
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_BLE_UUID_SERVICE = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")  # 自定义服务 UUID
_BLE_UUID_CHAR_RX = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")  # 自定义特征 UUID

_BLE_SERVICE = (
    _BLE_UUID_SERVICE,
    (
        (_BLE_UUID_CHAR_RX, bluetooth.FLAG_READ | bluetooth.FLAG_WRITE),  # 可读可写特征
    ),
)

class BLEUART:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        name = get_device_id()
        ((self._rx_handle,),) = self._ble.gatts_register_services((_BLE_SERVICE,))
        self._connections = set()
        self._payload = advertising_payload(name=name, services=[_BLE_UUID_SERVICE])
        self._advertise()
        self._buffer = b""  # 用于存储分片数据

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print("手机已连接")
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.remove(conn_handle)
            self._advertise()
            print("手机已断开")
        elif event == _IRQ_GATTS_WRITE:
            conn_handle = data[0]
            value = self._ble.gatts_read(self._rx_handle)
            if value:
                print("收到数据:", bytes(value).decode())
                self._buffer += value  # 将分片数据追加到缓冲区
                try:
                    data = json.loads(self._buffer.decode())
                    user_id = data.get("user_id")
                    ssid = data.get("ssid")
                    password = data.get("password")
                    print(f"user_id: {user_id}, ssid: {ssid}, password: {password}")
                    ced = do_connect(ssid, password)
                    if not ced:
                        print("Wi-Fi failed")
                    else:
                        print("Wi-Fi success")
                        aed = activate(user_id)
                        if aed:
                            print("activate")
                            check_for_new_version()
                            print("check new version!")
                except (ValueError, TypeError) as e:
                    print("JSON解码失败:", e)

    def _advertise(self):
        self._ble.gap_advertise(100000, adv_data=self._payload)

def main():
    ble = bluetooth.BLE()
    uart = BLEUART(ble)
    print("等待手机连接...")
    while True:
        pass

if __name__ == "__main__":
    main()