import time
import ujson
import _thread
from board.board import BLEWifiBoard
from protocol.protocol import WebsocketProtocol
from iot.things import ThingManager

class Application:
    _instance = None

    @staticmethod
    def get_instance():
        if Application._instance is None:
            Application._instance = Application()
        return Application._instance

    def __init__(self):
        if Application._instance is not None:
            raise Exception("This class is a singleton!")
        self.device_state = "unknown"
        self.protocol = None
        self.thing_manager = ThingManager()
        self.tasks = []
        self.lock = _thread.allocate_lock()
        self.clock_ticks = 0
        self.aborted = False
        self.voice_detected = False

    def start(self):
        board = BLEWifiBoard()
        self.set_device_state("starting")

        # Initialize protocol
        self.protocol = WebsocketProtocol(None)
        self.protocol.on_network_error(self.on_network_error)
        self.protocol.on_incoming_audio(self.on_incoming_audio)
        self.protocol.on_audio_channel_opened(self.on_audio_channel_opened)
        self.protocol.on_audio_channel_closed(self.on_audio_channel_closed)
        self.protocol.on_incoming_json(self.on_incoming_json)
        self.protocol.start()

        # Start main loop
        _thread.start_new_thread(self.main_loop, ())

        # Start clock timer
        _thread.start_new_thread(self.clock_timer, ())

        # Set device to idle state
        self.set_device_state("idle")

    def set_device_state(self, state):
        if self.device_state == state:
            return
        self.device_state = state
        print(f"Device state changed to: {state}")

    def schedule(self, task):
        with self.lock:
            self.tasks.append(task)

    def main_loop(self):
        while True:
            with self.lock:
                tasks = self.tasks[:]
                self.tasks.clear()
            for task in tasks:
                task()
            time.sleep(0.1)

    def clock_timer(self):
        while True:
            self.clock_ticks += 1
            if self.clock_ticks % 10 == 0:
                print("Clock tick: ", self.clock_ticks)
            time.sleep(1)

    def on_network_error(self, message):
        self.set_device_state("idle")
        print(f"Network error: {message}")

    def on_incoming_audio(self, data):
        print("Incoming audio data received")

    def on_audio_channel_opened(self):
        print("Audio channel opened")
        descriptors = self.thing_manager.get_descriptors_json()
        self.protocol.send_iot_descriptors(descriptors)
        states, _ = self.thing_manager.get_states_json(delta=False)
        self.protocol.send_iot_states(states)

    def on_audio_channel_closed(self):
        print("Audio channel closed")
        self.set_device_state("idle")

    def on_incoming_json(self, data):
        print("Incoming JSON data:", data)
        if data.get("type") == "iot":
            commands = data.get("commands", [])
            for command in commands:
                self.thing_manager.invoke(command)

    def update_iot_states(self):
        states, changed = self.thing_manager.get_states_json(delta=True)
        if changed:
            self.protocol.send_iot_states(states)

    def reboot(self):
        print("Rebooting device...")
        time.sleep(1)
        # Simulate reboot by resetting the application instance
        Application._instance = None
        Application.get_instance().start()
