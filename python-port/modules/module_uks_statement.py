from __future__ import annotations

from .module_base import ModuleBase
from uks import UKS


class ModuleUKSStatement(ModuleBase):
    """Module to parse simple statements and store them in the UKS."""

    def __init__(self):
        super().__init__()
        self.uks: UKS | None = None

    def initialize(self, uks: UKS) -> None:  # type: ignore[override]
        self.uks = uks

    def add_statement(self, text: str) -> None:
        if self.uks is None:
            return
        parts = text.split()
        if len(parts) < 3:
            return
        source = parts[0]
        rel = parts[1]
        target = " ".join(parts[2:])
        self.uks.add_statement(source, rel, target)
