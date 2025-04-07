import machine
import network
import time
from application import Application

def initialize_nvs():
    # 模拟初始化 NVS（在 MicroPython 中通常不需要）
    print("Initializing NVS...")

def initialize_wifi():
    # 初始化 WiFi
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    if not wifi.isconnected():
        print("Connecting to WiFi...")
        wifi.connect("YourSSID", "YourPassword")  # 替换为实际的 SSID 和密码
        for _ in range(30):  # 最多等待 30 秒
            if wifi.isconnected():
                print("WiFi connected:", wifi.ifconfig())
                return
            time.sleep(1)
        print("Failed to connect to WiFi.")
    else:
        print("WiFi already connected:", wifi.ifconfig())

def main():
    # 初始化 NVS
    initialize_nvs()

    # 初始化 WiFi
    initialize_wifi()

    # 启动应用程序
    app = Application.get_instance()
    app.start()

if __name__ == "__main__":
    main()
