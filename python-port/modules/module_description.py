"""Module description container."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModuleDescription:
    """Holds metadata about a module."""

    name: str
    description: str = ""
