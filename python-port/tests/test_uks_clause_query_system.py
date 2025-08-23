import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from uks import UKS, ThingLabels, transient_relationships, QueryRelationship


def test_clause_and_hits_misses():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    rel = uks.add_relationship("cat", "is", "animal")
    rel2 = uks.add_relationship("cat", "likes", "fish")
    uks.add_clause(rel, "because", rel2)

    assert rel.clauses and rel.clauses[0].clause is rel2
    assert rel2.clauses_from == [rel]

    results = uks.query(source="cat", reltype="is")
    assert isinstance(results[0], QueryRelationship)
    assert rel.hits == 1 and rel.misses == 0
    assert rel2.misses == 1 and rel2.hits == 0
    uks.shutdown()
