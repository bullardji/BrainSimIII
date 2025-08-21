"""Python port of the Universal Knowledge Store (UKS).

The module exposes :class:`Thing`, :class:`Relationship`, and :class:`UKS`
classes closely mirroring their counterparts in the original C# project.
"""

from .relationship import Relationship
from .thing import Thing, transient_relationships
from .thing_labels import ThingLabels
from .uks import UKS

__all__ = ["Thing", "Relationship", "ThingLabels", "UKS", "transient_relationships"]
