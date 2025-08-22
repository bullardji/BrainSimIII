from modules.module_balance_tree import ModuleBalanceTree
from uks import UKS, ThingLabels, transient_relationships


def test_balance_tree_splits_children():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    root = uks.get_or_add_thing("root", uks.labeled("Object"))
    for i in range(5):
        child = uks.get_or_add_thing(f"c{i}")
        child.add_parent(root)
    module = ModuleBalanceTree()
    module.set_uks(uks)
    module.max_children = 2
    module.do_the_work()
    # root or its descendents should have at most 2 children each
    nodes = [root] + root.Descendents()
    assert all(len(n.Children) <= 2 for n in nodes)
    assert any(t.Label.startswith("root") and t is not root for t in nodes)
