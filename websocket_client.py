import asyncio
import websockets
import json

class WebSocketClient:
    def __init__(self, access_token, device_mac, device_uuid):
        self.url = "ws://139.155.252.64:7677"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Protocol-Version": "1",
            "Device-Id": device_mac,
            "Client-Id": device_uuid
        }

    async def connect(self):
        self.connection = await websockets.connect(self.url, extra_headers=self.headers)

    async def hello(self):
        # 构造握手报文
        hello_message = {
            "type": "hello",
            "version": 1,
            "transport": "websocket",
            "audio_params": {
                "format": "opus",
                "sample_rate": 16000,
                "channels": 1,
                "frame_duration": 60
            }
        }
        # 发送握手报文
        await self.connection.send(json.dumps(hello_message))
        # 接收服务器响应
        response = await self.connection.recv()
        return json.loads(response)

    async def close(self):
        await self.connection.close()

# 示例用法
async def main():
    client = WebSocketClient(
        access_token="your_access_token",
        device_mac="your_device_mac",
        device_uuid="your_device_uuid"
    )
    await client.connect()
    response = await client.hello()
    print("Server response:", response)
    await client.close()

# 如果需要运行此脚本，请取消下面的注释
asyncio.run(main())
