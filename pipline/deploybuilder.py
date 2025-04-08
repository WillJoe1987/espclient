
from logging import root
import os
import json
from re import S
import time
import logging
import subprocess  # 用于调用外部命令

rootfiles = ["application.py", "main.py"]
rootdir = "../"
subdirs = [{
    "dir": "board",
    "files": ["**"]
}, {
    "dir": "iot",
    "files": ["**"]
}, {
    "dir":"protocol",
    "files": ["**"]
}, {
    "dir":"utils",
    "files": ["**"]
}]

to_config = "./deploy.json"
version = "1.0"
device_port = "COM3"  # 替换为实际的设备端口

def collecting_files():

    # 获取当前目录下的所有文件和文件夹
    all_files = os.listdir(rootdir)

    # 创建一个空列表来存储符合条件的文件
    files_to_configure = []

    # 遍历所有文件和文件夹
    for item in all_files:
        if item in rootfiles:  # 如果是根目录下的文件，直接添加
            files_to_configure.append(item.replace("\\", "/"))
        else:
            for subdir in subdirs:
                if item == subdir["dir"]:
                    for file in subdir["files"]:
                        if "*" in file and not file.startswith("**"):  # Match files in the current directory with optional prefix/suffix
                            prefix, _, suffix = file.partition("*")
                            for f in os.listdir(os.path.join(rootdir, item)):
                                if f.startswith(prefix) and f.endswith(suffix):
                                    files_to_configure.append(os.path.join(item, f).replace("\\", "/"))
                        elif "**" in file:  # Match files recursively in subdirectories with optional prefix/suffix
                            prefix, _, suffix = file.partition("**")
                            for root, _, files in os.walk(os.path.join(rootdir, item)):
                                for f in files:
                                    if f.startswith(prefix) and f.endswith(suffix):
                                        files_to_configure.append(os.path.relpath(os.path.join(root, f), rootdir).replace("\\", "/"))
                        else:  # Add specific files
                            files_to_configure.append(os.path.join(item, file).replace("\\", "/"))

    print("收集到的文件:", files_to_configure)
    return files_to_configure

# {
#     "version":"1.0",
#     "name":"deploy",
#     "timestamp":"2023-10-01T12:00:00Z",
#     "description":"upload to esp32, and run deploy.py. In this file, define your file on by one.",
#     "filesPath":[]
# }
def write_config_to_json():
    if os.path.exists(to_config):
        with open(to_config, 'r', encoding='utf-8') as file:
            try:
                config_data = json.load(file)
                print("读取到的配置:", config_data)
            except json.JSONDecodeError as e:
                print("JSON解析错误:", e)
    else:
        print(f"文件 {to_config} 不存在")
    
    files_to_configure = collecting_files()

    time_stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 8 * 3600))
    config_data["timestamp"] = time_stamp,
    config_data["version"] = version
    config_data["filesPath"] = files_to_configure

    with open(to_config, 'w', encoding='utf-8') as file:
        json.dump(config_data, file, indent=4, ensure_ascii=False)
    print(f"配置已写入文件 {to_config}")

def read_json_file(file_path):
    """
    读取 JSON 文件并返回内容
    """
    with open(file_path, 'r') as file:
        return json.load(file)

def upload_files_to_device():
    """
    使用 mpremote 将文件上传到设备
    """
    if not os.path.exists(to_config):
        print(f"配置文件 {to_config} 不存在，请先运行 write_config_to_json() 生成配置文件。")
        return

    # 首先上传配置文件到设备
    try:
        subprocess.run(["mpremote","connect", device_port, "cp", to_config, f":{os.path.basename(to_config)}"], check=True)
        print(f"已上传配置文件: {to_config}")
    except subprocess.CalledProcessError as e:
        print(f"上传配置文件失败: {to_config}, 错误: {e}")
    
    # 读取配置文件
    config = read_json_file(to_config)
    files = config.get("filesPath", [])
    print(f"开始上传 {len(files)} 个文件到设备...")

    for file_path in files:
        try:
            absolute_path = os.path.abspath(f"{rootdir}{file_path}")
            # 获取文件名（忽略子目录）
            file_name = os.path.basename(file_path)
            # 调用 mpremote 上传文件
            subprocess.run(["mpremote","connect", device_port, "cp", absolute_path, f":{file_name}"], check=True)
            print(f"已上传: {file_path}")
        except subprocess.CalledProcessError as e:
            print(f"上传失败: {file_path}, 错误: {e}")

    print("文件上传完成！")

if __name__ == "__main__":
    write_config_to_json()
    upload_files_to_device()