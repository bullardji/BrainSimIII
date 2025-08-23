from __future__ import annotations

"""Detect line segments and circular arcs from edge points."""

import math
from typing import Iterable, List

from .module_base import ModuleBase
from vision.point_plus import PointPlus
from vision.geometry import Segment, Arc


class ModuleVisionFindSegmentsAndArcs(ModuleBase):
    """Analyse edge points to produce geometric primitives."""

    def __init__(self, edges: Iterable[PointPlus] | None = None):
        super().__init__()
        self.edges: List[PointPlus] = list(edges) if edges else []
        self.segments: List[Segment] = []
        self.arcs: List[Arc] = []

    def set_edges(self, edges: Iterable[PointPlus]) -> None:
        self.edges = list(edges)

    # --------------------------------------------------------------
    def initialize(self) -> None:
        pass

    def fire(self) -> None:
        self.segments, used = self._detect_segments(self.edges)
        remaining = [p for p in self.edges if p not in used]
        self.arcs = self._detect_arcs(remaining)

    # --------------------------------------------------------------
    @staticmethod
    def _detect_segments(points: List[PointPlus], tol: float = 0.01) -> tuple[List[Segment], set[PointPlus]]:
        segments: List[Segment] = []
        used: set[PointPlus] = set()
        i = 0
        n = len(points)
        while i < n - 1:
            j = i + 1
            while j < n:
                if j - i < 2:
                    j += 1
                    continue
                if not ModuleVisionFindSegmentsAndArcs._collinear(points[i], points[j], points[i + 1:j], tol):
                    break
                j += 1
            if j - i >= 3:
                seg = Segment(points[i], points[j - 1])
                segments.append(seg)
                used.update(points[i:j])
            i = j
        return segments, used

    @staticmethod
    def _collinear(p1: PointPlus, p2: PointPlus, pts: Iterable[PointPlus], tol: float) -> bool:
        for p in pts:
            area = abs(p1.x * (p2.y - p.y) + p2.x * (p.y - p1.y) + p.x * (p1.y - p2.y))
            if area > tol:
                return False
        return True

    # --------------------------------------------------------------
    @staticmethod
    def _circle_from_points(p1: PointPlus, p2: PointPlus, p3: PointPlus):
        """Return center and radius of circle through three points."""
        temp = p2.x ** 2 + p2.y ** 2
        bc = (p1.x ** 2 + p1.y ** 2 - temp) / 2.0
        cd = (temp - p3.x ** 2 - p3.y ** 2) / 2.0
        det = (p1.x - p2.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p2.y)
        if abs(det) < 1e-6:
            return None
        cx = (bc * (p2.y - p3.y) - cd * (p1.y - p2.y)) / det
        cy = ((p1.x - p2.x) * cd - (p2.x - p3.x) * bc) / det
        center = PointPlus(cx, cy)
        radius = center.distance_to(p1)
        return center, radius

    @classmethod
    def _detect_arcs(cls, points: List[PointPlus], tol: float = 1.0) -> List[Arc]:
        if len(points) < 3:
            return []
        arcs: List[Arc] = []
        pts = list(points)
        center_radius = cls._circle_from_points(pts[0], pts[1], pts[2])
        if not center_radius:
            return []
        center, radius = center_radius
        for p in pts:
            if abs(center.distance_to(p) - radius) > tol:
                return []
        start_angle = math.atan2(pts[0].y - center.y, pts[0].x - center.x)
        end_angle = math.atan2(pts[-1].y - center.y, pts[-1].x - center.x)
        arcs.append(Arc(center, radius, start_angle, end_angle))
        return arcs
