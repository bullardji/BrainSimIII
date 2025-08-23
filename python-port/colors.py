"""Color utilities for the BrainSimIII Python port.

This module ports a subset of the color-related helpers from
``BrainSimulator/Utils.cs`` into Python. It provides an ``HSLColor`` class
for converting between RGB and HSL color spaces and helpers for mapping
color names.
"""
from __future__ import annotations

from dataclasses import dataclass
import colorsys
from typing import Dict, Tuple, List


@dataclass
class HSLColor:
    """Simple representation of an HSL color.

    Hue is expressed in degrees ``[0, 360)`` while saturation and luminance
    are in the range ``[0, 1]``.
    """

    hue: float = 0.0
    saturation: float = 0.0
    luminance: float = 0.0

    @classmethod
    def from_rgb(cls, r: int, g: int, b: int) -> "HSLColor":
        """Create an :class:`HSLColor` from integer RGB values."""
        # ``colorsys`` uses the HLS convention with hue [0,1)
        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        return cls(hue=h * 360.0, saturation=s, luminance=l)

    def to_rgb(self) -> Tuple[int, int, int]:
        """Return the color as integer ``(r, g, b)`` tuple."""
        r, g, b = colorsys.hls_to_rgb(self.hue / 360.0, self.luminance, self.saturation)
        # Use round to avoid off-by-one errors when converting back to ints
        return round(r * 255), round(g * 255), round(b * 255)

    def copy(self) -> "HSLColor":
        return HSLColor(self.hue, self.saturation, self.luminance)

    def __sub__(self, other: "HSLColor") -> float:
        """Return a difference metric similar to the C# implementation."""
        c1 = self.copy()
        c2 = other.copy()
        # whites/blacks/greys normalised to hue 0.5 as in C# code
        if c1.luminance > 0.95 or c1.luminance < 0.1 or c1.saturation < 0.1:
            c1.hue = 0.5
        if c2.luminance > 0.95 or c2.luminance < 0.1 or c2.saturation < 0.1:
            c2.hue = 0.5
        diff = abs(c1.hue - c2.hue) * 5 + abs(c1.saturation - c2.saturation) + abs(c1.luminance - c2.luminance)
        return diff / 7

    def equals(self, other: "HSLColor") -> bool:
        if other is None:
            return False
        if self.luminance < 0.05 and other.luminance < 0.05:
            return True
        if self.luminance > 0.95 and other.luminance > 0.95:
            return True
        abs_hue_diff = abs(self.hue - other.hue)
        return abs_hue_diff < 5 or abs_hue_diff > 355


_COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "orange": (255, 158, 0),
    "yellow": (255, 255, 0),
    "chartreuse": (127, 255, 0),
    "lime": (0, 255, 0),
    "spring green": (0, 255, 127),
    "green": (0, 128, 0),
    "teal": (0, 128, 128),
    "cyan": (0, 255, 255),
    "azure": (0, 127, 255),
    "blue": (0, 0, 255),
    "magenta": (255, 0, 255),
    "purple": (128, 0, 128),
    "rose": (255, 0, 127),
    "silver": (192, 192, 192),
    "gray": (128, 128, 128),
    "maroon": (128, 0, 0),
    "olive": (128, 128, 0),
    "navy": (0, 0, 128),
}


def color_from_name(color_name: str) -> Tuple[int, int, int]:
    """Return an RGB tuple for a given color name.

    Unrecognised names default to a medium gray to match the C# helper.
    """
    if not color_name:
        return (111, 111, 111)
    return _COLOR_MAP.get(color_name.lower(), (111, 111, 111))


_VALID_COLOR_NAMES: List[str] = [name.title() for name in _COLOR_MAP.keys()]


def is_valid_color_name(color_name: str) -> bool:
    """Return ``True`` if ``color_name`` is known regardless of case."""
    if not color_name:
        return False
    return color_name.lower() in _COLOR_MAP


def get_color_name_from_hsl(hsl: HSLColor) -> str:
    """Return the nearest human-friendly color name for ``hsl``.

    This mirrors ``Utils.GetColorNameFromHSL`` in the C# code.
    """
    if hsl.luminance < 0.10:
        return "Black"
    if hsl.luminance > 0.9:
        return "White"
    if hsl.saturation < 0.12:
        return "Gray"
    h = hsl.hue
    if h < 15 or h >= 345:
        return "Red"
    if 15 <= h < 45:
        return "Orange"
    if 45 <= h < 75:
        return "Yellow"
    if 75 <= h < 105:
        return "Chartreuse"
    if 105 <= h < 135:
        return "Green" if hsl.luminance < 0.40 else "Lime"
    if 135 <= h < 165:
        return "Spring Green"
    if 165 <= h < 195:
        return "Cyan"
    if 195 <= h < 225:
        return "Azure"
    if 225 <= h < 255:
        return "Blue"
    if 255 <= h < 315:
        return "Purple" if hsl.luminance < 0.40 else "Magenta"
    if 315 <= h < 345:
        return "Rose"
    return "Gray"
