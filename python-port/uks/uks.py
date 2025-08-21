from __future__ import annotations

"""Universal Knowledge Store main interface."""

from datetime import datetime, timedelta
import json
import threading
from typing import Callable, Dict, List, Optional

from .thing import Thing, transient_relationships
from .relationship import Relationship
from .thing_labels import ThingLabels


class UKS:
    """Container for all Things and Relationships.

    This is a partial port of the C# UKS class.  It maintains a global list of
    Things and periodically removes transient relationships whose TTL has
    expired.
    """

    def __init__(self) -> None:
        # initialise UKS list only once
        if not ThingLabels.get_thing("has-child"):
            ThingLabels.clear_label_list()
            self.UKSList: List[Thing] = []
            self.create_initial_structure()
        else:
            # Reuse existing list if UKS already initialised
            self.UKSList = [t for t in ThingLabels._labels.values()]

        # event handlers for relationship changes
        self._handlers: Dict[str, List[Callable[[Relationship], None]]] = {}

        # Start background thread for TTL processing
        self._stop_event = threading.Event()
        thread = threading.Thread(target=self._timer_loop, daemon=True)
        thread.start()

    # ------------------------------------------------------------------
    # Initialization helpers
    # ------------------------------------------------------------------
    def create_initial_structure(self) -> None:
        # Minimal structure: root thing and required relationship types
        root = self.add_thing("Object", None)
        has_child = self.add_thing("has-child", None)
        unknown = self.add_thing("unknownObject", root)
        # The above ensures parent/child relations are supported

    # ------------------------------------------------------------------
    # Timer loop handling transient relationships
    # ------------------------------------------------------------------
    def _timer_loop(self) -> None:
        while not self._stop_event.is_set():
            self.remove_expired_relationships()
            self._stop_event.wait(1.0)

    def remove_expired_relationships(self) -> None:
        now = datetime.now()
        for rel in list(transient_relationships):
            if rel.time_to_live != timedelta.max and rel.last_used + rel.time_to_live < now:
                self.remove_relationship(rel)

    # ------------------------------------------------------------------
    # Thing management
    # ------------------------------------------------------------------
    def add_thing(self, label: str, parent: Optional[Thing]) -> Thing:
        thing = Thing(label)
        if parent is not None:
            thing.add_parent(parent)
        self.UKSList.append(thing)
        return thing

    def get_or_add_thing(self, label: str, parent: Optional[Thing] = None, value: Optional[object] = None) -> Thing:
        t = ThingLabels.get_thing(label)
        if t is None:
            t = Thing(label, value)
            self.UKSList.append(t)
            if parent is not None:
                t.add_parent(parent)
        return t

    def labeled(self, label: str) -> Optional[Thing]:
        return ThingLabels.get_thing(label)

    def delete_thing(self, thing: Thing) -> None:
        for rel in list(thing.relationships):
            thing.remove_relationship(rel)
        for rel in list(thing.relationships_from):
            rel.source.remove_relationship(rel)
        ThingLabels.remove_thing_label(thing.Label)
        if thing in self.UKSList:
            self.UKSList.remove(thing)

    # ------------------------------------------------------------------
    # Relationship helpers
    # ------------------------------------------------------------------
    def add_relationship(
        self,
        source: str | Thing,
        reltype: str | Thing,
        target: Optional[str | Thing],
        ttl: Optional[float] = None,
        weight: float = 1.0,
    ) -> Relationship:
        s = self._thing_from_param(source)
        rt = self._thing_from_param(reltype)
        t = self._thing_from_param(target) if target is not None else None

        existing = self.get_relationship(s, rt, t)
        if existing is not None:
            if weight > existing.weight:
                existing.weight = weight
            if ttl is not None:
                existing.time_to_live = timedelta(seconds=ttl)
                existing.last_used = datetime.now()
            self._fire("update", existing)
            return existing

        rel = s.add_relationship(rt, t, ttl, weight)
        self._fire("add", rel)
        return rel

    def get_relationship(
        self,
        source: str | Thing,
        reltype: str | Thing,
        target: Optional[str | Thing] = None,
    ) -> Optional[Relationship]:
        """Return an existing relationship matching the given parameters.

        Parameters accept either :class:`Thing` instances or labels.  If a
        label is provided and no corresponding :class:`Thing` exists the
        method returns ``None`` without creating new Things.  This mirrors the
        behaviour of the C# ``GetRelationship`` helper used throughout the
        project.
        """

        s = source if isinstance(source, Thing) else ThingLabels.get_thing(source)
        rt = reltype if isinstance(reltype, Thing) else ThingLabels.get_thing(reltype)
        t = (
            target
            if isinstance(target, Thing)
            else ThingLabels.get_thing(target) if target is not None else None
        )
        if s is None or rt is None:
            return None
        for rel in s.relationships:
            if rel.reltype is rt and rel.target is t:
                return rel
        return None

    def add_statement(
        self,
        source: str | Thing,
        reltype: str | Thing,
        target: Optional[str | Thing],
        ttl: Optional[float] = None,
        weight: float = 1.0,
    ) -> Relationship:
        """Create a relationship if one does not already exist.

        This is a light‑weight analogue of the C# ``AddStatement`` method.  It
        performs basic Thing lookup/creation and ensures duplicate statements
        are not produced.
        """

        s = self._thing_from_param(source)
        rt = self._thing_from_param(reltype)
        t = self._thing_from_param(target) if target is not None else None

        existing = self.get_relationship(s, rt, t)
        if existing is not None:
            if weight > existing.weight:
                existing.weight = weight
            return existing

        rel = s.add_relationship(rt, t, ttl, weight)
        self._fire("add", rel)
        return rel

    def get_all_relationships(self, sources: List[Thing], reverse: bool) -> List[Relationship]:
        """Return relationships from ``sources`` including inherited ones."""
        result: List[Relationship] = []
        stack = list(sources)
        visited: set[Thing] = set()
        while stack:
            t = stack.pop()
            if t in visited:
                continue
            visited.add(t)
            result.extend(t.relationships)
            stack.extend(t.Children if reverse else t.Parents)
        return result

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, path: str) -> None:
        data = {
            "things": [
                {"label": t.Label, "value": t.V}
                for t in self.UKSList
            ],
            "relationships": [
                {
                    "source": r.source.Label,
                    "reltype": r.reltype.Label,
                    "target": r.target.Label if r.target else None,
                    "weight": r.weight,
                    "ttl": None if r.time_to_live == timedelta.max else r.time_to_live.total_seconds(),
                }
                for t in self.UKSList for r in t.relationships
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ThingLabels.clear_label_list()
        transient_relationships.clear()
        self.UKSList = []
        mapping: Dict[str, Thing] = {}
        for td in data.get("things", []):
            t = Thing(td["label"], td.get("value"))
            self.UKSList.append(t)
            mapping[t.Label] = t
        for rd in data.get("relationships", []):
            s = mapping[rd["source"]]
            rt = mapping[rd["reltype"]]
            tgt = mapping.get(rd["target"]) if rd.get("target") else None
            ttl = rd.get("ttl")
            s.add_relationship(rt, tgt, ttl, rd.get("weight", 1.0))

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------
    def query(
        self,
        *,
        source: Optional[str] = None,
        reltype: Optional[str] = None,
        target: Optional[str] = None,
        min_weight: float = 0.0,
        max_ttl: Optional[float] = None,
    ) -> List[Relationship]:
        """Return relationships matching the given filters."""

        now = datetime.now()
        results: List[Relationship] = []
        for t in self.UKSList:
            if source and t.Label != source:
                continue
            for r in t.relationships:
                if reltype and r.reltype.Label != reltype:
                    continue
                if target and (r.target is None or r.target.Label != target):
                    continue
                if r.weight < min_weight:
                    continue
                if max_ttl is not None and r.time_to_live != timedelta.max:
                    remaining = (r.last_used + r.time_to_live - now).total_seconds()
                    if remaining > max_ttl:
                        continue
                results.append(r)
        return results

    # ------------------------------------------------------------------
    # Event hooks
    # ------------------------------------------------------------------
    def on(self, event: str, callback: Callable[[Relationship], None]) -> None:
        self._handlers.setdefault(event, []).append(callback)

    def _fire(self, event: str, rel: Relationship) -> None:
        for cb in self._handlers.get(event, []):
            cb(rel)

    def remove_relationship(self, rel: Relationship) -> None:
        rel.source.remove_relationship(rel)
        self._fire("remove", rel)

    def _thing_from_param(self, param: str | Thing) -> Thing:
        if isinstance(param, Thing):
            return param
        t = ThingLabels.get_thing(param)
        if t is None:
            t = self.add_thing(param, self.labeled("Object"))
        return t
