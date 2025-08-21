import time
import sys
from pathlib import Path

# Allow importing modules from the python-port directory
sys.path.append(str(Path(__file__).resolve().parents[1]))

from uks import UKS, Thing, ThingLabels, transient_relationships


def test_parent_child_and_ancestors():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    parent = uks.get_or_add_thing("animal")
    child = uks.get_or_add_thing("dog")
    child.add_parent(parent)
    assert child.Parents == [parent]
    assert parent.Children == [child]
    assert child.AncestorList() == [parent]


def test_transient_relationship_expiry():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    a = uks.get_or_add_thing("a")
    b = uks.get_or_add_thing("b")
    reltype = uks.get_or_add_thing("has-property")
    a.add_relationship(reltype, b, ttl=0.2)
    assert transient_relationships  # relationship registered
    time.sleep(0.5)
    uks.remove_expired_relationships()
    assert not transient_relationships
    assert not a.relationships


def test_add_statement_and_get_relationship():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    rel = uks.add_statement("cat", "is-a", "animal")
    fetched = uks.get_relationship("cat", "is-a", "animal")
    assert rel is fetched
    rel2 = uks.add_statement("cat", "is-a", "animal")
    assert rel2 is rel


def test_persistence_and_query(tmp_path):
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    uks.add_relationship("a", "likes", "b", weight=0.7)
    path = tmp_path / "uks.json"
    uks.save(str(path))
    uks2 = UKS()
    uks2.load(str(path))
    rels = uks2.query(source="a", reltype="likes", min_weight=0.5)
    assert len(rels) == 1


def test_event_hooks_and_conflict_resolution():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    added = []
    updated = []
    removed = []
    uks.on("add", lambda r: added.append(r))
    uks.on("update", lambda r: updated.append(r))
    uks.on("remove", lambda r: removed.append(r))

    rel = uks.add_relationship("a", "likes", "b", weight=0.1)
    assert added and not updated
    rel2 = uks.add_relationship("a", "likes", "b", weight=0.5)
    assert rel2 is rel
    assert updated and rel.weight == 0.5
    uks.remove_relationship(rel)
    assert removed


def test_label_autoincrement():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    a = uks.add_thing("node", None)
    b = uks.add_thing("node", None)
    c = uks.add_thing("node*", None)
    assert a.Label == "node"
    assert b.Label == "node0"
    assert c.Label == "node1"
