import sys
from pathlib import Path

# Add python-port to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from modules.module_add_counts import ModuleAddCounts
from uks import UKS, ThingLabels, transient_relationships


def test_module_add_counts_creates_aggregate_relationships():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()

    thing = uks.get_or_add_thing("thing")
    reltype = uks.get_or_add_thing("has-attr")
    unknown = uks.labeled("unknownObject")
    group = uks.add_thing("group", unknown)
    target1 = uks.add_thing("target1", group)
    target2 = uks.add_thing("target2", group)

    thing.add_relationship(reltype, target1)
    thing.add_relationship(reltype, target2)

    mod = ModuleAddCounts()
    mod.set_uks(uks)
    mod.is_enabled = True
    mod.do_the_work()

    assert uks.get_relationship("thing", "has-attr.2", "group") is not None


