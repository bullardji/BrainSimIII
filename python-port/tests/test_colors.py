import sys
from pathlib import Path

# Allow importing modules from the python-port directory
sys.path.append(str(Path(__file__).resolve().parents[1]))

from colors import (
    HSLColor,
    color_from_name,
    get_color_name_from_hsl,
    is_valid_color_name,
)


def test_color_from_name_and_validation():
    assert color_from_name("red") == (255, 0, 0)
    assert color_from_name("Chartreuse") == (127, 255, 0)
    assert color_from_name("SPRING GREEN") == (0, 255, 127)
    assert color_from_name("unknown") == (111, 111, 111)
    # validation is case-insensitive
    assert is_valid_color_name("blue")
    assert is_valid_color_name("Blue")
    assert not is_valid_color_name("unknown")


def test_hsl_round_trip():
    rgb = (10, 200, 100)
    hsl = HSLColor.from_rgb(*rgb)
    assert hsl.to_rgb() == rgb


def test_get_color_name_from_hsl():
    red = HSLColor.from_rgb(255, 0, 0)
    assert get_color_name_from_hsl(red) == "Red"
    white = HSLColor(luminance=0.95)
    assert get_color_name_from_hsl(white) == "White"
