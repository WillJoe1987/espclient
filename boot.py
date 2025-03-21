from persist import set_user_id, set_activated, get_version_url, get_serv_version, set_serv_version, set_serve_url, set_active_url, set_version_url, get_device_id, get_active_url
import machine
import urequests

def reboot():
    # 清除用户 ID 和设置 Activated 为 False
    set_user_id("")
    set_activated(False)
    
    print("Configuration reset. Rebooting...")
    machine.reset()

def check_for_new_version():
    version_url = get_version_url()
    if not version_url:
        print("VERSION_URL is not set.")
        return False

    uuid = get_device_id()
    if not uuid:
        print("Device UUID is not set.")
        return False

    try:
        # 在请求中添加设备 UUID 作为查询参数
        response = urequests.get(f"{version_url}?uuid={uuid}")
        if response.status_code != 200:
            print(f"Failed to fetch version info. HTTP Status: {response.status_code}")
            return False

        data = response.json()
        if data.get("code") != 200:
            print(f"Error in response: {data.get('msg', 'Unknown error')}")
            return False

        current_version = get_serv_version()
        new_version = data["data"].get("version", "")

        if current_version == new_version:
            print("Version is up-to-date.")
            return False

        print(f"New version available: {new_version}. Updating configuration...")

        # 更新 SERVE_URL
        if "SERVE_URL" in data["data"] and data["data"]["SERVE_URL"]:
            set_serve_url(data["data"]["SERVE_URL"])

        # 更新 ACTIVE_URL
        if "ACTIVE_URL" in data["data"] and data["data"]["ACTIVE_URL"]:
            set_active_url(data["data"]["ACTIVE_URL"])

        # 更新 VERSION_URL
        if "VERSION_URL" in data["data"] and data["data"]["VERSION_URL"]:
            set_version_url(data["data"]["VERSION_URL"])

        # 更新版本号
        set_serv_version(new_version)

        print("Configuration updated successfully.")
        return True

    except Exception as e:
        print(f"Error checking for new version: {e}")
        return False

def activate(userid):
    active_url = get_active_url()
    if not active_url:
        print("ACTIVE_URL is not set.")
        return False

    uuid = get_device_id()
    if not uuid:
        print("Device UUID is not set.")
        return False

    payload = {
        "uuid": uuid,
        "userid": userid
    }

    try:
        response = urequests.post(active_url, json=payload)
        if response.status_code != 200:
            print(f"Failed to activate. HTTP Status: {response.status_code}")
            return False

        data = response.json()
        if data.get("code") != "200":
            print(f"Activation failed: {data.get('msg', 'Unknown error')}")
            return False

        activation_data = data.get("data", {})
        if not activation_data.get("active", False):
            print(f"Activation failed: {activation_data.get('reason', 'Unknown reason')}")
            return False

        print(f"Activation successful: {activation_data.get('reason', 'No reason provided')}")
        set_user_id(userid)
        set_activated(True)
        return True

    except Exception as e:
        print(f"Error during activation: {e}")
        return False

if __name__ == "__main__":
    activate("123")