import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from modules import ModuleHandler


def test_module_class_create_creates_subclass():
    handler = ModuleHandler()
    module = handler.activate("ModuleClassCreate")
    module.is_enabled = True
    module.min_common_attributes = 2
    uks = handler.the_uks
    root = uks.labeled("Object")
    animal = uks.get_or_add_thing("Animal", root)
    cat = uks.get_or_add_thing("cat", animal)
    dog = uks.get_or_add_thing("dog", animal)
    tail = uks.get_or_add_thing("tail")
    has = uks.get_or_add_thing("has")
    cat.add_relationship(has, tail)
    dog.add_relationship(has, tail)
    module.do_the_work()
    new_parent = uks.labeled("Animal.has.tail")
    assert new_parent is not None
    assert new_parent in cat.Parents and new_parent in dog.Parents
    assert animal not in cat.Parents
    module.cancel_timer()
