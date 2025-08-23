from __future__ import annotations

"""Module that removes redundant attributes in the UKS.

This is a direct port of the C# ``ModuleRemoveRedundancy``.  The module runs
periodically and weakens or deletes relationships on Things when the same
relationship exists on a parent with sufficient confidence.  It helps maintain a
compact knowledge store by avoiding duplicate information on child nodes.
"""

import threading

from .module_base import ModuleBase
from uks import UKS, Thing, Relationship


class ModuleRemoveRedundancy(ModuleBase):
    """Periodically prune redundant attributes from Things."""

    def __init__(self) -> None:
        super().__init__(label="ModuleRemoveRedundancy")
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
        # The original module performs all work on a timer; ``fire`` merely
        # ensures initialization and updates the dialog (not implemented here).
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
            # Reschedule the timer and exit
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
            self._remove_redundant_attributes(t)
        self.debug_string += "Agent  Finished\n"

    # ------------------------------------------------------------------
    def _remove_redundant_attributes(self, t: Thing) -> None:
        for parent in t.Parents:
            rels_with_inheritance = self.the_uks.get_all_relationships([parent], False)
            for r in list(t.relationships):
                match = next(
                    (
                        x
                        for x in rels_with_inheritance
                        if x.source is not r.source
                        and x.reltype is r.reltype
                        and x.target is r.target
                    ),
                    None,
                )
                if match and match.weight > 0.8:
                    r.weight -= 0.1
                    if r.weight < 0.5:
                        t.remove_relationship(r)
                        self.debug_string += f"Removed: {r}\n"
                        # restart scanning from scratch since list changed
                        return self._remove_redundant_attributes(t)
                    else:
                        self.debug_string += f"{r}   ({r.weight:0.00})\n"

    def get_parameters(self) -> dict:
        return {"interval": self.interval}

    def set_parameters(self, params: dict) -> None:
        self.interval = float(params.get("interval", self.interval))

    # Utility for tests to cancel timer
    def cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
