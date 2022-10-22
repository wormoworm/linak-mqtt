from smtplib import quotedata
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
    
    def _os_signal_handler(self, signum, frame):
        """Handle OS signal"""

        print(f"Received signal from OS ({signum}), shutting down gracefully...")
        self.stop()
        sys.exit()

    def __init__(self, config: LinakMqttConfig):

        self.config = config

        # Register a function to be invoked when we receive SIGTERM or SIGHUP.
        # This allows us to act on these events, which are sent by systemd when stopping the service.
        # signal.signal(signal.SIGTERM, self._os_signal_handler)
        # signal.signal(signal.SIGHUP, self._os_signal_handler)
        # signal.signal(signal.SIGINT, self._os_signal_handler)

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
        # self._loop.stop()

    async def main(self):
        try:
            while True:
                await asyncio.sleep(MAIN_LOOP_INTERVAL_S)
                self._get_and_publish_height()
        except (KeyboardInterrupt, SystemExit):
            # Keyboard interrupt (SIGINT) or exception triggered by sys.exit()
            self.stop()

    def on_mqtt_connected(self, client, userdata, flags, rc):
        self.subscribe_to_mqtt_topics()
        self._get_and_publish_height()

    def subscribe_to_mqtt_topics(self):
        self.mqtt_client.subscribe(topic = TOPIC_FORMAT_COMMANDS.format(self.config.client_id), qos = 1)
    
    def on_message_received(self, client, userdata, message):
        print(f"Message received on topic: {message.topic}")
        if message.topic == TOPIC_FORMAT_COMMANDS.format(self.config.client_id):
            self.process_command(json.loads(message.payload))
    
    def publish_height(self, height_raw):
        height_metres = self.controller.calculate_height_metres(height_raw)
        payload = {
            "timestamp": get_current_time_ms(),
            "height_raw": height_raw,
            "height_metres": height_metres
        }
        height_metres_net = self._calculate_height_metres_net(height_metres)
        if height_metres_net:
            payload["height_metres_net"] = height_metres_net
        self.mqtt_client.publish(topic = TOPIC_FORMAT_TELEMETRY.format(self.config.client_id), payload = json.dumps(payload), qos = 1)
    
    def _get_and_publish_height(self):
        self.publish_height(self.controller.get_height_raw())
    
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
        self.controller.move(height, self._set_height_tick_callback)
        self.publish_height()
    
    def process_stop_command(self, command: dict):
        self.controller.stop()
    
    def _set_height_tick_callback(self, height_raw):
        self.publish_height(height_raw)

    def _calculate_height_metres_net(self, height_metres):
        minimum_height = os.getenv("LINAK_MQTT_MINIMUM_HEIGHT")
        if minimum_height:
            return round(height_metres + float(minimum_height), 3)
        else:
            return None


"""Entrypoint"""
mqtt_config = LinakMqttConfig("10.0.1.2", 8884, os.getenv("LINAK_MQTT_CLIENT_ID"), os.getenv("LINAK_MQTT_USERNAME"), os.getenv("LINAK_MQTT_PASSWORD"))
linakMqtt = LinakMqtt(mqtt_config)