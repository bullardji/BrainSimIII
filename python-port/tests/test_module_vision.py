import sys
from pathlib import Path
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore

from modules.module_vision import ModuleVision


def test_edge_detection(tmp_path):
    if Image is None:
        pytest.skip("Pillow not available")
    img = Image.new("L", (2, 2), color=0)
    img.putpixel((0, 0), 255)
    path = tmp_path / "test.png"
    img.save(path)

    mod = ModuleVision(str(path))
    mod.initialize()
    assert mod.get_edge_count() > 0
