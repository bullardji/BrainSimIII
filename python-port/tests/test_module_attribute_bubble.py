from modules.module_attribute_bubble import ModuleAttributeBubble
from uks import UKS, ThingLabels, transient_relationships


def test_attribute_bubble_adds_parent_relationship():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    mod = ModuleAttributeBubble()
    mod.set_uks(uks)
    parent = uks.get_or_add_thing("Fruit", uks.labeled("Object"))
    color = uks.get_or_add_thing("color", uks.labeled("Object"))
    red = uks.get_or_add_thing("red", color)
    c1 = uks.get_or_add_thing("apple1", parent)
    c2 = uks.get_or_add_thing("apple2", parent)
    c1.add_relationship(color, red)
    c2.add_relationship(color, red)
    mod.do_the_work()
    assert uks.get_relationship(parent, color, red) is not None


def test_attribute_bubble_conflicting_children():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    mod = ModuleAttributeBubble()
    mod.set_uks(uks)
    parent = uks.get_or_add_thing("Fruit", uks.labeled("Object"))
    color = uks.get_or_add_thing("color", uks.labeled("Object"))
    red = uks.get_or_add_thing("red", color)
    blue = uks.get_or_add_thing("blue", color)
    has_prop = uks.get_or_add_thing("hasProperty", uks.labeled("Object"))
    exclusive = uks.get_or_add_thing("isExclusive", uks.labeled("Object"))
    color.add_relationship(has_prop, exclusive)
    c1 = uks.get_or_add_thing("apple1", parent)
    c2 = uks.get_or_add_thing("apple2", parent)
    c1.add_relationship(color, red)
    c2.add_relationship(color, blue)
    mod.do_the_work()
    assert uks.get_relationship(parent, color, red) is None
    assert uks.get_relationship(parent, color, blue) is None
