"""Deplacements, symetries et reseaux."""
from __future__ import annotations

import math

import pytest

from CAD_Core.math3d import Plane, Vec3, X_AXIS, Z_AXIS
from CAD_Core.primitives import box
from CAD_Core.profiles import Curve
from CAD_Core.transform3d import (align3d, align_to_face, array_along_helix,
                                  array_path, array_polar, array_rectangular,
                                  bounding_box, copy_items, explode_positions,
                                  mirror3d, move, rotate3d,
                                  rotate_between_points, scale3d)


@pytest.fixture()
def cube():
    return box(100, 100, 100)


def test_deplacer_et_copier(cube):
    assert move(cube, (500, 0, 0))[0].centroid.rounded(6) == (550.0, 50.0, 50.0)
    copies = copy_items(cube, (200, 0, 0), 3)
    assert len(copies) == 3
    assert [round(c.centroid.x) for c in copies] == [250, 450, 650]
    with pytest.raises(ValueError):
        copy_items(cube, (1, 0, 0), 0)


def test_rotations(cube):
    tourne = rotate3d(cube, Z_AXIS, 90)[0]
    assert tourne.volume == pytest.approx(cube.volume)
    assert tourne.centroid.rounded(6) == (-50.0, 50.0, 50.0)
    par_points = rotate_between_points(cube, (0, 0, 0), (0, 0, 1), 180)[0]
    assert par_points.centroid.rounded(6) == (-50.0, -50.0, 50.0)
    with pytest.raises(ValueError):
        rotate_between_points(cube, (0, 0, 0), (0, 0, 0), 90)


def test_echelle_et_miroir(cube):
    assert scale3d(cube, 2)[0].volume == pytest.approx(8e6)
    with pytest.raises(ValueError):
        scale3d(cube, 0)
    symetrie = mirror3d(cube, Plane.from_point_normal((0, 0, 0), X_AXIS))
    assert len(symetrie) == 2
    assert round(symetrie[1].centroid.x) == -50
    assert len(mirror3d(cube, Plane.from_point_normal((0, 0, 0), X_AXIS),
                        keep_source=False)) == 1


def test_alignement(cube):
    aligne = align3d(cube, [(0, 0, 0), (100, 0, 0)],
                     [(1000, 1000, 0), (1000, 1100, 0)])[0]
    assert aligne.volume == pytest.approx(cube.volume)
    assert aligne.centroid.rounded(3) == (950.0, 1050.0, 50.0)


def test_reseaux(cube):
    assert len(array_rectangular(cube, 3, 2, 2, 200, 200, 200)) == 12
    assert len(array_polar(cube, (0, 0, 0), Z_AXIS, 6, 360)) == 6
    assert len(array_path(cube, Curve.line((0, 0, 0), (1000, 0, 0)), 5)) == 5
    assert len(array_along_helix(cube, radius=500, count=8)) == 8
    with pytest.raises(ValueError):
        array_rectangular(cube, 0, 1, 1)
    with pytest.raises(ValueError):
        array_polar(cube, count=0)
    with pytest.raises(ValueError):
        array_path(cube, Curve.line((0, 0, 0), (0, 0, 0)), 3)


def test_reseau_sur_chemin_a_pas_impose(cube):
    occurrences = array_path(cube, Curve.line((0, 0, 0), (1000, 0, 0)), 1,
                             measure=True, spacing=250)
    assert len(occurrences) == 5


def test_boite_et_positions(cube):
    reseau = array_rectangular(cube, 3, 2, 1, 200, 200, 200)
    assert bounding_box(reseau).size.as_tuple() == (500.0, 300.0, 100.0)
    assert len(explode_positions(reseau)) == 6


def test_poser_sur_une_face(cube):
    pose = align_to_face(cube, 0, (500, 500, 500), (0, 0, 1))
    assert pose.volume == pytest.approx(cube.volume)
    assert pose.bbox.min.z == pytest.approx(500.0, abs=1e-6)
    with pytest.raises(ValueError):
        align_to_face(cube, 99, (0, 0, 0), (0, 0, 1))
