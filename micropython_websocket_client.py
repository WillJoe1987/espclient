import usocket as socket
import ustruct as struct
import time
import json
from wificonnections import do_connect

class WebSocketClient:
    def __init__(self, url, access_token, device_mac, device_uuid):
        self.url = url
        self.access_token = access_token
        self.device_mac = device_mac
        self.device_uuid = device_uuid
        self.sock = None

    def connect(self):
        # 解析 WebSocket URL
        host, port, path = self._parse_url(self.url)
        
        # 建立 TCP 连接
        addr = socket.getaddrinfo(host, port)[0][-1]
        self.sock = socket.socket()
        self.sock.connect(addr)
        
        # 发送 WebSocket 握手请求
        self._handshake(host, port, path)

    def _parse_url(self, url):
        if not url.startswith("ws://"):
            raise ValueError("仅支持 ws:// 协议")
        url = url[5:]
        if "/" in url:
            host, path = url.split("/", 1)
            path = "/" + path
        else:
            host = url
            path = "/"  # 默认路径为 "/"
        if ":" in host:
            host, port = host.split(":")
            port = int(port)
        else:
            port = 80
        return host, port, path

    def _handshake(self, host, port, path):
        # 构造 WebSocket 握手请求
        headers = [
            f"GET {path} HTTP/1.1",
            f"Host: {host}:{port}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==",
            "Sec-WebSocket-Version: 13",
            f"Authorization: Bearer {self.access_token}",
            f"Protocol-Version: 1",
            f"Device-Id: {self.device_mac}",
            f"Client-Id: {self.device_uuid}",
            "\r\n"
        ]
        self.sock.send("\r\n".join(headers).encode("utf-8"))
        
        # 读取服务器响应
        response = self.sock.recv(1024).decode("utf-8")
        if "101 Switching Protocols" not in response:
            raise OSError("WebSocket 握手失败")

    def send(self, message):
        # 发送 WebSocket 数据帧
        frame = self._create_frame(message)
        self.sock.send(frame)

    def _create_frame(self, message):
        # 创建 WebSocket 数据帧
        message = message.encode("utf-8")
        length = len(message)
        if length <= 125:
            header = struct.pack("B", 0x81) + struct.pack("B", length)
        elif length <= 65535:
            header = struct.pack("B", 0x81) + struct.pack("B", 126) + struct.pack(">H", length)
        else:
            header = struct.pack("B", 0x81) + struct.pack("B", 127) + struct.pack(">Q", length)
        return header + message

    def recv(self):
        # 接收 WebSocket 数据帧
        header = self.sock.recv(2)
        if not header:
            return None
        length = header[1] & 0x7F
        if length == 126:
            length = struct.unpack(">H", self.sock.recv(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self.sock.recv(8))[0]
        return self.sock.recv(length).decode("utf-8")

    def close(self):
        # 关闭 WebSocket 连接
        if self.sock:  # 检查 self.sock 是否为 None
            self.sock.close()
            self.sock = None  # 确保关闭后将 self.sock 设置为 None

# 示例用法
def main():
    client = WebSocketClient(
        url="ws://139.155.252.64:7677",
        access_token="your_access_token",
        device_mac="your_device_mac",
        device_uuid="your_device_uuid"
    )
    try:
        print("连接到 WebSocket 服务器...")
        client.connect()
        print("连接成功！")
        
        # 发送握手消息
        hello_message = {
            "type": "1hello",
            "version": 1,
            "transport": "websocket",
            "audio_params": {
                "format": "opus",
                "sample_rate": 16000,
                "channels": 1,
                "frame_duration": 60
            }
        }
        client.send(json.dumps(hello_message))
        
        # 接收服务器响应
        response = client.recv()
        print("服务器响应:", response)
    finally:
        client.close()
        print("连接已关闭")

if __name__ == "__main__":
    if do_connect():
        main()
