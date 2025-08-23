from __future__ import annotations

"""UKS relationship objects.

Relationships connect a *source* Thing to a *target* Thing via a *reltype*
Thing which describes the kind of relationship.  They may optionally expire
after ``time_to_live`` seconds and keep track of the last time they were
accessed via ``last_used``.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class Clause:
    """A relationship-to-relationship dependency."""

    clause_type: "Thing"
    clause: "Relationship"



@dataclass
class Relationship:
    source: "Thing"
    reltype: "Thing"
    target: Optional["Thing"]
    weight: float = 1.0
    time_to_live: timedelta = timedelta.max
    last_used: datetime = field(default_factory=datetime.now)
    hits: int = 0
    misses: int = 0
    clauses: List[Clause] = field(default_factory=list)
    clauses_from: List["Relationship"] = field(default_factory=list)
    created: datetime = field(default_factory=datetime.now)

    def touch(self) -> None:
        """Update the ``last_used`` timestamp to now."""
        self.last_used = datetime.now()

    def add_clause(self, clause_type: "Thing", target: "Relationship") -> None:
        """Attach a :class:`Clause` linking this relationship to ``target``."""

        c = Clause(clause_type, target)
        self.clauses.append(c)
        target.clauses_from.append(self)

    @property
    def value(self) -> float:
        """Return weighted value based on hits and misses."""

        return self.weight * (self.hits + 1) / (self.hits + self.misses + 2)

    def __hash__(self) -> int:  # pragma: no cover - trivial
        return hash((self.source, self.reltype, self.target))

    def __eq__(self, other: object) -> bool:  # pragma: no cover - trivial
        if not isinstance(other, Relationship):
            return NotImplemented
        return (
            self.source is other.source
            and self.reltype is other.reltype
            and self.target is other.target
        )


@dataclass
class QueryRelationship:
    """A relationship returned from UKS queries with additional query metadata."""
    
    source: "Thing"
    reltype: "Thing"  
    target: Optional["Thing"]
    weight: float = 1.0
    value: float = 0.0
    hits: int = 0
    misses: int = 0
    
    @classmethod
    def from_relationship(cls, rel: Relationship) -> "QueryRelationship":
        """Create a QueryRelationship from a regular Relationship."""
        return cls(
            source=rel.source,
            reltype=rel.reltype,
            target=rel.target,
            weight=rel.weight,
            value=rel.value,
            hits=rel.hits,
            misses=rel.misses
        )

