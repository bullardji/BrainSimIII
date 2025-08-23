"""PointPlus geometry helpers.

This module translates the richer C# ``PointPlus`` utility.  It supports
cartesian and polar coordinates, confidence values, basic 3‑D handling and a
number of convenience operators so geometry code can stay concise.  The aim is
not raw performance but feature parity with the original helpers which underpin
several vision modules.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Iterator


@dataclass(frozen=True)
class PointPlus:
    x: float
    y: float
    z: float = 0.0
    confidence: float = 1.0

    # ------------------------------------------------------------------
    # Constructors / conversions
    # ------------------------------------------------------------------
    @staticmethod
    def from_polar(radius: float, angle: float, confidence: float = 1.0) -> "PointPlus":
        """Create a point from polar coordinates (2‑D)."""
        return PointPlus(radius * math.cos(angle), radius * math.sin(angle), 0.0, confidence)

    def to_polar(self) -> tuple[float, float]:
        """Return (radius, angle) for the X/Y components."""
        radius = math.hypot(self.x, self.y)
        angle = math.atan2(self.y, self.x)
        return (radius, angle)

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    # ------------------------------------------------------------------
    # Operator overloads
    # ------------------------------------------------------------------
    def __add__(self, other: "PointPlus") -> "PointPlus":
        conf = (self.confidence + other.confidence) / 2.0
        return PointPlus(self.x + other.x, self.y + other.y, self.z + other.z, conf)

    def __sub__(self, other: "PointPlus") -> "PointPlus":
        conf = (self.confidence + other.confidence) / 2.0
        return PointPlus(self.x - other.x, self.y - other.y, self.z - other.z, conf)

    def __mul__(self, factor: float) -> "PointPlus":
        return PointPlus(self.x * factor, self.y * factor, self.z * factor, self.confidence)

    __rmul__ = __mul__

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------
    def distance_to(self, other: "PointPlus") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2)

    def rotate(self, angle: float) -> "PointPlus":
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        x = self.x * cos_a - self.y * sin_a
        y = self.x * sin_a + self.y * cos_a
        return PointPlus(x, y, self.z, self.confidence)

    # ------------------------------------------------------------------
    # Iteration & representation helpers
    # ------------------------------------------------------------------
    def __iter__(self) -> Iterator[float]:
        yield from (self.x, self.y, self.z)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"PointPlus(x={self.x:.3f}, y={self.y:.3f}, z={self.z:.3f}, confidence={self.confidence:.3f})"
