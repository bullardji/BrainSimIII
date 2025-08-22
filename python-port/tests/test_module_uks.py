from pathlib import Path

from modules import ModuleHandler


def test_module_uks_save_load(tmp_path: Path) -> None:
    handler = ModuleHandler()
    data = [{"class": "ModuleUKS", "label": "UKS", "params": {"file_name": str(tmp_path / "uks.json")}}]
    handler.load_active(data)
    uks = handler.the_uks
    uks.add_relationship("Object", "has-child", "Foo")
    handler.deactivate("UKS")

    handler2 = ModuleHandler()
    handler2.load_active(data)
    rels = handler2.the_uks.query(source="Object", reltype="has-child", target="Foo")
    assert rels
