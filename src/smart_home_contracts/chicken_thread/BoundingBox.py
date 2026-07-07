from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BoundingBox:
    left: float
    top: float
    right: float
    bottom: float
    normalized: bool = True

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> BoundingBox:
        return cls(
            left=float(data["left"]),
            top=float(data["top"]),
            right=float(data["right"]),
            bottom=float(data["bottom"]),
            normalized=bool(data.get("normalized", True)),
        )

    def to_dict(self) -> dict[str, float | bool]:
        return {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "normalized": self.normalized,
        }
