"""Algebre 3D : vecteurs, matrices, plans, boites englobantes."""
from __future__ import annotations

import math

import pytest

from CAD_Core.math3d import (BBox3, Mat4, ORIGIN, Plane, Vec3, X_AXIS, XY_PLANE,
                             Y_AXIS, Z_AXIS, polygon_area_3d, polygon_normal)


def test_operations_vectorielles():
    a, b = Vec3(1, 2, 3), Vec3(4, 5, 6)
    assert (a + b).as_tuple() == (5, 7, 9)
    assert (b - a).as_tuple() == (3, 3, 3)
    assert (a * 2).as_tuple() == (2, 4, 6)
    assert a.dot(b) == 32
    assert a.cross(b).as_tuple() == (-3, 6, -3)
    assert Vec3(3, 4, 0).norm() == 5.0
    assert Vec3(3, 4, 0).unit().norm() == pytest.approx(1.0)
    assert Vec3(0, 0, 0).unit().as_tuple() == (0.0, 0.0, 0.0)


def test_conversion_souple():
    assert Vec3.of((1, 2, 3)).as_tuple() == (1.0, 2.0, 3.0)
    assert Vec3.of([4, 5]).as_tuple() == (4.0, 5.0, 0.0)
    assert Vec3.of({"x": 7, "z": 9}).as_tuple() == (7.0, 0.0, 9.0)


def test_perpendiculaire_toujours_orthogonale():
    for vecteur in (X_AXIS, Y_AXIS, Z_AXIS, Vec3(1, 1, 1), Vec3(0.01, 0, 0.99)):
        assert vecteur.dot(vecteur.any_perpendicular()) == pytest.approx(0.0,
                                                                        abs=1e-9)


def test_rotation_et_inverse():
    matrice = Mat4.rotation(Z_AXIS, math.pi / 2)
    tourne = matrice.apply(Vec3(1, 0, 0))
    assert tourne.rounded(9) == (0.0, 1.0, 0.0)
    assert matrice.inverse() * matrice == Mat4.identity()
    assert matrice.determinant() == pytest.approx(1.0)


def test_rotation_autour_dun_point():
    matrice = Mat4.rotation(Z_AXIS, math.pi, base=(10, 0, 0))
    assert matrice.apply(Vec3(11, 0, 0)).rounded(6) == (9.0, 0.0, 0.0)


def test_echelle_et_symetrie():
    assert Mat4.scaling(3).apply(Vec3(1, 2, 3)).as_tuple() == (3.0, 6.0, 9.0)
    miroir = Mat4.mirror(Plane.from_point_normal((0, 0, 0), X_AXIS))
    assert miroir.apply(Vec3(5, 1, 2)).rounded(6) == (-5.0, 1.0, 2.0)
    assert miroir.is_mirroring()


def test_alignement_sur_deux_points():
    matrice = Mat4.align([(0, 0, 0), (1, 0, 0)], [(5, 5, 5), (5, 6, 5)])
    assert matrice.apply((0, 0, 0)).rounded(6) == (5.0, 5.0, 5.0)
    assert matrice.apply((1, 0, 0)).rounded(6) == (5.0, 6.0, 5.0)


def test_alignement_refuse_des_listes_incoherentes():
    with pytest.raises(ValueError):
        Mat4.align([(0, 0, 0)], [])


def test_matrice_singuliere():
    with pytest.raises(ValueError):
        Mat4([0] * 16).inverse()


def test_plan_distance_projection_intersection():
    plan = Plane.from_points((0, 0, 0), (1, 0, 0), (0, 1, 0))
    assert plan.normal.rounded(6) == (0.0, 0.0, 1.0)
    assert plan.signed_distance((0, 0, 4)) == 4.0
    assert plan.project((3, 2, 9)).rounded(6) == (3.0, 2.0, 0.0)
    coupe = plan.line_intersection((0, 0, -2), (0, 0, 6))
    assert coupe.rounded(6) == (0.0, 0.0, 0.0)
    assert plan.line_intersection((0, 0, 1), (0, 0, 2)) is None


def test_plan_refuse_trois_points_alignes():
    with pytest.raises(ValueError):
        Plane.from_points((0, 0, 0), (1, 0, 0), (2, 0, 0))


def test_repere_du_plan_suit_la_norme_dxf():
    u, v = XY_PLANE.basis()
    assert u.rounded(6) == (1.0, 0.0, 0.0)
    assert v.rounded(6) == (0.0, 1.0, 0.0)


def test_boite_englobante():
    boite = BBox3.of([(0, 0, 0), (10, 4, 6)])
    assert boite.valid
    assert boite.size.as_tuple() == (10.0, 4.0, 6.0)
    assert boite.center.as_tuple() == (5.0, 2.0, 3.0)
    assert boite.contains((5, 2, 3))
    assert not boite.contains((50, 2, 3))
    assert boite.intersects(BBox3.of([(9, 0, 0), (20, 4, 6)]))
    assert not boite.intersects(BBox3.of([(30, 0, 0), (40, 4, 6)]))
    assert BBox3().to_dict() == {"vide": True}


def test_aire_et_normale_dun_polygone():
    carre = [(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)]
    assert polygon_area_3d(carre) == pytest.approx(4.0)
    assert polygon_normal(carre).rounded(6) == (0.0, 0.0, 1.0)
    assert polygon_area_3d([(0, 0, 0), (1, 0, 0)]) == 0.0


def test_format_colonne_pour_webgl():
    matrice = Mat4.translation((1, 2, 3))
    colonnes = matrice.to_column_major()
    assert colonnes[12:15] == [1.0, 2.0, 3.0]
