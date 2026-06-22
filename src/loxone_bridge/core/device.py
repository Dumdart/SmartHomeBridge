from abc import ABC, abstractmethod

class device(ABC):  
    @abstractmethod
    def get_device_state(self):
        pass

    @abstractmethod
    def set_device_state(self, state):
        pass
    
