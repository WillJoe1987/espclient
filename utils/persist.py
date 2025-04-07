import esp32
from esp32 import NVS as nvs
import struct

_nvs = nvs("deivce_info")

def _set_nvs(key, value):
    if isinstance(value, str):
        _nvs.set_blob(key, value)
    elif isinstance(value, int):
        _nvs.set_i32(key, value)
    elif isinstance(value, float):
        _nvs.set_blob(key, struct.pack("f", value))
    elif isinstance(value, bool):
        _nvs.set_i32(key, int(value))
    else:
        raise ValueError("Unsupported value type")
    _nvs.commit()

def _get_nvs(key, default=None):
    try:
        # 尝试读取字符串类型
        buffer = bytearray(128)  # 假设最大长度为 128 字节
        length = _nvs.get_blob(key, buffer)
        return buffer[:length].decode('utf-8')  # 解码为字符串
    except OSError:
        try:
            # 尝试读取整数类型
            return _nvs.get_i32(key)
        except OSError:
            try:
                # 尝试读取浮点数类型
                buffer = bytearray(4)  # 浮点数固定为 4 字节
                _nvs.get_blob(key, buffer)
                return struct.unpack("f", buffer)[0]
            except OSError:
                return default

def _delete(key):
    try:
        _nvs.erase_key(key)
        _nvs.commit()
    except OSError:
        pass


def _set_device_id(devie_id):
    _set_nvs("DEVICE_ID", devie_id)

# API for specific keys
def get_device_id():
    return _get_nvs("DEVICE_ID", default="")

def get_serve_url():
    return _get_nvs("SERVE_URL", default="")

def set_serve_url(value):
    _set_nvs("SERVE_URL", value)

def get_user_id():
    return _get_nvs("USER_ID", default="")

def set_user_id(value):
    _set_nvs("USER_ID", value)

def is_activated():
    return bool(_get_nvs("ACTIVATED", default=0))

def set_activated(value):
    _set_nvs("ACTIVATED", bool(value))

def get_active_url():
    return _get_nvs("ACTIVE_URL", default="")

def set_active_url(value):
    _set_nvs("ACTIVE_URL", value)

def get_version_url():
    return _get_nvs("VERSION_URL", default="")

def set_version_url(value):
    _set_nvs("VERSION_URL", value)

def get_serv_version():
    return _get_nvs("SERV_VERSION", default="")

def set_serv_version(value):
    _set_nvs("SERV_VERSION", value)

# Wi-Fi list management
def add_wifi(ssid, password):
    wifi_list = _get_nvs("WIFI_LIST", default="").split(";")
    wifi_dict = {entry.split(",")[0]: entry.split(",")[1] for entry in wifi_list if entry}  # 转为字典去重
    wifi_dict[ssid] = password  # 更新或添加新的 Wi-Fi
    _set_nvs("WIFI_LIST", ";".join([f"{key},{value}" for key, value in wifi_dict.items()]))

def remove_wifi(ssid):
    wifi_list = _get_nvs("WIFI_LIST", default="").split(";")
    wifi_list = [entry for entry in wifi_list if not entry.startswith(f"{ssid},")]
    _set_nvs("WIFI_LIST", ";".join(wifi_list))

def get_wifi_list():
    wifi_list = _get_nvs("WIFI_LIST", default="")
    return [entry.split(",") for entry in wifi_list.split(";") if entry]

# 示例用法
if __name__ == "__main__":
    # set_serve_url("https://example.com")
    # print("SERVE_URL:", get_serve_url())

    # set_user_id("12345")
    # print("USER_ID:", get_user_id())

    # set_activated(True)
    # print("Activated:", is_activated())

    # set_active_url("https://active.example.com")
    # print("ACTIVE_URL:", get_active_url())

    # set_serv_version("1.0.0")
    # print("SERV_VERSION:", get_serv_version())

    # add_wifi("WiFi1", "password1")
    # add_wifi("WiFi2", "password2")
    # print("Wi-Fi List:", get_wifi_list())

    # remove_wifi("WiFi1")
    # print("Wi-Fi List after removal:", get_wifi_list())

    # _close()
    # _set_device_id("selibrige")
    # print(get_device_id())
    # VERSION_URL = "http://1.14.96.238/audio/version"
    # set_version_url(VERSION_URL)
    # set_serv_version("0.0.1")
    print(get_version_url())
    print(get_serv_version())