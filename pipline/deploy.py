import json,os
#本代码用于在eps32开发板上执行部署操作，主要基于micropython的基础库进行操作。
#由于rt-thread-micropython插件的能力限制，目前只能逐文件部署，不能进行目录的递归部署。
#代码上传后都位于根目录下，导致根据包名的引用关系出错；
#因此，需要手动逐个文件调整目录结构。
# 目前的解决方案是：
# 1. 通过deploybuilder.py脚本，自动生成文件目录结构配置文件deploy.json，并上传deploy.json以及相关代码到设备上。
# 2. 在设备上执行deploy.py脚本，自动调整目录结构

#本脚本仅执行第四步操作，即，根据deploy.json文件，自动调整目录结构。

def read_json_file(file_path):
    """
    读取JSON文件并返回内容
    """
    with open(file_path, 'r') as file:
        return json.load(file)

deploy_config = "/deploy.json"

CHECKING_TYPE_NONE = 0
CHECKING_TYPE_FILE = 1
CHECKING_TYPE_DIR = 2

def check_type(path):
    if not _check_exsit(path):
        return CHECKING_TYPE_NONE
    try:
        os.chdir(path)
        os.chdir('..')
        return CHECKING_TYPE_DIR
    except OSError:
        return CHECKING_TYPE_FILE

def _check_exsit(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False
    
def check_root_exsit(filename):
    os.chdir('/')
    return _check_exsit(filename)

def check_and_mkdir(path):
    os.chdir('/')
    log_p = ""
    for p in path:
        log_p += "/" + p
        path_type = check_type(p)
        if path_type == CHECKING_TYPE_NONE:
            print(f"Path does not exist: {log_p}")
            os.mkdir(p)  # 创建目录
            os.chdir(p)  # 切换到新创建的目录
        elif path_type == CHECKING_TYPE_FILE:
            print(f"Path is a file: {log_p}")
            os.chdir('/')  # 切换到文件所在目录
            raise OSError(f"Path is a file: {log_p}")
        elif path_type == CHECKING_TYPE_DIR:
            print(f"Path is a directory: {log_p}")
            os.chdir(p)  # 切换到目录
    os.chdir('/')  # 切换回根目录

def deploy_file(file_path):

    # 如果目标目录是根目录，则不做任何操作
    if "/" not in file_path:
        print(f"root file : {file_path}")
        return 0
    
    # 获取文件名
    file_name = file_path.split("/")[-1]  # 使用字符串分割获取文件名
    # 获取目标目录
    target_dir = file_path.split("/")[:-1]  # 使用字符串分割获取目录路径


    # 检查文件是否存在
    if not check_root_exsit(file_name):
        print(f"no file at root : {file_name}")
        return 0
    

    """
    将文件移动到指定目录
    """
    try:
        # 创建目标目录（如果不存在）
        check_and_mkdir(target_dir)
        # 移动文件
        os.rename(file_name, file_path)
        print(f"renamed : {file_path}")
        return 1
    except Exception as e:
        print(f"failed one : {e}")
        return 0

def deploy_files(deploy_config):
    """
    根据deploy.json文件的配置，调整目录结构
    """
    config = read_json_file(deploy_config)
    files = config.get("filesPath", [])
    print("configuared file totol :", len(files))
    file_count = 0
    for file_path in files:
        file_count += deploy_file(file_path)
    
    print(f"configuared file totol:{len(files)}, and deploied : {file_count} files.")

exclude_clean = [".mpyproject.json", "deploy.json", "deploy.py"]

def clean():
    """
    清理根目录下的所有文件和目录，排除 exclude_clean 中的文件
    """
    os.chdir('/')
    files = os.listdir()
    for f in files:
        if f not in exclude_clean:
            try:
                # 检查是否是目录
                if check_type(f) == CHECKING_TYPE_DIR:
                    delete_dir_recursive(f)  # 递归删除目录
                    print(f"delete dir : {f}")
                else:
                    os.remove(f)  # 删除文件
                    print(f"delete file : {f}")
            except OSError as e:
                print(f"Failed to delete {f}: {e}")
    print("clean done.")

def delete_dir_recursive(directory):
    """
    递归删除目录及其内容
    """
    os.chdir(directory)
    for item in os.listdir():
        item_path = f"{item}"
        if check_type(item_path) == CHECKING_TYPE_DIR:
            delete_dir_recursive(item_path)  # 递归删除子目录
        else:
            os.remove(item_path)  # 删除文件
            print(f"delete file : {item_path}")
    os.chdir('..')  # 返回上级目录
    os.rmdir(directory)  # 删除空目录

if __name__ == "__main__":
    deploy_files(deploy_config)
    # clean()