from __future__ import annotations

"""Mapping between Thing labels and objects.

This mirrors the C# `ThingLabels` static helper which keeps a global
case-insensitive dictionary of all created `Thing` instances. Labels are
stored case-insensitively but the original casing is preserved on the
`Thing` instances themselves.
"""

from typing import Dict, Optional


class ThingLabels:
    _labels: Dict[str, "Thing"] = {}

    @classmethod
    def add_thing_label(cls, label: str, thing: "Thing") -> str:
        """Associate *label* with *thing*, auto-incrementing on collisions.

        Mimics the behaviour of the C# implementation which automatically
        appends digits when a label already exists.  A trailing ``"*"`` forces
        numbering to start at 0.  Any previous label mapped to ``thing`` is
        removed before assignment.
        """

        if label == "":
            return label

        # Remove any previous label associated with this Thing
        old = getattr(thing, "_label", "")
        if old:
            cls._labels.pop(old.lower(), None)

        base = label
        cur = -1
        if label.endswith("*"):
            base = label[:-1]
            cur = 0
            label = f"{base}{cur}"

        while True:
            key = label.lower()
            existing = cls._labels.get(key)
            if existing is None or existing is thing:
                cls._labels[key] = thing
                return label
            cur += 1
            label = f"{base}{cur}"

    @classmethod
    def get_thing(cls, label: str) -> Optional["Thing"]:
        return cls._labels.get(label.lower())

    @classmethod
    def remove_thing_label(cls, label: str) -> None:
        cls._labels.pop(label.lower(), None)

    @classmethod
    def clear_label_list(cls) -> None:
        cls._labels.clear()
