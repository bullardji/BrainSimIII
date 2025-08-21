import sys
import math
import sys
from pathlib import Path


# Allow importing modules from the python-port directory
sys.path.append(str(Path(__file__).resolve().parents[1]))

import utils
from angle import Angle


def test_round_to_significant_digits():
    assert utils.round_to_significant_digits(123.456, 2) == 120.0


def test_color_conversion():
    color_int = utils.color_to_int(1, 2, 3)
    assert utils.int_to_color(color_int) == (1, 2, 3)


def test_build_and_parse_filename(tmp_path):
    fn = utils.build_annotated_image_file_name(
        folder=str(tmp_path),
        delta_turn=Angle.from_degrees(5),
        delta_move=1.0,
        camera_pan=Angle.from_degrees(2),
        camera_tilt=Angle.from_degrees(3),
        extension="jpg",
    )
    assert utils.image_has_movement(fn)
    assert utils.get_turn_delta_from_annotated_image_file_name(fn).degrees == 5
    assert utils.get_move_delta_from_annotated_image_file_name(fn) == 1.0
    assert utils.get_camera_pan_from_annotated_image_file_name(fn).degrees == 2
    assert utils.get_camera_tilt_from_annotated_image_file_name(fn).degrees == 3

    fn2 = utils.build_annotated_image_file_name(
        str(tmp_path),
        Angle.from_degrees(0),
        0.0,
        Angle.from_degrees(0),
        Angle.from_degrees(0),
        "jpg",
    )
    assert not utils.image_has_movement(fn2)


def test_find_first_and_find_all():
    data = [1, 2, 3, 4, 5]
    assert utils.find_first(data, lambda x: x > 3) == 4
    assert utils.find_first(data, lambda x: x > 10) is None
    assert utils.find_all(data, lambda x: x % 2 == 0) == [2, 4]


def test_rad():
    assert math.isclose(utils.rad(180), math.pi)
