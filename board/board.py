import re
from typing import override
from rpds import T
from yaml import scan
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

# 增加wifiboard类的监听能力，以及从nvs中记录ssid进行链接的能力。
# TODO : 增加wifi scan到的热点列表，并与过往链接记录匹配，以降低连接失败的概率。
class WifiBoard(Board):

    def __init__(self):
        self.wifi_monitor_interval = 10  # 监控间隔时间
        super().__init__()
        self.wifi = network.WLAN(network.STA_IF)    
        self.board_name = "WiFiBoard"  # 设置板子名称  
        self.moniting = False  # 是否正在监控Wi-Fi状态

    def on_wifi_disconnect(self):
        """
        抽象方法，子类需实现Wi-Fi断开时的处理逻辑。
        """
        raise NotImplementedError("on_wifi_disconnect must be implemented by subclasses")

    def monitor_wifi_status(self):
        if self.moniting:
            return  # 如果已经在监控Wi-Fi状态，则不再启动新的线程
        # 启动Wi-Fi状态监听
        while True:
            if self.wifi.isconnected():
                self.moniting = True
                time.sleep(self.wifi_monitor_interval)  # 定期检查Wi-Fi状态
            else:
                self.moniting = False
                break
        self.on_wifi_disconnect()

    def start_network(self):
        self.wifi.active(True)  # Ensure Wi-Fi is active    
        if self.wifi.isconnected():
            print("Wi-Fi is already connected.")
            self.monitor_wifi_status()
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
        print(f"Connecting to Wi-Fi SSID: {ssid}...")
        try_count = 0
        while not self.wifi.isconnected() and try_count < 3:
            try_count += 1
            print(f"Attempt {try_count} to connect to {ssid}...")
            self.wifi.connect(ssid, password)
            if self.wifi.isconnected():
                print("Connected to Wi-Fi:", self.wifi.ifconfig())
                self.monitor_wifi_status()
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

# BLEWifiBoard类，继承自WifiBoard,如果wifi链接失败，则启动BLE获取wifi信息
class BLEWifiBoard(WifiBoard):

    def __init__(self):
        super().__init__()
        self.board_name = "BLEWifiBoard"  # 设置板子名称
    
    def on_wifi_disconnect(self):
        print("Wi-Fi disconnected, starting BLE for reconfiguration...")
        self.start_ble()

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
    
    # --- 手动定义广播数据函数, ---
    # TODO: 后续可优化点：1、是否已激活以及是否绑定用户；2、wifi scan到的热点列表；
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
    # 关闭蓝牙服务并停止广播
    def closeBLE(self):
        if self._ble:
            self._ble.gap_advertise(None)  # 停止广播
            self._ble.active(False)       # 停止蓝牙
            print("蓝牙服务已关闭")