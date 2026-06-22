from abc import ABC, abstractmethod
from loxone_bridge.core.command import command, command_result


class device_controller(ABC):
    @abstractmethod
    def get_command(self, command: str) -> command:
        pass
    
    @abstractmethod
    async def excecute_command(self, command: str) -> command_result:
        pass
