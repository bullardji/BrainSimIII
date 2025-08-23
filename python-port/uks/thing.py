from __future__ import annotations

"""Thing class representing nodes in the Universal Knowledge Store."""

import threading
from datetime import timedelta
from typing import List, Optional

from .relationship import Relationship
from .thing_labels import ThingLabels

# Registry of transient relationships used by UKS timers
transient_relationships: List[Relationship] = []


class Thing:
    def __init__(self, label: str, value: Optional[object] = None):
        self._label = ""
        self.V = value
        self.relationships: List[Relationship] = []
        self.relationships_from: List[Relationship] = []
        self.relationships_as_type: List[Relationship] = []
        self._lock = threading.RLock()
        self.Label = label

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return self.ToString()

    # ------------------------------------------------------------------
    # String utilities
    # ------------------------------------------------------------------
    def ToString(self, show_properties: bool = False) -> str:
        ret = self.Label
        if self.V is not None:
            ret += f" V: {self.V}"
        if show_properties and self.relationships:
            ret += " {" + ",".join(r.target.Label if r.target else "" for r in self.relationships) + "}"
        return ret

    # ------------------------------------------------------------------
    # Label management
    # ------------------------------------------------------------------
    @property
    def Label(self) -> str:
        return self._label

    @Label.setter
    def Label(self, value: str) -> None:
        if value == self._label:
            return
        self._label = ThingLabels.add_thing_label(value, self)

    # ------------------------------------------------------------------
    # Relationship management
    # ------------------------------------------------------------------
    def add_relationship(
        self,
        reltype: "Thing",
        target: Optional["Thing"],
        ttl: Optional[float] = None,
        weight: float = 1.0,
    ) -> Relationship:
        """Create and register a new relationship from this Thing.

        Parameters
        ----------
        reltype:
            The relationship type Thing.
        target:
            The target Thing or ``None`` for property-only relationships.
        ttl:
            Optional time-to-live in seconds.  When provided the relationship is
            added to :data:`transient_relationships` for automatic expiry.
        weight:
            Strength of the relationship.  Used by some modules to adjust
            confidence levels.
        """
        ttl_td = timedelta(seconds=ttl) if ttl is not None else timedelta.max
        rel = Relationship(self, reltype, target, weight, ttl_td)
        with self._lock:
            self.relationships.append(rel)
        if target is not None:
            with target._lock:
                target.relationships_from.append(rel)
        with reltype._lock:
            reltype.relationships_as_type.append(rel)
        if ttl is not None:
            transient_relationships.append(rel)
        return rel

    def add_parent(self, parent: "Thing") -> Relationship:
        has_child = ThingLabels.get_thing("has-child")
        if has_child is None:
            raise ValueError("Relationship type 'has-child' not found")
        return parent.add_relationship(has_child, self)

    def remove_parent(self, parent: "Thing") -> None:
        """Detach *parent* from this Thing if present."""
        has_child = ThingLabels.get_thing("has-child")
        for rel in list(parent.relationships):
            if rel.reltype == has_child and rel.target is self:
                parent.remove_relationship(rel)
                break

    def remove_relationship(self, rel: Relationship) -> None:
        with self._lock:
            if rel in self.relationships:
                self.relationships.remove(rel)
        if rel.target:
            with rel.target._lock:
                if rel in rel.target.relationships_from:
                    rel.target.relationships_from.remove(rel)
        with rel.reltype._lock:
            if rel in rel.reltype.relationships_as_type:
                rel.reltype.relationships_as_type.remove(rel)
        if rel in transient_relationships:
            transient_relationships.remove(rel)

    # ------------------------------------------------------------------
    # Relationship queries
    # ------------------------------------------------------------------
    @property
    def Parents(self) -> List["Thing"]:
        has_child = ThingLabels.get_thing("has-child")
        with self._lock:
            return [r.source for r in self.relationships_from if r.reltype == has_child and r.target is self]

    @property
    def Children(self) -> List["Thing"]:
        has_child = ThingLabels.get_thing("has-child")
        with self._lock:
            return [r.target for r in self.relationships if r.reltype == has_child and r.target is not None]

    @property
    def ChildrenWithSubclasses(self) -> List["Thing"]:
        """Return direct children expanding any instance subclasses.

        A child whose label starts with this Thing's label is treated as an
        instance/subclass.  In that case its own children are included instead
        of the child itself, mirroring the behaviour of the C# implementation.
        """

        children = self.Children[:]
        i = 0
        while i < len(children):
            c = children[i]
            if c.Label.startswith(self.Label):
                children.extend(c.Children)
                children.pop(i)
                continue
            i += 1
        return children

    def AncestorList(self) -> List["Thing"]:
        result: List[Thing] = []
        stack = list(self.Parents)
        while stack:
            parent = stack.pop()
            if parent not in result:
                result.append(parent)
                stack.extend(parent.Parents)
        return result

    def Descendents(self) -> List["Thing"]:
        result: List[Thing] = []
        stack = list(self.Children)
        while stack:
            child = stack.pop()
            if child not in result:
                result.append(child)
                stack.extend(child.Children)
        return result

    def has_ancestor(self, label: str) -> bool:
        """Return ``True`` if any ancestor has the given *label*."""
        return any(t.Label == label for t in self.AncestorList())

    def has_ancestor_labeled(self, label: str) -> bool:
        """Case-insensitive label lookup for ancestor relationships."""
        return self.has_ancestor(label)

    # ------------------------------------------------------------------
    # Attribute and property helpers
    # ------------------------------------------------------------------
    def get_attributes(self) -> List["Thing"]:
        ret: List[Thing] = []
        with self._lock:
            for r in self.relationships:
                if r.reltype.Label.lower() in {"hasattribute", "is", "hasproperty", "allows"} and r.target:
                    ret.append(r.target)
        return ret

    def set_attribute(self, attribute_value: "Thing", rel_label: str = "hasAttribute") -> Relationship:
        reltype = ThingLabels.get_thing(rel_label)
        if reltype is None:
            reltype = Thing(rel_label)
        return self.add_relationship(reltype, attribute_value)

    def set_property(self, property_value: "Thing") -> Relationship:
        return self.set_attribute(property_value, "hasProperty")

    def set_allows(self, thing: "Thing") -> Relationship:
        return self.set_attribute(thing, "allows")

    def has_property(self, t: "Thing") -> bool:
        with self._lock:
            for r in self.relationships:
                if r.reltype.Label.lower() == "hasproperty" and r.target is t:
                    return True
        for parent in self.Parents:
            if parent.has_property(t):
                return True
        return False

    def allows(self, t: "Thing") -> bool:
        with self._lock:
            for r in self.relationships:
                if r.reltype.Label.lower() == "allows" and r.target is t:
                    return True
        for parent in self.Parents:
            if parent.allows(t):
                return True
        return False
