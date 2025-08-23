from __future__ import annotations
"""Statement helpers for the Universal Knowledge Store.

This mirrors the lightweight statement builder used in the C# project.  A
:class:`Statement` represents a single relationship to be asserted in the
knowledge store and can be converted to and from :class:`Relationship`
instances or serialised to dictionaries for persistence.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Dict, Any

from .relationship import Relationship


@dataclass(eq=True)
class Statement:
    """Represent a UKS statement.

    Parameters
    ----------
    source, reltype, target:
        Labels identifying the source Thing, relationship type and target
        Thing.  ``target`` may be ``None`` for attribute-only relations.
    weight:
        Strength of the relationship (defaults to ``1.0``).
    ttl:
        Optional time-to-live in seconds.  ``None`` means the relationship is
        permanent.
    """

    source: str
    reltype: str
    target: Optional[str] = None
    weight: float = 1.0
    ttl: Optional[float] = None

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------
    def to_relationship(self, uks: "UKS") -> Relationship:
        """Materialise this statement into the given :class:`UKS`.

        This simply delegates to :meth:`UKS.add_relationship` using the stored
        parameters.
        """

        return uks.add_relationship(self.source, self.reltype, self.target, self.ttl, self.weight)

    @classmethod
    def from_relationship(cls, rel: Relationship) -> "Statement":
        ttl = None
        if rel.time_to_live != timedelta.max:
            ttl = rel.time_to_live.total_seconds()
        target_label = rel.target.Label if rel.target else None
        return cls(rel.source.Label, rel.reltype.Label, target_label, rel.weight, ttl)

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "reltype": self.reltype,
            "target": self.target,
            "weight": self.weight,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Statement":
        return cls(
            data["source"],
            data["reltype"],
            data.get("target"),
            data.get("weight", 1.0),
            data.get("ttl"),
        )


__all__ = ["Statement"]
