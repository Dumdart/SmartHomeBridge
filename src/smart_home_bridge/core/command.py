from __future__ import annotations

from abc import ABC, abstractmethod
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

Publishable = Callable[[str], Awaitable[None] | None]


class command(ABC):
    def __init__(self, publishable: Publishable | None = None):
        self.publishable = publishable

    async def publish(self, payload: str):
        if self.publishable is None:
            return

        result = self.publishable(payload)
        if inspect.isawaitable(result):
            await result

    @abstractmethod
    async def excecute(self) -> command_result:
        pass


@dataclass
class command_result:
    data: object | None = None
    success: bool = True
