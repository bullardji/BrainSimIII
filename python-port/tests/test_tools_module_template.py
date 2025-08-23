import sys
from pathlib import Path

# Allow importing from python-port directory
sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools import create_module


def test_create_module(tmp_path):
    path = create_module("Demo", tmp_path)
    assert path.name == "module_demo.py"
    content = path.read_text()
    assert "class ModuleDemo" in content
    assert "ModuleBase" in content


