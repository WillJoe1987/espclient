import bluetooth
import struct
from micropython import const

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

_BLE_UUID_SERVICE = bluetooth.UUID(0x1800)
_BLE_UUID_CHAR_RX = bluetooth.UUID(0x2A00)
_BLE_SERVICE = (
    _BLE_UUID_SERVICE,
    (
        (_BLE_UUID_CHAR_RX, bluetooth.FLAG_READ | bluetooth.FLAG_WRITE),
    ),
)

class BLEUART:
    def __init__(self, ble, name="ESP32-BLE"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._rx_handle,),) = self._ble.gatts_register_services((_BLE_SERVICE,))
        self._connections = set()
        self._payload = advertising_payload(name=name, services=[_BLE_UUID_SERVICE])
        self._advertise()

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

    def _advertise(self):
        self._ble.gap_advertise(100000, adv_data=self._payload)

def main():
    ble = bluetooth.BLE()
    uart = BLEUART(ble, name="MyESP32-BLE")
    print("等待手机连接...")
    while True:
        pass

if __name__ == "__main__":
    main()