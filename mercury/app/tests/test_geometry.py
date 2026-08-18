"""Tests du noyau geometrique : ce sont les fondations, ils passent d'abord."""
from __future__ import annotations

import math

import pytest

from CAD_Core.geometry import (
    Segment, Vec2, offset_polygon, point_in_polygon, polygon_area,
    polygon_centroid, polygon_perimeter, segment_intersection,
)


def test_vecteurs():
    a, b = Vec2(3, 4), Vec2(1, 0)
    assert a.norm() == 5.0
    assert abs(a.unit().norm() - 1.0) < 1e-9
    assert (a + b).as_tuple() == (4, 4)
    assert (a - b).as_tuple() == (2, 4)
    assert a.dot(b) == 3
    assert a.cross(b) == -4
    assert b.perp().as_tuple() == (0, 1)


def test_segment():
    s = Segment(Vec2(0, 0), Vec2(10, 0))
    assert s.length == 10
    assert s.midpoint.as_tuple() == (5, 0)
    assert s.point_at(0.5).as_tuple() == (5, 0)
    assert s.distance_to(Vec2(5, 3)) == 3
    assert s.distance_to(Vec2(-5, 0)) == 5      # au dela de l'extremite


def test_intersection():
    a = Segment(Vec2(0, 0), Vec2(10, 0))
    b = Segment(Vec2(5, -5), Vec2(5, 5))
    point, t, u = segment_intersection(a, b)
    assert abs(point.x - 5) < 1e-9 and abs(point.y) < 1e-9
    assert 0 < t < 1 and 0 < u < 1
    assert segment_intersection(a, Segment(Vec2(0, 3), Vec2(10, 3))) is None


def test_polygone():
    carre = [Vec2(0, 0), Vec2(1000, 0), Vec2(1000, 1000), Vec2(0, 1000)]
    assert polygon_area(carre) == 1_000_000
    assert polygon_perimeter(carre) == 4000
    centre = polygon_centroid(carre)
    assert abs(centre.x - 500) < 1e-6 and abs(centre.y - 500) < 1e-6
    assert point_in_polygon(Vec2(500, 500), carre)
    assert not point_in_polygon(Vec2(1500, 500), carre)


def test_offset_dans_les_deux_sens():
    """Distance negative : le contour retrecit. Positive : il grandit."""
    carre = [Vec2(0, 0), Vec2(1000, 0), Vec2(1000, 1000), Vec2(0, 1000)]
    reduit = offset_polygon(carre, -100)
    assert abs(abs(polygon_area(reduit)) - 640_000) < 1000,         "attendu 800 x 800 mm, obtenu %.0f" % abs(polygon_area(reduit))
    agrandi = offset_polygon(carre, 100)
    assert abs(abs(polygon_area(agrandi)) - 1_440_000) < 1000
    # un contour oriente dans l'autre sens doit se comporter pareil
    inverse = list(reversed(carre))
    assert abs(abs(polygon_area(offset_polygon(inverse, -100))) - 640_000) < 1000
