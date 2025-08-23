from __future__ import annotations

"""Module providing clause-based UKS helpers.

This is a port of the C# ``ModuleUKSClause`` which exposes a handful of
utility methods for working with the UKS knowledge store.  It offers helpers
for adding relationships while parsing simple natural language strings,
retrieving clause types, searching labels and listing relationship types.

The port performs basic singularisation of words and interprets any words
preceding the final noun as attribute modifiers.  When a relationship is
added, attribute modifiers are attached via ``is`` or ``hasProperty`` links to
mirror the behaviour of the original module.
"""

import re
from typing import List, Tuple

from .module_base import ModuleBase
from uks import Relationship, Thing

try:  # optional, provides better singularisation
    import inflect

    _inflector = inflect.engine()

    def _singular(word: str) -> str:
        res = _inflector.singular_noun(word)
        if res and res != word and res != "ha":
            return res
        return word
except Exception:  # pragma: no cover - fallback simple rules
    def _singular(word: str) -> str:
        lower = word.lower()
        if lower in {"has", "is"}:
            return lower
        if word.endswith("ies"):
            return word[:-3] + "y"
        if word.endswith("ses"):
            return word[:-1]
        if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
            return word[:-1]
        return word


class ModuleUKSClause(ModuleBase):
    """Expose clause utilities for UKS manipulation."""

    def __init__(self) -> None:
        super().__init__(label="ModuleUKSClause")

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    def initialize(self) -> None:  # pragma: no cover - nothing to do
        pass

    def fire(self) -> None:  # pragma: no cover - module is helper only
        if not self.initialized:
            self.initialize()
            self.initialized = True

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    @staticmethod
    def _split(text: str, kind: str) -> Tuple[str, List[str]]:
        parts = [p for p in re.split(r"\s+", text.strip()) if p]
        if not parts:
            return "", []
        if kind == "type":
            base = _singular(parts[0])
            modifiers = [_singular(p) for p in parts[1:]]
        else:
            base = _singular(parts[-1])
            modifiers = [_singular(p) for p in parts[:-1]]
        return base, modifiers

    def get_clause_type(self, new_thing: str) -> Thing | None:
        if self.the_uks is None:
            return None
        parent = self.the_uks.get_or_add_thing("ClauseType")
        return self.the_uks.get_or_add_thing(new_thing, parent)

    def add_relationship(self, source: str, target: str, relationship_type: str) -> Relationship | None:
        if self.the_uks is None:
            return None
        src_label, src_mods = self._split(source, "source")
        tgt_label, tgt_mods = self._split(target, "source")
        rel_label, rel_mods = self._split(relationship_type, "type")

        src = self.the_uks.get_or_add_thing(src_label)
        tgt = self.the_uks.get_or_add_thing(tgt_label)
        rel_parent = self.the_uks.get_or_add_thing("RelationshipType")
        rel = self.the_uks.get_or_add_thing(rel_label, rel_parent)

        for m in src_mods:
            mod = self.the_uks.get_or_add_thing(m)
            self.the_uks.add_statement(src, "is", mod)
        for m in tgt_mods:
            mod = self.the_uks.get_or_add_thing(m)
            self.the_uks.add_statement(tgt, "is", mod)
        for m in rel_mods:
            mod = self.the_uks.get_or_add_thing(m)
            self.the_uks.add_statement(rel, "hasProperty", mod)

        return self.the_uks.add_statement(src, rel, tgt)

    def get_uks_thing(self, thing: str, parent: str | None = None) -> Thing | None:
        if self.the_uks is None:
            return None
        return self.the_uks.get_or_add_thing(thing, parent)

    def search_label_uks(self, label: str) -> Thing | None:
        if self.the_uks is None:
            return None
        return self.the_uks.labeled(label)

    def relationship_types(self) -> List[str]:
        if self.the_uks is None:
            return []
        rel_parent = self.the_uks.get_or_add_thing("RelationshipType")
        return [child.Label for child in rel_parent.Children]
