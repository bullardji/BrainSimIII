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

def test_balance_tree_timer_reset():
    ThingLabels.clear_label_list()
    transient_relationships.clear()
    uks = UKS()
    module = ModuleBalanceTree()
    module.set_uks(uks)
    module.interval = 0.1
    module.on_start()
    assert module._timer is not None
    module.reset()
    assert module._timer is None
    module.on_stop()


def test_balance_tree_parameter_roundtrip():
    module = ModuleBalanceTree()
    module.set_parameters({"max_children": 3, "interval": 5.0})
    params = module.get_parameters()
    assert params["max_children"] == 3 and params["interval"] == 5.0
