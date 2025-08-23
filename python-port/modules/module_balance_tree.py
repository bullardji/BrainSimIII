"""Port of the C# ModuleBalanceTree module.

This module ensures that Things in the UKS do not end up with an excessive
number of direct children.  When a Thing exceeds ``max_children`` a new parent
Thing is created (sharing the original label with an auto-incremented suffix)
so that the children are distributed more evenly between the old and new
parents.  The original implementation uses a timer to periodically scan the
knowledge base; that behaviour is reproduced using ``threading.Timer``.
"""
from __future__ import annotations

import threading
from typing import Optional

from .module_base import ModuleBase
from uks import UKS, Thing


class ModuleBalanceTree(ModuleBase):
    def __init__(self, label: Optional[str] = None) -> None:
        super().__init__(label)
        self.max_children: int = 6
        self.interval: float = 10.0
        self._timer: Optional[threading.Timer] = None
        self.debug_string = "Initialized\n"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        pass

    def on_start(self) -> None:
        self._setup_timer()

    def on_stop(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        super().on_stop()

    def fire(self) -> None:  # timer driven
        if not self.initialized:
            self.initialize()

    def _setup_timer(self) -> None:
        if self._timer is None:
            self._timer = threading.Timer(self.interval, self._callback)
            self._timer.daemon = True
            self._timer.start()

    def _callback(self) -> None:
        if self.is_enabled and self.the_uks is not None:
            threading.Thread(target=self.do_the_work, daemon=True).start()
        # Reschedule
        self._timer = None
        self._setup_timer()

    # ------------------------------------------------------------------
    # Core behaviour
    # ------------------------------------------------------------------
    def do_the_work(self) -> None:
        if self.the_uks is None:
            return
        self.debug_string = "Agent Started\n"
        for t in list(self.the_uks.UKSList):
            if t.has_ancestor("Object") and "." not in t.Label:
                self.handle_excessive_children(t)
        self.debug_string += "Agent Finished\n"

    def handle_excessive_children(self, t: Thing) -> None:
        if self.the_uks is None:
            return
        while len(t.Children) > self.max_children:
            new_parent = self.the_uks.add_thing(t.Label, t)
            self.debug_string += f"Created new class: {new_parent.Label}\n"
            while len(new_parent.Children) < self.max_children and t.Children:
                child = t.Children[0]
                child.remove_parent(t)
                child.add_parent(new_parent)

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------
    def get_parameters(self) -> dict:
        return {"max_children": self.max_children, "interval": self.interval}

    def set_parameters(self, params: dict) -> None:
        self.max_children = int(params.get("max_children", self.max_children))
        self.interval = float(params.get("interval", self.interval))
        return {"max_children": self.max_children}

