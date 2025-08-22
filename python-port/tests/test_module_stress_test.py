import sys
from pathlib import Path

# Add python-port to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from modules.module_stress_test import ModuleStressTest
from uks import UKS, ThingLabels, transient_relationships


def test_add_many_test_items_inserts_hierarchy():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    mod = ModuleStressTest()
    mod.set_uks(uks)
    message = mod.add_many_test_items(10)
    assert message == "Items added successfully."
    # At least 10 things should have been created
    assert len(uks.UKSList) >= 10
    # Verify hierarchical names exist
    assert uks.labeled("A0") is not None
    assert uks.labeled("B00") is not None
    assert uks.labeled("C000") is not None


def test_add_many_test_items_invalid_counts():
    uks = UKS()
    mod = ModuleStressTest()
    mod.set_uks(uks)
    assert "cannot commence" in mod.add_many_test_items(0)
    assert "cannot commence" in mod.add_many_test_items(100001)
