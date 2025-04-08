import machine
import network
import ubinascii
import ujson
import time

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
        self.ap = network.WLAN(network.AP_IF)
        self.wifi_config_mode = False

    def start_network(self):
        if self.wifi_config_mode:
            self._enter_wifi_config_mode()
        else:
            self._connect_to_wifi()

    def _enter_wifi_config_mode(self):
        self.ap.active(True)
        self.ap.config(essid="Xiaozhi_Config", authmode=network.AUTH_OPEN)
        print("WiFi Config Mode: Connect to the AP and configure via web interface.")
        while True:
            time.sleep(10)

    def _connect_to_wifi(self):
        self.wifi.active(True)
        ssid = "YourSSID"  # Replace with actual SSID
        password = "YourPassword"  # Replace with actual password
        self.wifi.connect(ssid, password)
        for _ in range(30):  # Wait up to 30 seconds for connection
            if self.wifi.isconnected():
                print(f"Connected to {ssid}")
                return
            time.sleep(1)
        print("Failed to connect to WiFi. Entering config mode.")
        self.wifi_config_mode = True
        self._enter_wifi_config_mode()

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


class WifiBluetoothBoard(WifiBoard):
    def __init__(self):
        super().__init__()
        self.bluetooth = None  # Placeholder for Bluetooth instance

    def start_network(self):
        super().start_network()
        # Initialize Bluetooth here if needed
        print("Bluetooth functionality is not implemented yet.")

    