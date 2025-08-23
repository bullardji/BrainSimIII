import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from modules import ModuleHandler


def test_module_uks_clause_add_relationship():
    handler = ModuleHandler()
    module = handler.activate("ModuleUKSClause")
    module.add_relationship("big dogs", "small cats", "has part")

    uks = handler.the_uks
    dog = uks.labeled("dog")
    cat = uks.labeled("cat")
    big = uks.labeled("big")
    small = uks.labeled("small")
    has = uks.labeled("has")
    part = uks.labeled("part")

    assert uks.get_relationship(dog, has, cat) is not None
    assert uks.get_relationship(dog, "is", big) is not None
    assert uks.get_relationship(cat, "is", small) is not None
    assert uks.get_relationship(has, "hasProperty", part) is not None


def test_module_uks_clause_relationship_types():
    handler = ModuleHandler()
    module = handler.activate("ModuleUKSClause")
    module.add_relationship("dog", "cat", "chases")
    types = module.relationship_types()
    assert "chase" in types
