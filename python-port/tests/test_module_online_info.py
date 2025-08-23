import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from modules.module_online_info import ModuleOnlineInfo
from uks import UKS


def test_online_info_adds_summary(monkeypatch):
    called = {}

    def fake_get(url, timeout=10):  # pragma: no cover - trivial
        class Resp:
            status_code = 200

            def json(self):
                return {"extract": "sample summary"}

        called["url"] = url
        return Resp()

    monkeypatch.setattr("modules.module_online_info.requests.get", fake_get)

    uks = UKS()
    mod = ModuleOnlineInfo()
    mod.initialize(uks)
    mod.add_query("Cat")
    rels = uks.get_all_relationships(uks.UKSList, False)
    assert any(r.reltype.Label == "hasSummary" and r.target.Label == "sample summary" for r in rels)
