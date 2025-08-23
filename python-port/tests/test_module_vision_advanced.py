import math
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from modules.module_vision_find_segments_and_arcs import ModuleVisionFindSegmentsAndArcs
from modules.module_shape import ModuleShape
from modules.module_mental_model import ModuleMentalModel
from vision import PointPlus, Segment


def test_segments_and_arcs_detection():
    line_pts = [PointPlus(x, 0) for x in range(5)]
    arc_angles = [math.pi / 2, 2 * math.pi / 3, 3 * math.pi / 4]
    arc_pts = [PointPlus(6 + math.cos(a), math.sin(a)) for a in arc_angles]
    mod = ModuleVisionFindSegmentsAndArcs(edges=line_pts + arc_pts)
    mod.fire()
    assert len(mod.segments) == 1
    assert len(mod.arcs) == 1
    assert math.isclose(mod.segments[0].length, 4.0, rel_tol=1e-6)
    assert math.isclose(mod.arcs[0].radius, 1.0, rel_tol=1e-6)


def test_shape_and_mental_model():
    pts = [PointPlus(0, 0), PointPlus(1, 0), PointPlus(1, 1), PointPlus(0, 1), PointPlus(0, 0)]
    segments = [Segment(pts[i], pts[i + 1]) for i in range(4)]
    shape_mod = ModuleShape(segments=segments, arcs=[])
    shape_mod.fire()
    shapes = shape_mod.get_shapes()
    assert shapes and shapes[0]["type"] == "rectangle"
    mm = ModuleMentalModel()
    mm.ingest_shapes(shapes)
    assert mm.get_shape_count("rectangle") == 1
