from linak_desk_control import LinakController
from paho.mqtt.client import Client
from time_utils import get_current_time_ms
import os
import sys
import signal
import json
import asyncio

TOPIC_FORMAT_TELEMETRY = "devices/linak/{}/telemetry"
TOPIC_FORMAT_COMMANDS = "devices/linak/{}/commands"

COMMAND_SET_HEIGHT = "set_height"
COMMAND_STOP = "stop"
COMMAND_REQUEST_HEIGHT = "request_height"

MAIN_LOOP_INTERVAL_S = 5

class LinakMqttConfig:
    """Contains config data used by the LinakMqtt controller class."""

    def __init__(self, endpoint: str, port: int, client_id: str, username: str, password: str) -> None:
        pass
        self.endpoint = endpoint
        self.port = port
        self.client_id = client_id
        self.username = username
        self.password = password


class LinakMqtt:

    def __init__(self, config: LinakMqttConfig):

        self.config = config

        # Register a function to be invoked when we receive SIGTERM or SIGHUP.
        # This allows us to act on these events, which are sent by systemd when stopping the service.
        signal.signal(signal.SIGTERM, self._os_signal_handler)
        signal.signal(signal.SIGHUP, self._os_signal_handler)

        # Initialise USB device
        self.controller = LinakController()

        # Connect to MQTT
        self.mqtt_client = Client(self.config.client_id)
        self.mqtt_client.on_connect = self.on_mqtt_connected
        self.mqtt_client.on_message = self.on_message_received
        
        print(f"Setting MQTT username / password: {self.config.username} / {self.config.password}")
        self.mqtt_client.username_pw_set(self.config.username, self.config.password)
        
        print(f"About to connect to MQTT")
        self.mqtt_client.connect_async(host = self.config.endpoint, port = self.config.port)
        self.mqtt_client.loop_start()

        self._loop = asyncio.get_event_loop()
        self._loop.create_task(self.main())
        self._loop.run_forever()
    
    def stop(self):
        """Stop application"""
        print("Stopping...")
        # Stop event loop
        self._loop.stop()
    
    def _os_signal_handler(self, signum, frame):
        """Handle OS signal"""

        print("Received signal from OS ({0}), shutting down gracefully...".format(signum), force_display = True)
        self.stop()
        sys.exit()

    async def main(self):
        try:
            while True:
                await asyncio.sleep(MAIN_LOOP_INTERVAL_S)
                self.publish_height()
        except (KeyboardInterrupt, SystemExit):
            # Keyboard interrupt (SIGINT) or exception triggered by sys.exit()
            self.stop()

    def on_mqtt_connected(self, client, userdata, flags, rc):
        self.subscribe_to_mqtt_topics()
        
        # Publish current height
        self.publish_height()

    def subscribe_to_mqtt_topics(self):
        self.mqtt_client.subscribe(topic = TOPIC_FORMAT_COMMANDS.format(self.config.client_id))
    
    def on_message_received(self, client, userdata, message):
        print(f"Message received on topic: {message.topic}")
        if message.topic == TOPIC_FORMAT_COMMANDS.format(self.config.client_id):
            self.process_command(json.loads(message.payload))
    
    def publish_height(self):
        height_raw, height_m = self.controller.getHeight()
        payload = {
            "timestamp": get_current_time_ms(),
            "height_raw": height_raw,
            "height_m": height_m
        }
        self.mqtt_client.publish(topic = TOPIC_FORMAT_TELEMETRY.format(self.config.client_id), payload = json.dumps(payload), qos = 1)
    
    def process_command(self, command):
        print(command)
        command_type = command.get("type")
        if not command_type:
            print("Command type not provided, ignoring command")
            return
        if command_type == COMMAND_REQUEST_HEIGHT:
            self.process_request_height_command(command)
        elif command_type == COMMAND_SET_HEIGHT:
            self.process_set_height_command(command)
        elif command_type == COMMAND_STOP:
            self.process_stop_command(command)
        else:
            print(f"Command type \"{command_type}\" is not supported, ignoring command")
    
    def process_request_height_command(self, command: dict):
        self.publish_height()
    
    def process_set_height_command(self, command: dict):
        height = command.get("height", None)
        if not height:
            print("Height not provided, ignoring set_height command")
        self.controller.move(height)
        self.publish_height()
    
    def process_stop_command(self, command: dict):
        self.controller.stop()


"""Entrypoint"""
mqtt_config = LinakMqttConfig("10.0.1.2", 8884, os.getenv("LINAK_MQTT_CLIENT_ID"), os.getenv("LINAK_MQTT_USERNAME"), os.getenv("LINAK_MQTT_PASSWORD"))
linakMqtt = LinakMqtt(mqtt_config)