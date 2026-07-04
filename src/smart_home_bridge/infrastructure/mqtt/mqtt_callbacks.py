from abc import ABC, abstractmethod


class mqtt_callbacks(ABC):
    @abstractmethod
    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        pass

    @abstractmethod
    def on_connect(self, client, userdata, flags, rc, properties=None):
        pass
    
    @abstractmethod
    def on_disconnect(self, client, userdata, disconnect_flags, reason_code=None, properties=None):
        code = reason_code if reason_code is not None else disconnect_flags
        print("Disconnected with code %s." % code)

    @abstractmethod
    def on_publish(self, client, userdata, mid, reason_code=None, properties=None):
        print("Publish: " + str(mid))

    @abstractmethod
    def on_unsubscribe(self, client, userdata, mid, properties=None):
        pass

    @abstractmethod
    def on_message(self, client, userdata, msg):
        pass
