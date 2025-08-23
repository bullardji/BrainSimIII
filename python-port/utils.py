from __future__ import annotations

import datetime, os, math, threading
from typing import Callable, Iterable, List, Optional, Tuple, TypeVar
try:
    from .angle import Angle
except ImportError:
    from angle import Angle


T = TypeVar("T")


def find_first(source: Iterable[T], condition: Callable[[T], bool]) -> Optional[T]:
    """Return the first item in *source* satisfying *condition* or ``None``."""
    for item in source:
        if condition(item):
            return item
    return None


def find_all(source: Iterable[T], condition: Callable[[T], bool]) -> List[T]:
    """Return all items in *source* satisfying *condition*."""
    return [item for item in source if condition(item)]


def rad(degrees: float) -> float:
    """Convert degrees to radians."""
    return math.radians(degrees)


def round_to_significant_digits(d: float, digits: int) -> float:
    if d == 0:
        return 0.0
    scale = 10 ** (math.floor(math.log10(abs(d))) + 1)
    return scale * round(d / scale, digits)


def int_to_color(the_color: int) -> Tuple[int, int, int]:
    return (
        the_color >> 16 & 0xFF,
        the_color >> 8 & 0xFF,
        the_color & 0xFF,
    )


def color_to_int(r: int, g: int, b: int) -> int:
    return (r << 16) + (g << 8) + b


def build_annotated_image_file_name(
    folder: str,
    delta_turn: Angle,
    delta_move: float,
    camera_pan: Angle | None,
    camera_tilt: Angle | None,
    extension: str,
) -> str:
    camera_pan = camera_pan or Angle.from_degrees(0)
    camera_tilt = camera_tilt or Angle.from_degrees(0)
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = (
        f"{timestamp}_{int(delta_turn.degrees)}_{delta_move:.1f}_"
        f"{int(camera_pan.degrees)}_{int(camera_tilt.degrees)}_.{extension}"
    )
    return os.path.join(folder, filename)


def image_has_movement(filename: str) -> bool:
    name = os.path.splitext(os.path.basename(filename))[0]
    parts = name.split("_")
    if len(parts) != 8:
        return False
    return "_0_0.0_" not in name


def get_turn_delta_from_annotated_image_file_name(filename: str) -> Angle:
    parts = os.path.basename(filename).split("_")
    if len(parts) <= 3:
        return Angle.from_degrees(0)
    try:
        return Angle.from_degrees(int(parts[3]))
    except ValueError:
        return Angle.from_degrees(0)


def get_move_delta_from_annotated_image_file_name(filename: str) -> float:
    parts = os.path.basename(filename).split("_")
    if len(parts) <= 4:
        return 0.0
    try:
        return float(parts[4])
    except ValueError:
        return 0.0


def get_camera_pan_from_annotated_image_file_name(filename: str) -> Angle:
    parts = os.path.basename(filename).split("_")
    if len(parts) <= 5:
        return Angle.from_degrees(0)
    try:
        return Angle.from_degrees(int(parts[5]))
    except ValueError:
        return Angle.from_degrees(0)


def get_camera_tilt_from_annotated_image_file_name(filename: str) -> Angle:
    parts = os.path.basename(filename).split("_")
    if len(parts) <= 6:
        return Angle.from_degrees(0)
    try:
        return Angle.from_degrees(int(parts[6]))
    except ValueError:
        return Angle.from_degrees(0)


_trackid = 1000
_trackid_lock = threading.Lock()


def new_track_id() -> str:
    """Return a unique tracking id as a zero-padded string."""
    global _trackid
    with _trackid_lock:
        _trackid += 1
        return f"{_trackid:04d}"


def reset_track_id(value: int = 1000) -> None:
    """Reset the internal track id counter (for testing)."""
    global _trackid
    with _trackid_lock:
        _trackid = int(value)
