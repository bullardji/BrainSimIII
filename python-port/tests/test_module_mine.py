import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import modules


def test_module_mine_discovery_and_activation():
    handler = modules.ModuleHandler()
    assert "ModuleMine" in handler.registry
    mod = handler.activate("ModuleMine")
    mod.fire()  # should run without error
    handler.deactivate(mod.label)
