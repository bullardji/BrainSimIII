import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from modules.module_uks_query import ModuleUKSQuery
from modules.module_uks_statement import ModuleUKSStatement
from uks import UKS, ThingLabels


def test_statement_and_query():
    ThingLabels.clear_label_list()
    uks = UKS()
    stmt = ModuleUKSStatement()
    stmt.initialize(uks)
    stmt.add_statement("Cat is Animal")

    query = ModuleUKSQuery()
    query.initialize(uks)
    results = list(query.query("Cat", "is", "Animal"))
    assert ("Cat", "is", "Animal") in results
