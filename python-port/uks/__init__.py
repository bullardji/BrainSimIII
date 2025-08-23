"""Python port of the Universal Knowledge Store (UKS).

The module exposes :class:`Thing`, :class:`Relationship`, and :class:`UKS`
classes closely mirroring their counterparts in the original C# project.
"""

from .relationship import Relationship, Clause, QueryRelationship
from .thing import Thing, transient_relationships
from .thing_labels import ThingLabels
from .statement import Statement
from .uks import UKS

__all__ = [
    "Thing",
    "Relationship",
    "Clause",
    "QueryRelationship",
    "ThingLabels",
    "UKS",
    "Statement",
    "transient_relationships",
]
