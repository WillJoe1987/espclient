import time
import network
from persist import add_wifi, get_wifi_list

wlan = network.WLAN(network.WLAN.IF_STA)
wlan.active(True)

def do_connect(ssid=None, password=None):
    if wlan.isconnected():
        print("Wi-Fi is already connected.")
        return True

    if ssid and password:
        # 如果传入了参数，直接尝试连接
        res = _connect_to_wifi(ssid, password)
        add_wifi(ssid, password)  # 保存成功连接的 Wi-Fi
        return res
    else:
        # 如果未传入参数，从存储的 Wi-Fi 列表中遍历尝试连接
        wifi_list = get_wifi_list()
        for saved_ssid, saved_password in wifi_list:
            if _connect_to_wifi(saved_ssid, saved_password):
                return True
        print("Failed to connect to any saved Wi-Fi networks.")
        return False

def _connect_to_wifi(ssid, password):
    if wlan.isconnected():
        print("Wi-Fi is already connected.")
        return True

    print(f"Connecting to Wi-Fi SSID: {ssid}...")
    wlan.connect(ssid, password)
    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > 10:  # 超时时间 10 秒
            print(f"Connection to {ssid} timed out.")
            return False
        time.sleep(1)

    if wlan.isconnected():
        print("Connected to Wi-Fi:", wlan.ifconfig())
        return True
    else:
        print(f"Failed to connect to {ssid}.")
        return False

def is_connected():
    return wlan.isconnected()


if __name__ == "__main__":
    do_connect()
    print("Wi-Fi connected:", wlan.isconnected())
    print("Wi-Fi config:", wlan.ifconfig())