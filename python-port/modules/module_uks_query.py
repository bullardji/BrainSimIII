from __future__ import annotations
import re
from typing import Iterable

from .module_base import ModuleBase
from uks import UKS


class ModuleUKSQuery(ModuleBase):
    """Module providing regex-based queries over the UKS."""

    def __init__(self):
        super().__init__()
        self.uks: UKS | None = None

    def initialize(self, uks: UKS) -> None:  # type: ignore[override]
        self.uks = uks

    def query(self, source: str = "", reltype: str = "", target: str = "") -> Iterable[tuple[str, str, str]]:
        if self.uks is None:
            return []
        pattern_source = re.compile(source, re.IGNORECASE)
        pattern_rel = re.compile(reltype, re.IGNORECASE)
        pattern_target = re.compile(target, re.IGNORECASE)
        results = []
        for rel in self.uks.get_all_relationships(self.uks.UKSList, False):
            if pattern_source.search(rel.source.Label) and pattern_rel.search(rel.reltype.Label) and (
                rel.target is not None and pattern_target.search(rel.target.Label)
            ):
                results.append((rel.source.Label, rel.reltype.Label, rel.target.Label))
        return results
