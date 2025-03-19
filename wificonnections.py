import time
import network

SSID = "byeww"
PASSWORD = "wlj19870130"
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
def do_connect():
    if wlan.isconnected():
        print("Wi-Fi is already connected.")
        return True
    else:
        try:
            print("Connecting to Wi-Fi...")
            wlan.connect(SSID, PASSWORD)
            start_time = time.time()
            while not wlan.isconnected():
                if time.time() - start_time > 10:  # 超时时间 10 秒
                    raise OSError("Wi-Fi connection timed out")
                print("Connecting...")
                time.sleep(1)
            print("Connected to Wi-Fi:", wlan.ifconfig())
            return True
        except Exception as e:
            print("Wi-Fi connection failed:", e)
            return False
