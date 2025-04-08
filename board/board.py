import machine
import network
import ubinascii
import ujson
import time
from utils.persist import add_wifi, get_wifi_list, get_device_id
import bluetooth
from micropython import const
import struct

class Board:
    def __init__(self):
        self.uuid = self._generate_uuid()
        self.board_name = "DefaultBoard"

    def _generate_uuid(self):
        # 使用设备的MAC地址生成UUID
        mac = ubinascii.hexlify(network.WLAN().config('mac')).decode()
        return f"{mac[:8]}-{mac[8:12]}-{mac[12:16]}-{mac[16:20]}-{mac[20:]}"

    def get_uuid(self):
        return self.uuid

    def get_json(self):
        # 返回设备信息的JSON
        info = {
            "uuid": self.uuid,
            "board_name": self.board_name,
            "chip_model": "ESP32",
            "flash_size": machine.mem32[0x3FF00000],  # 示例值
            "heap_size": machine.mem_free()
        }
        return ujson.dumps(info)

    def start_network(self):
        raise NotImplementedError("start_network must be implemented by subclasses")

    def set_power_save_mode(self, enabled):
        raise NotImplementedError("set_power_save_mode must be implemented by subclasses")

class WifiBoard(Board):

    def __init__(self):
        super().__init__()
        self.wifi = network.WLAN(network.STA_IF)      

    def start_network(self):
        self.wifi.active(True)  # Ensure Wi-Fi is active    
        if self.wifi.isconnected():
            print("Wi-Fi is already connected.")
            return True
        else:
            # 如果未传入参数，从存储的 Wi-Fi 列表中遍历尝试连接
            wifi_list = get_wifi_list()
            for saved_ssid, saved_password in wifi_list:
                if self._connect_to_wifi(saved_ssid, saved_password):
                    return True
            print("Failed to connect to any saved Wi-Fi networks.")
            return False

    def _connect_to_wifi(self, ssid, password):
        
        if self.wifi.isconnected():
            print("Wi-Fi is already connected.")
            return True

        print(f"Connecting to Wi-Fi SSID: {ssid}...")
        try_count = 0
        while not self.wifi.isconnected() and try_count < 3:
            try_count += 1
            print(f"Attempt {try_count} to connect to {ssid}...")
            self.wifi.connect(ssid, password)
            if self.wifi.isconnected():
                print("Connected to Wi-Fi:", self.wifi.ifconfig())
                add_wifi(ssid, password)
                return True
            time.sleep(1)

        return False

    def set_power_save_mode(self, enabled):
        if enabled:
            self.wifi.config(pm=network.WIFI_PS_MIN_MODEM)
        else:
            self.wifi.config(pm=network.WIFI_PS_NONE)

    def get_json(self):
        # 返回WiFi相关信息的JSON
        info = super().get_json()
        info_dict = ujson.loads(info)
        if self.wifi.isconnected():
            info_dict.update({
                "ssid": self.wifi.config('essid'),
                "ip": self.wifi.ifconfig()[0],
                "rssi": self.wifi.status('rssi')
            })
        return ujson.dumps(info_dict)

class BLEWifiBoard(WifiBoard):
    """
        BLEWifiBoard类，继承自WifiBoard,如果wifi链接失败，则启动BLE获取wifi信息
    """
    
    def __init__(self):
        super().__init__()

    def start_network(self):
        super().start_network()
        if not self.wifi.isconnected():
            print("Wi-Fi connection failed, starting BLE...")
            self.start_ble()
        else:
            print("Wi-Fi connected successfully.")
        return self.wifi.isconnected()

    def start_ble(self):
        # BLE启动逻辑
        print("BLE starting.")
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
        
        self._ble = bluetooth.BLE()
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
                    data = ujson.loads(self._buffer.decode())
                    user_id = data.get("user_id")
                    ssid = data.get("ssid")
                    password = data.get("password")
                    print(f"user_id: {user_id}, ssid: {ssid}, password: {password}")
                    ced = self._connect_to_wifi(ssid, password)
                    if not ced:
                        print("Wi-Fi failed, SSID OR PASSWORD ERROR")
                    else:
                        self.closeBLE()
                except (ValueError, TypeError) as e:
                    print("JSON解码失败:", e)

    def _advertise(self):
        self._ble.gap_advertise(100000, adv_data=self._payload)

    def closeBLE(self):
        """关闭蓝牙服务并停止广播"""
        if self._ble:
            self._ble.gap_advertise(None)  # 停止广播
            self._ble.active(False)       # 停止蓝牙
            print("蓝牙服务已关闭")