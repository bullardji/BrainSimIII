from __future__ import annotations

"""UKS relationship objects.

Relationships connect a *source* Thing to a *target* Thing via a *reltype*
Thing which describes the kind of relationship.  They may optionally expire
after ``time_to_live`` seconds and keep track of the last time they were
accessed via ``last_used``.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class Relationship:
    source: "Thing"
    reltype: "Thing"
    target: Optional["Thing"]
    weight: float = 1.0
    time_to_live: timedelta = timedelta.max
    last_used: datetime = field(default_factory=datetime.now)
    misses: int = 0

    def touch(self) -> None:
        """Update the ``last_used`` timestamp to now."""
        self.last_used = datetime.now()

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
