import time
import sys
from pathlib import Path

# Allow importing modules from the python-port directory
sys.path.append(str(Path(__file__).resolve().parents[1]))

from uks import UKS, Thing, ThingLabels, transient_relationships, Relationship, Statement



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
    uks.shutdown()


def test_add_statement_and_get_relationship():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    rel = uks.add_statement("cat", "is-a", "animal")
    fetched = uks.get_relationship("cat", "is-a", "animal")
    assert rel is fetched
    rel2 = uks.add_statement("cat", "is-a", "animal")
    assert rel2 is rel
    uks.shutdown()


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
    uks.shutdown()


def test_relationship_hash_and_labels_threadsafe():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    a = uks.get_or_add_thing("a")
    b = uks.get_or_add_thing("b")
    rt = uks.get_or_add_thing("r")
    r1 = Relationship(a, rt, b)
    r2 = Relationship(a, rt, b)
    s = {r1}
    assert r2 in s and r1 == r2

    # Thread-safe label assignment
    import threading

    def worker(idx: int) -> None:
        uks.add_thing(f"T{idx}", None)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ThingLabels.labels()) >= 10
    uks.shutdown()


def test_thing_attribute_helpers_extended():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    t = uks.get_or_add_thing("t")
    prop = uks.get_or_add_thing("prop")
    allow = uks.get_or_add_thing("allow")
    t.set_property(prop)
    t.set_allows(allow)
    attrs = t.get_attributes()
    assert prop in attrs and allow in attrs
    uks.shutdown()


def test_statement_round_trip_and_merge(tmp_path):
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    stmt = Statement("a", "likes", "b", ttl=5, weight=0.3)
    rel = stmt.to_relationship(uks)
    assert rel.weight == 0.3
    exported = uks.export_statements()
    assert Statement.from_relationship(rel) in exported
    path = tmp_path / "uks.json"
    uks.save(str(path))

    uks2 = UKS()
    uks2.add_relationship("c", "likes", "d")
    uks2.load(str(path), merge=True)
    assert uks2.get_relationship("a", "likes", "b")
    assert uks2.get_relationship("c", "likes", "d")
    uks.shutdown()
    uks2.shutdown()


def test_query_regex():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    uks.add_relationship("cat", "is-a", "animal")
    uks.add_relationship("car", "is-a", "vehicle")
    uks.add_relationship("dog", "is-a", "animal")
    res = uks.query(source_regex="c.*", reltype="is-a")
    labels = {r.source.Label for r in res}
    assert labels == {"cat", "car"}
    uks.shutdown()
