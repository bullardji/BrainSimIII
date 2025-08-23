from __future__ import annotations

"""Maintain a simple mental model of detected shapes."""

from typing import Iterable, List, Dict

from .module_base import ModuleBase


class ModuleMentalModel(ModuleBase):
    """Store and retrieve shapes for downstream reasoning."""

    def __init__(self):
        super().__init__()
        self.shapes: List[Dict] = []

    def initialize(self) -> None:
        pass

    def ingest_shapes(self, shapes: Iterable[Dict]) -> None:
        self.shapes.extend(shapes)

    def fire(self) -> None:
        # The mental model is passive in this port; shapes are ingested from
        # other modules and retained for queries.
        pass

    def get_shape_count(self, shape_type: str | None = None) -> int:
        if shape_type is None:
            return len(self.shapes)
        return sum(1 for s in self.shapes if s.get("type") == shape_type)
