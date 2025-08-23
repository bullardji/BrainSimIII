import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from PIL import Image

from modules.module_vision import ModuleVision


def test_edge_detection(tmp_path):
    img = Image.new("L", (2, 2), color=0)
    img.putpixel((0, 0), 255)
    path = tmp_path / "test.png"
    img.save(path)

    mod = ModuleVision(str(path))
    mod.initialize()
    assert mod.get_edge_count() > 0
