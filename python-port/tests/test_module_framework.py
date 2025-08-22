import sys
import sys
from pathlib import Path

# Allow importing modules from the python-port directory
sys.path.append(str(Path(__file__).resolve().parents[1]))

from modules import ModuleBase, ModuleHandler
from uks import UKS, ThingLabels, transient_relationships


class DummyModule(ModuleBase):
    def initialize(self) -> None:
        self.counter = 0

    def pre_step(self) -> None:
        self.counter += 1

    def fire(self) -> None:
        self.counter += 1

    def post_step(self) -> None:
        self.counter += 1

    def get_parameters(self) -> dict:
        return {"counter": self.counter}

    def set_parameters(self, params: dict) -> None:
        self.counter = params.get("counter", 0)


def test_module_handler_activation_and_fire():
    handler = ModuleHandler()
    handler.register(DummyModule, "dummy")
    module = handler.activate("DummyModule")
    assert module.initialized
    assert module.counter == 0

    handler.fire_modules()
    # pre_step + fire + post_step -> +3
    assert module.counter == 3

    handler.deactivate(module.label)
    assert handler.active_modules == []

    # Test serialization
    module = DummyModule()
    module.set_parameters({"counter": 7})
    data = module.serialize()
    restored = DummyModule.deserialize(data)
    assert restored.counter == 7

    # ModuleHandler serialization/deserialization
    handler.register(DummyModule, "dummy")
    m = handler.activate("DummyModule")
    m.counter = 2
    dumped = handler.serialize_active()
    handler.active_modules = []
    handler.load_active(dumped)
    assert handler.active_modules[0].counter == 2

    # Dynamic discovery should have picked up built-in modules
    assert "ModuleAddCounts" in handler.registry


def test_uks_relationships():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    uks.add_relationship("A", "parent", "B")
    a = uks.labeled("A")
    assert a.relationships[0].reltype.Label == "parent"
    assert a.relationships[0].target.Label == "B"
