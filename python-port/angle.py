import math

class Angle:
    """Represents an angle in radians with helpers for degree conversion."""

    def __init__(self, radians: float = 0.0) -> None:
        self.the_angle = float(radians)

    @property
    def degrees(self) -> float:
        """Return the angle in degrees."""
        return self.the_angle * 180.0 / math.pi

    @degrees.setter
    def degrees(self, value: float) -> None:
        self.the_angle = float(value) * math.pi / 180.0

    @staticmethod
    def from_degrees(degrees: float) -> "Angle":
        return Angle(degrees * math.pi / 180.0)

    def __float__(self) -> float:
        return self.the_angle

    def __sub__(self, other: "Angle") -> "Angle":
        return Angle(self.the_angle - float(other))

    def __add__(self, other: "Angle") -> "Angle":
        return Angle(self.the_angle + float(other))

    def __repr__(self) -> str:
        return f"{self.the_angle:.2f} {self.degrees:.1f}°"

    # ------------------------------------------------------------------
    # Comparison and hashing support
    # ------------------------------------------------------------------

    def _coerce(self, other) -> float | None:
        """Return *other* as a float if possible, ``None`` otherwise."""
        if isinstance(other, Angle):
            return other.the_angle
        try:
            return float(other)
        except (TypeError, ValueError):
            return None

    def __eq__(self, other: object) -> bool:
        other_val = self._coerce(other)
        if other_val is None:
            return NotImplemented  # type: ignore[return-value]
        return self.the_angle == other_val

    def __lt__(self, other: "Angle") -> bool:
        other_val = self._coerce(other)
        if other_val is None:
            return NotImplemented  # type: ignore[return-value]
        return self.the_angle < other_val

    def __le__(self, other: "Angle") -> bool:
        other_val = self._coerce(other)
        if other_val is None:
            return NotImplemented  # type: ignore[return-value]
        return self.the_angle <= other_val

    def __gt__(self, other: "Angle") -> bool:
        other_val = self._coerce(other)
        if other_val is None:
            return NotImplemented  # type: ignore[return-value]
        return self.the_angle > other_val

    def __ge__(self, other: "Angle") -> bool:
        other_val = self._coerce(other)
        if other_val is None:
            return NotImplemented  # type: ignore[return-value]
        return self.the_angle >= other_val

    def __hash__(self) -> int:
        return hash(self.the_angle)

    def normalize(self) -> "Angle":
        a = self.the_angle % (2 * math.pi)
        if a < 0:
            a += 2 * math.pi
        return Angle(a)
