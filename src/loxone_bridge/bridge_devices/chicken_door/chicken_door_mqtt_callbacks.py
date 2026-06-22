import asyncio

from loxone_bridge.bridge_devices.chicken_door.door_controller import door_controller
from loxone_bridge.infrastructure.mqtt.mqtt_callbacks import mqtt_callbacks


class chicken_door_mqtt_callbacks(mqtt_callbacks):
    def __init__(self, door_controller: door_controller):
        super().__init__()
        self.door_controller = door_controller
        
    def on_message(self, client, userdata, msg): 
        try:
            command = msg.payload.decode().strip()
            print(f"Received message on topic {msg.topic}: {command}")

            return asyncio.run(self.door_controller.excecute_command(command))
            
        except Exception as e:      
            print(f"Message is not a command: {e}")

            
    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        print("Subscribed: " + str(mid) + " " + str(granted_qos))

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print("CONNACK received with code %s." % rc)

    def on_disconnect(self, client, userdata, rc, properties=None):
        print("Disconnected with code %s." % rc)

    def on_publish(self, client, userdata, mid, properties=None):
        print("Publish: " + str(mid))

    def on_unsubscribe(self, client, userdata, mid, properties=None):
        print("Unsubscribed: " + str(mid))
