from __future__ import annotations
from pathlib import Path
from typing import List

from PIL import Image, ImageFilter

from .module_base import ModuleBase
from vision.point_plus import PointPlus


class ModuleVision(ModuleBase):
    """Very small vision subsystem that detects edges using Pillow."""

    def __init__(self, image_path: str | None = None):
        super().__init__()
        self.image_path = image_path
        self.edges: List[PointPlus] = []

    def initialize(self) -> None:
        if self.image_path:
            self.load_image(self.image_path)

    def load_image(self, path: str) -> None:
        img = Image.open(path).convert("L")
        edge_img = img.filter(ImageFilter.FIND_EDGES)
        width, height = edge_img.size
        pixels = edge_img.load()
        self.edges.clear()
        for y in range(height):
            for x in range(width):
                if pixels[x, y] > 0:
                    self.edges.append(PointPlus(x, y))

    def get_edge_count(self) -> int:
        return len(self.edges)
