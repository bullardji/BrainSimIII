import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import math

from vision.point_plus import PointPlus


def test_point_operations():
    p1 = PointPlus(1, 2, 0, 0.8)
    p2 = PointPlus(3, 4, 1, 0.6)

    # operator overloads and confidence averaging
    assert p1 + p2 == PointPlus(4, 6, 1, 0.7)
    assert p2 - p1 == PointPlus(2, 2, 1, 0.7)

    # scalar multiply keeps confidence
    assert p1 * 2 == PointPlus(2, 4, 0, 0.8)

    # distance includes z component
    assert round(p1.distance_to(p2), 5) == round((2**2 + 2**2 + 1**2) ** 0.5, 5)

    # rotation around Z axis (allow for floating rounding)
    rotated = PointPlus(1, 0).rotate(math.pi / 2).to_tuple()
    assert round(rotated[0], 6) == 0.0
    assert round(rotated[1], 6) == 1.0

    # polar conversions
    p3 = PointPlus.from_polar(1, math.pi / 4)
    radius, angle = p3.to_polar()
    assert round(radius, 5) == 1.0
    assert round(angle, 5) == round(math.pi / 4, 5)
