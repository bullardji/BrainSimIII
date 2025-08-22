import sys
from pathlib import Path

# Add python-port to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from modules.module_remove_redundancy import ModuleRemoveRedundancy
from uks import UKS, ThingLabels, transient_relationships


def test_module_remove_redundancy_prunes_child_attributes():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    parent = uks.get_or_add_thing("parent")
    child = uks.get_or_add_thing("child")
    child.add_parent(parent)
    reltype = uks.get_or_add_thing("has-color")
    color1 = uks.get_or_add_thing("red")
    color2 = uks.get_or_add_thing("blue")
    parent.add_relationship(reltype, color1, weight=1.0)
    parent.add_relationship(reltype, color2, weight=1.0)
    child.add_relationship(reltype, color1, weight=0.55)
    child.add_relationship(reltype, color2, weight=0.55)

    mod = ModuleRemoveRedundancy()
    mod.set_uks(uks)
    mod.is_enabled = True
    mod.do_the_work()

    assert uks.get_relationship("child", "has-color", "red") is None
    assert uks.get_relationship("child", "has-color", "blue") is None
