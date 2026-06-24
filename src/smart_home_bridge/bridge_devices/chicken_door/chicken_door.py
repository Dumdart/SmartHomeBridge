from enum import Enum
from smart_home_bridge.core.device import device


class door_position(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class chicken_door(device):
    def __init__(self, device_id, name, position: door_position):
        self.device_id = device_id
        self.name = name
        self.position = position
    
    def get_device_state(self):        
        return self.position

    def set_device_state(self, state):
        self.position = door_position(state)

    def open(self) -> door_position:
        self.position = door_position.OPEN
        return self.position

    def close(self) -> door_position:
        self.position = door_position.CLOSED
        return self.position

    def stop(self) -> door_position:
        return self.position
