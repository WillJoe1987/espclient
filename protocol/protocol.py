import ujson
import time
import machine
import ubinascii

class Protocol:
    def __init__(self):
        self.server_sample_rate = 24000
        self.server_frame_duration = 60
        self.session_id = self._generate_session_id()
        self.error_occurred = False
        self.last_incoming_time = time.ticks_ms()

    def _generate_session_id(self):
        # 使用设备的MAC地址生成唯一的会话ID
        mac = ubinascii.hexlify(machine.unique_id()).decode()
        return f"session-{mac}"

    def on_incoming_audio(self, callback):
        self.on_incoming_audio_callback = callback

    def on_incoming_json(self, callback):
        self.on_incoming_json_callback = callback

    def on_audio_channel_opened(self, callback):
        self.on_audio_channel_opened_callback = callback

    def on_audio_channel_closed(self, callback):
        self.on_audio_channel_closed_callback = callback

    def on_network_error(self, callback):
        self.on_network_error_callback = callback

    def send_text(self, text):
        raise NotImplementedError("send_text must be implemented by subclasses")

    def set_error(self, message):
        self.error_occurred = True
        if hasattr(self, "on_network_error_callback"):
            self.on_network_error_callback(message)

    def is_timeout(self):
        timeout_seconds = 120 * 1000  # 120 seconds in milliseconds
        elapsed_time = time.ticks_diff(time.ticks_ms(), self.last_incoming_time)
        return elapsed_time > timeout_seconds

    def send_abort_speaking(self, reason):
        message = {"session_id": self.session_id, "type": "abort", "reason": reason}
        self.send_text(ujson.dumps(message))

    def send_start_listening(self, mode):
        message = {"session_id": self.session_id, "type": "listen", "state": "start", "mode": mode}
        self.send_text(ujson.dumps(message))

    def send_stop_listening(self):
        message = {"session_id": self.session_id, "type": "listen", "state": "stop"}
        self.send_text(ujson.dumps(message))

    def send_iot_descriptors(self, descriptors):
        try:
            descriptor_list = ujson.loads(descriptors)
            if not isinstance(descriptor_list, list):
                raise ValueError("Descriptors should be a list")
            for descriptor in descriptor_list:
                message = {
                    "session_id": self.session_id,
                    "type": "iot",
                    "update": True,
                    "descriptors": [descriptor],
                }
                self.send_text(ujson.dumps(message))
        except ValueError as e:
            self.set_error(f"Failed to parse IoT descriptors: {str(e)}")

    def send_iot_states(self, states):
        message = {
            "session_id": self.session_id,
            "type": "iot",
            "update": True,
            "states": ujson.loads(states),
        }
        self.send_text(ujson.dumps(message))


class WebsocketProtocol(Protocol):
    def __init__(self, websocket):
        super().__init__()
        self.websocket = websocket

    def start(self):
        pass  # Placeholder for starting the protocol

    def send_audio(self, data):
        if not self.websocket:
            return
        self.websocket.send(data)

    def send_text(self, text):
        if not self.websocket:
            return
        try:
            self.websocket.send(text)
        except Exception as e:
            self.set_error(f"Failed to send text: {str(e)}")

    def is_audio_channel_opened(self):
        return self.websocket is not None and not self.error_occurred and not self.is_timeout()

    def close_audio_channel(self):
        if self.websocket:
            self.websocket.close()
            self.websocket = None

    def open_audio_channel(self, url, headers):
        try:
            self.websocket.connect(url, headers=headers)
            self.websocket.on_message(self._on_message)
            self.websocket.on_close(self._on_close)
            self.websocket.send(ujson.dumps({"type": "hello", "version": 1}))
            if hasattr(self, "on_audio_channel_opened_callback"):
                self.on_audio_channel_opened_callback()
            return True
        except Exception as e:
            self.set_error(f"Failed to open audio channel: {str(e)}")
            return False

    def _on_message(self, message):
        try:
            data = ujson.loads(message)
            if "type" in data and data["type"] == "hello":
                self._parse_server_hello(data)
            elif hasattr(self, "on_incoming_json_callback"):
                self.on_incoming_json_callback(data)
            self.last_incoming_time = time.ticks_ms()
        except ValueError:
            if hasattr(self, "on_incoming_audio_callback"):
                self.on_incoming_audio_callback(message)

    def _on_close(self):
        if hasattr(self, "on_audio_channel_closed_callback"):
            self.on_audio_channel_closed_callback()

    def _parse_server_hello(self, data):
        if "audio_params" in data:
            params = data["audio_params"]
            self.server_sample_rate = params.get("sample_rate", self.server_sample_rate)
            self.server_frame_duration = params.get("frame_duration", self.server_frame_duration)
