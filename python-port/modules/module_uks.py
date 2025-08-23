"""UKS persistence module."""
from __future__ import annotations

import os
from typing import Dict

from .module_base import ModuleBase


class ModuleUKS(ModuleBase):
    """Manage UKS persistence via ``UKS.save`` and ``UKS.load``."""

    def __init__(self, label: str | None = None) -> None:
        super().__init__(label)
        self.file_name: str = ""

    def initialize(self) -> None:
        """Nothing required for initialization."""
        return

    def on_start(self) -> None:
        super().on_start()
        if self.file_name:
            if os.path.exists(self.file_name):
                self.the_uks.load(self.file_name)

    def on_stop(self) -> None:
        if self.file_name:
            self.the_uks.save(self.file_name)
        super().on_stop()

    def fire(self) -> None:  # pragma: no cover - no periodic work
        return

    def get_parameters(self) -> Dict[str, str]:
        params = super().get_parameters()
        params["file_name"] = self.file_name
        return params

    def set_parameters(self, params: Dict[str, str]) -> None:
        self.file_name = params.get("file_name", "")
