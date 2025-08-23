from __future__ import annotations

"""Port of the C# ModuleClassCreate.

This module examines Things within the UKS and looks for children of a given
Thing that share common attributes.  If a sufficient number of children share
an attribute, a new intermediate class is created to group them.
"""

import threading
from dataclasses import dataclass
from typing import List, Dict

from .module_base import ModuleBase
from uks import UKS, Thing, Relationship


@dataclass
class _RelDest:
    rel_type: Thing
    target: Thing
    relationships: List[Relationship]


class ModuleClassCreate(ModuleBase):
    """Periodically create subclasses based on shared attributes."""

    def __init__(self) -> None:
        super().__init__(label="ModuleClassCreate")
        self.is_enabled: bool = False
        self.debug_string = "Initialized\n"
        self.max_children = 12
        self.min_common_attributes = 3
        self._timer: threading.Timer | None = None

    # ------------------------------------------------------------------
    def initialize(self) -> None:
        self._setup()

    def fire(self) -> None:
        # This module performs its work on a timer; fire ensures initialization
        if not self.initialized:
            self.initialize()
            self.initialized = True

    def reset(self) -> None:  # cancel timer on reset
        super().reset()
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    # ------------------------------------------------------------------
    def _setup(self) -> None:
        if self._timer is None:
            self._timer = threading.Timer(10.0, self._same_thread_callback)
            self._timer.daemon = True
            self._timer.start()

    def _same_thread_callback(self) -> None:
        if not self.is_enabled:
            self._setup()
            return
        threading.Thread(target=self.do_the_work, daemon=True).start()
        self._setup()

    # ------------------------------------------------------------------
    def do_the_work(self) -> None:
        if self.the_uks is None:
            return
        self.debug_string = "Agent Started\n"
        for t in list(self.the_uks.UKSList):
            if (
                t.Label.find(".") == -1
                and "unknown" not in t.Label
                and any(p.Label == "Object" for p in t.AncestorList())
            ):
                self._handle_class_with_common_attributes(t)
        self.debug_string += "Agent  Finished\n"

    def _handle_class_with_common_attributes(self, t: Thing) -> None:
        attributes: List[_RelDest] = []
        for child in t.Children:
            for r in child.relationships:
                if r.reltype.Label == "has-child":
                    continue
                key = next(
                    (a for a in attributes if a.rel_type is r.reltype and a.target is r.target),
                    None,
                )
                if key is None:
                    key = _RelDest(r.reltype, r.target, [])
                    attributes.append(key)
                key.relationships.append(r)
        for item in attributes:
            if len(item.relationships) >= self.min_common_attributes:
                new_label = f"{t.Label}.{item.rel_type.Label}.{item.target.Label}"
                new_parent = self.the_uks.get_or_add_thing(new_label, t)
                new_parent.add_relationship(item.rel_type, item.target)
                self.debug_string += f"Created new subclass {new_parent.Label}\n"
                for rel in item.relationships:
                    child = rel.source
                    child.add_parent(new_parent)
                    for pr in list(t.relationships):
                        if pr.reltype.Label == "has-child" and pr.target is child:
                            t.remove_relationship(pr)

    # Utility for tests to cancel timer
    def cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
