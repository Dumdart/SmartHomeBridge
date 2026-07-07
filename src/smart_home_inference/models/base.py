from typing import Protocol

from smart_home_contracts.chicken_thread import DetectionFrame


class InferenceModel(Protocol):
    identifier: str

    def ready(self) -> tuple[bool, str | None]:
        ...

    def infer(self, image_bytes: bytes, source: str | None = None) -> DetectionFrame:
        ...
