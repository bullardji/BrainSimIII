from __future__ import annotations

"""Construct higher-level shapes from segments and arcs."""

import math
from typing import Iterable, List

from .module_base import ModuleBase
from vision.geometry import Segment, Arc
from vision.point_plus import PointPlus


class ModuleShape(ModuleBase):
    """Combine geometric primitives into simple shapes."""

    def __init__(self, segments: Iterable[Segment] | None = None, arcs: Iterable[Arc] | None = None):
        super().__init__()
        self.segments: List[Segment] = list(segments) if segments else []
        self.arcs: List[Arc] = list(arcs) if arcs else []
        self.shapes: List[dict] = []

    def set_primitives(self, segments: Iterable[Segment], arcs: Iterable[Arc]) -> None:
        self.segments = list(segments)
        self.arcs = list(arcs)

    def initialize(self) -> None:
        pass

    def fire(self) -> None:
        self.shapes = []
        self._detect_circle()
        self._detect_polygon()

    # --------------------------------------------------------------
    def _detect_circle(self) -> None:
        if len(self.arcs) == 1:
            arc = self.arcs[0]
            if abs(arc.extent - 2 * math.pi) < math.radians(5):
                self.shapes.append({"type": "circle", "center": arc.center, "radius": arc.radius})

    def _detect_polygon(self) -> None:
        if not self.segments:
            return
        pts: List[PointPlus] = [self.segments[0].start]
        for seg in self.segments:
            pts.append(seg.end)
        if pts[0].distance_to(pts[-1]) > 1e-6:
            return
        # simple polygon detection; right-angle heuristic for rectangles
        angles = []
        for i in range(1, len(pts) - 1):
            v1 = (pts[i].x - pts[i-1].x, pts[i].y - pts[i-1].y)
            v2 = (pts[i+1].x - pts[i].x, pts[i+1].y - pts[i].y)
            a1 = math.atan2(v1[1], v1[0])
            a2 = math.atan2(v2[1], v2[0])
            diff = (a2 - a1) % (2 * math.pi)
            angles.append(diff)
        if all(abs(a - math.pi/2) < math.radians(5) for a in angles):
            shape_type = "rectangle"
        else:
            shape_type = "polygon"
        self.shapes.append({"type": shape_type, "sides": len(self.segments)})

    def get_shapes(self) -> List[dict]:
        return list(self.shapes)
