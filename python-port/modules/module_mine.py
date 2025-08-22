from __future__ import annotations

"""Simple placeholder module mirroring the C# ModuleMine template.

The original C# ``ModuleMine`` class acts as an example module with no
behaviour other than demonstrating the module lifecycle.  The Python
counterpart follows the same pattern: it can be activated and will
respond to engine ticks without performing any additional work.  Having
this module available allows tests and documentation to reference a
minimal module implementation that exercises the framework in isolation.
"""

from .module_base import ModuleBase


class ModuleMine(ModuleBase):
    """Minimal module that performs no actions each step."""

    def initialize(self) -> None:  # pragma: no cover - nothing to set up
        """No initialisation required for the template module."""

    def fire(self) -> None:  # pragma: no cover - no behaviour to execute
        """Called each simulation tick; performs no work."""
        self._ensure_initialized()
