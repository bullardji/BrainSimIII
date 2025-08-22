from __future__ import annotations

"""Port of the C# ``ModuleAttributeBubble``.

The module examines all Things in the UKS and bubbles up child relationships to
parent Things when enough children share the same relationship.  Conflicting
relationships and weighted counts are taken into account to emulate the
behaviour of the original module.
"""

import threading
from dataclasses import dataclass, field
from typing import List

from .module_base import ModuleBase
from uks import Thing, Relationship


@dataclass
class RelDest:
    rel_type: Thing
    target: Thing
    relationships: List[Relationship] = field(default_factory=list)


class ModuleAttributeBubble(ModuleBase):
    """Periodically bubble child attributes to their parent."""

    def __init__(self) -> None:
        super().__init__(label="ModuleAttributeBubble")
        self.is_enabled: bool = False
        self.debug_string = "Initialized\n"
        self._timer: threading.Timer | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        self._setup()

    def fire(self) -> None:
        if not self.initialized:
            self.initialize()
            self.initialized = True

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

    def cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    # ------------------------------------------------------------------
    def do_the_work(self) -> None:
        if self.the_uks is None:
            return
        self.debug_string = "Bubbler Started\n"
        for t in list(self.the_uks.UKSList):
            if t.has_ancestor("Object"):
                self._bubble_child_attributes(t)
        self.debug_string += "Bubbler Finished\n"

    # ------------------------------------------------------------------
    def _bubble_child_attributes(self, t: Thing) -> None:
        if not t.Children or t.Label == "unknownObject":
            return
        item_counts: List[RelDest] = []
        has_child = self.the_uks.labeled("has-child") if self.the_uks else None
        for child in t.ChildrenWithSubclasses:
            for r in child.relationships:
                if has_child and r.reltype is has_child:
                    continue
                use_rel_type = self._get_instance_type(r.reltype)
                found = next(
                    (x for x in item_counts if x.rel_type is use_rel_type and x.target is r.target),
                    None,
                )
                if not found:
                    found = RelDest(use_rel_type, r.target)
                    item_counts.append(found)
                found.relationships.append(r)
        if not item_counts:
            return
        sorted_items = sorted(item_counts, key=lambda x: len(x.relationships), reverse=True)
        exclude = {"hasProperty", "isTransitive", "isCommutative", "inverseOf", "hasAttribute", "hasDigit"}
        for rr in sorted_items:
            if rr.rel_type.Label in exclude:
                continue
            r = self.the_uks.get_relationship(t, rr.rel_type, rr.target)
            current_weight = r.weight if r else 0.0
            total_count = len(t.Children)
            positive_rels = [rel for rel in rr.relationships if rel.weight > 0.5]
            positive_count = len(positive_rels)
            positive_weight = sum(rel.weight for rel in rr.relationships)
            negative_count = 0
            negative_weight = 0
            for other in sorted_items:
                if other is rr:
                    continue
                if self._relationships_conflict(rr, other):
                    negative_count += len(other.relationships)
                    negative_weight += sum(rel.weight for rel in other.relationships)
            no_info_count = total_count - (positive_count + negative_count)
            positive_weight += current_weight + no_info_count * 0.51
            if no_info_count < 0:
                no_info_count = 0
            if negative_count >= positive_count:
                if r:
                    t.remove_relationship(r)
                    self.debug_string += f"Removed {r} \n"
                continue
            delta_weight = positive_weight - negative_weight
            if delta_weight < 0.8:
                target_weight = -0.1
            elif delta_weight < 1.7:
                target_weight = 0.01
            elif delta_weight < 2.7:
                target_weight = 0.2
            else:
                target_weight = 0.3
            if current_weight == 0:
                current_weight = 0.5
            new_weight = current_weight + target_weight
            if new_weight > 0.99:
                new_weight = 0.99
            if new_weight != current_weight or r is None:
                if new_weight < 0.5:
                    if r:
                        t.remove_relationship(r)
                        self.debug_string += f"Removed {r} \n"
                else:
                    if r is None:
                        r = t.add_relationship(rr.rel_type, rr.target)
                    r.weight = new_weight
                    for existing in list(t.relationships):
                        if existing is r:
                            continue
                        tmp = RelDest(existing.reltype, existing.target, [existing])
                        if self._relationships_conflict(tmp, rr):
                            t.remove_relationship(existing)
                    self.debug_string += f"{r}   {r.weight:.0f}\n"

    # ------------------------------------------------------------------
    def _relationships_conflict(self, r1: RelDest, r2: RelDest) -> bool:
        if r1.rel_type is r2.rel_type and r1.target is r2.target:
            return False
        is_exclusive = self.the_uks.labeled("isExclusive") if self.the_uks else None
        allow_multiple = self.the_uks.labeled("allowMultiple") if self.the_uks else None
        if r1.rel_type is r2.rel_type:
            parents = self._find_common_parents(r1.target, r2.target)
            for parent in parents:
                if (
                    is_exclusive
                    and parent.has_property(is_exclusive)
                    or (allow_multiple and parent.has_property(allow_multiple))
                ):
                    return True
        if r1.target is r2.target:
            parents = self._find_common_parents(r1.target, r2.target)
            for parent in parents:
                if is_exclusive and parent.has_property(is_exclusive):
                    return True
            r1_attrs = r1.rel_type.get_attributes()
            r2_attrs = r2.rel_type.get_attributes()
            r1_not = next((x for x in r1_attrs if x.Label in {"not", "no"}), None)
            r2_not = next((x for x in r2_attrs if x.Label in {"not", "no"}), None)
            if (r1_not is None) != (r2_not is None):
                return True
            for a1 in r1_attrs:
                for a2 in r2_attrs:
                    if a1 is a2:
                        continue
                    for p in self._find_common_parents(a1, a2):
                        if (
                            is_exclusive
                            and p.has_property(is_exclusive)
                            or (allow_multiple and p.has_property(allow_multiple))
                        ):
                            return True
            has_number1 = any(x.has_ancestor_labeled("number") for x in r1_attrs)
            has_number2 = any(x.has_ancestor_labeled("number") for x in r2_attrs)
            if has_number1 or has_number2:
                return True
        return False

    def _find_common_parents(self, t: Thing, t1: Thing) -> List[Thing]:
        return [p for p in t.Parents if p in t1.Parents]

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
