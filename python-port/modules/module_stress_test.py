from __future__ import annotations

"""Stress-testing module for bulk UKS insertion.

This is a direct port of the C# ``ModuleStressTest``.  It exposes a helper
:func:`add_many_test_items` which creates a large hierarchy of Things within the
UKS knowledge store.  The method mirrors the original logic and validates the
requested count, stopping once the desired number of items have been inserted.
"""

from typing import Optional

from .module_base import ModuleBase
from uks import UKS


class ModuleStressTest(ModuleBase):
    """Module providing utility methods for stress testing the UKS."""

    Output: str = ""

    def __init__(self) -> None:
        super().__init__(label="ModuleStressTest")

    def initialize(self) -> None:  # pragma: no cover - no setup required
        pass

    def fire(self) -> None:  # pragma: no cover - module has no periodic work
        self._ensure_initialized()

    # ------------------------------------------------------------------
    def add_many_test_items(self, count: int) -> str:
        """Populate the UKS with a large number of test items.

        Parameters
        ----------
        count:
            Number of items to insert.  The function returns a descriptive
            message in case ``count`` is outside the allowed range or upon
            successful completion.
        """
        max_count = 100_000
        if count <= 0:
            return "Count less or equal to 0, cannot commence."
        if count > max_count:
            return f"Count greater than maxCount {max_count}, cannot commence."
        if self.the_uks is None:
            return "UKS not assigned."

        created = 0
        outer = 0
        while created < count and outer < 100:
            parent = self.the_uks.get_or_add_thing(f"A{outer}")
            created += 1
            if created >= count:
                break
            for j in range(100):
                parent0 = self.the_uks.get_or_add_thing(f"B{outer}{j}", parent)
                created += 1
                if created >= count:
                    break
                for k in range(10):
                    self.the_uks.get_or_add_thing(f"C{outer}{j}{k}", parent0)
                    created += 1
                    if created >= count:
                        break
                if created >= count:
                    break
            outer += 1
        return "Items added successfully."
