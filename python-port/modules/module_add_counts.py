from __future__ import annotations

"""Module that adds count-based relationships in the UKS.

This is a port of the C# ``ModuleAddCounts``.  It scans all Things in the
knowledge store and, for each relationship type, adds an aggregate relationship
indicating how many times targets sharing a common ancestor occur.  The count is
encoded into the relationship type label, mirroring the behaviour of the
original module which stored the count as a relationship type property.
"""

import threading
from typing import Dict, List, Tuple

from .module_base import ModuleBase
from uks import UKS, Thing, Relationship


class ModuleAddCounts(ModuleBase):
    """Periodically add count relationships to Things."""

    def __init__(self) -> None:
        super().__init__(label="ModuleAddCounts")
        self.is_enabled: bool = False
        self.debug_string = "Initialized\n"
        self._timer: threading.Timer | None = None
        self.interval: float = 10.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        pass

    def on_start(self) -> None:
        self._setup()

    def on_stop(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        super().on_stop()

    def fire(self) -> None:
        if not self.initialized:
            self.initialize()
            self.initialized = True

    # ------------------------------------------------------------------
    def _setup(self) -> None:
        if self._timer is None:
            self._timer = threading.Timer(self.interval, self._same_thread_callback)
            self._timer.daemon = True
            self._timer.start()

    def _same_thread_callback(self) -> None:
        if not self.is_enabled:
            self._setup()
            return
        self.start_worker(self.do_the_work)

        self._setup()

    # ------------------------------------------------------------------
    def do_the_work(self) -> None:
        if self.the_uks is None:
            return
        self.debug_string = "Agent Started\n"
        for t in list(self.the_uks.UKSList):
            self._add_count_relationships(t)
        self.debug_string += "Agent Finished\n"

    # ------------------------------------------------------------------
    def _add_count_relationships(self, t: Thing) -> None:
        has_child = self.the_uks.labeled("has-child") if self.the_uks else None
        for r in list(t.relationships):
            if has_child is not None and r.reltype is has_child:
                continue
            use_rel_type = self._get_instance_type(r.reltype)
            targets = [
                rel.target
                for rel in t.relationships
                if rel.target is not None and self._get_instance_type(rel.reltype) is use_rel_type
            ]
            best_matches = self._get_attribute_counts(targets)
            for match, count in best_matches:
                rel_label = f"{use_rel_type.Label}.{count}"
                existing = self.the_uks.get_relationship(t, rel_label, match)
                if existing is None:
                    self.the_uks.add_statement(t, rel_label, match)
                    self.debug_string += f"Added: {t.Label} {rel_label} {match.Label}\n"

    # ------------------------------------------------------------------
    def _get_attribute_counts(self, ts: List[Thing]) -> List[Tuple[Thing, int]]:
        ret: List[Tuple[Thing, int]] = []
        if not ts:
            return ret
        counts: Dict[Thing, int] = {}
        for t in ts:
            for anc in t.AncestorList():
                counts[anc] = counts.get(anc, 0) + 1
        unknown = self.the_uks.labeled("unknownObject") if self.the_uks else None
        for k, v in counts.items():
            if unknown and unknown in k.AncestorList() and k is not unknown and v > 1:
                ret.append((k, v))
        return ret

    def _get_instance_type(self, t: Thing) -> Thing:
        use = t
        while (
            use.Parents
            and use.Label[-1:].isdigit()
            and "." not in t.Label
            and use.Label.startswith(use.Parents[0].Label)
        ):
            use = use.Parents[0]
        return use

    # Utility for tests to cancel timer
    def cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def get_parameters(self) -> dict:
        return {"interval": self.interval}

    def set_parameters(self, params: dict) -> None:
        self.interval = float(params.get("interval", self.interval))
