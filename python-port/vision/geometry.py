from __future__ import annotations

"""Geometry primitives used by advanced vision modules."""

from dataclasses import dataclass
from math import atan2, pi

from .point_plus import PointPlus


@dataclass(frozen=True)
class Segment:
    """Simple line segment defined by two :class:`PointPlus` instances."""

    start: PointPlus
    end: PointPlus

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)

    @property
    def angle(self) -> float:
        return atan2(self.end.y - self.start.y, self.end.x - self.start.x)


@dataclass(frozen=True)
class Arc:
    """Circular arc represented by centre, radius and start/end angles."""

    center: PointPlus
    radius: float
    start_angle: float
    end_angle: float

    @property
    def extent(self) -> float:
        return (self.end_angle - self.start_angle) % (2 * pi)
