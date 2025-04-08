import bluetooth
import struct
from micropython import const
from utils.persist import get_device_id
import json
from wificonnections import do_connect
from boot import activate, check_for_new_version





class BLEUART:
    def __init__(self, ble):

        # --- 蓝牙服务定义 ---
        self._IRQ_CENTRAL_CONNECT = const(1)
        self._IRQ_CENTRAL_DISCONNECT = const(2)
        self._IRQ_GATTS_WRITE = const(3)

        self._BLE_UUID_SERVICE = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")  # 自定义服务 UUID
        self._BLE_UUID_CHAR_RX = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")  # 自定义特征 UUID

        self._BLE_SERVICE = (
            self._BLE_UUID_SERVICE,
            (
                (self._BLE_UUID_CHAR_RX, bluetooth.FLAG_READ | bluetooth.FLAG_WRITE),  # 可读可写特征
            ),
        )

        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        name = get_device_id()
        ((self._rx_handle,),) = self._ble.gatts_register_services((self._BLE_SERVICE,))
        self._connections = set()
        self._payload = self.advertising_payload(name=name, services=[self._BLE_UUID_SERVICE])
        self._advertise()
        self._buffer = b""  # 用于存储分片数据

    # --- 手动定义广播数据函数 ---
    def advertising_payload(self, limited_disc=False, br_edr=False, name=None, services=None):
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

    def _irq(self, event, data):
        if event == self._IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print("手机已连接")
        elif event == self._IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.remove(conn_handle)
            self._advertise()
            print("手机已断开")
        elif event == self._IRQ_GATTS_WRITE:
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

    def close(self):
        """关闭蓝牙服务并停止广播"""
        if self._ble:
            self._ble.gap_advertise(None)  # 停止广播
            self._ble.active(False)       # 停止蓝牙
            print("蓝牙服务已关闭")

def main():
    ble = bluetooth.BLE()
    print("uart started.")
    uart = BLEUART(ble)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        uart.close()  # 在程序退出时关闭蓝牙服务
        print("程序已退出")
        
if __name__ == "__main__":
    main()