"""Solides facettises et operations booleennes."""
from __future__ import annotations

import math

import pytest

from CAD_Core.math3d import Plane, Vec3, Z_AXIS
from CAD_Core.primitives import box, cylinder, sphere
from CAD_Core.solid import (Polygon, Solid, interfere, intersect_all,
                            subtract_all, union_all)


@pytest.fixture()
def cube():
    return box(100, 100, 100)


def test_proprietes_dun_cube(cube):
    assert cube.volume == pytest.approx(1e6)
    assert cube.area == pytest.approx(6e4)
    assert cube.signed_volume > 0
    assert cube.centroid.rounded(6) == (50.0, 50.0, 50.0)
    assert len(cube.vertices()) == 8
    assert len(cube.edges()) == 12


def test_controle_de_solide(cube):
    controle = cube.check()
    assert controle["ferme"] and controle["valide"]
    assert controle["aretes_libres"] == 0
    assert controle["faces_degenerees"] == 0


def test_union_volume_exact():
    resultat = box(100, 100, 100).union(box(50, 50, 50, (75, 25, 25)))
    assert resultat.volume == pytest.approx(1e6 + 50 ** 3 - 25 * 50 * 50, rel=1e-6)
    assert resultat.check()["ferme"]


def test_soustraction_volume_exact():
    resultat = box(100, 100, 100).subtract(box(50, 50, 50, (75, 25, 25)))
    assert resultat.volume == pytest.approx(1e6 - 25 * 50 * 50, rel=1e-6)
    assert resultat.check()["ferme"]


def test_intersection_volume_exact():
    resultat = box(100, 100, 100).intersect(box(50, 50, 50, (75, 25, 25)))
    assert resultat.volume == pytest.approx(25 * 50 * 50, rel=1e-6)
    assert resultat.check()["ferme"]


def test_soustraction_dune_sphere_ne_renvoie_pas_le_complementaire():
    """Une primitive mal orientee inverserait le resultat : on le verifie."""
    grande = box(1000, 1000, 1000)
    bille = sphere(300, (500, 500, 500), segments=24, rings=12)
    creuse = grande.subtract(bille)
    assert creuse.volume == pytest.approx(1e9 - bille.volume, rel=1e-3)
    assert creuse.volume > bille.volume


def test_percement_traversant():
    perce = box(1000, 1000, 1000).subtract(
        cylinder(200, 2000, (500, 500, -500), segments=64))
    attendu = 1e9 - math.pi * 200 ** 2 * 1000
    assert perce.volume == pytest.approx(attendu, rel=2e-3)
    assert perce.check()["ferme"]


def test_reunion_et_soustraction_de_listes():
    reunis = union_all([box(100, 100, 100), box(100, 100, 100, (200, 0, 0))])
    assert reunis.volume == pytest.approx(2e6)
    reste = subtract_all(box(200, 200, 200),
                         [box(50, 50, 300, (0, 0, -50)),
                          box(50, 50, 300, (150, 150, -50))])
    assert reste.volume == pytest.approx(200 ** 3 - 2 * 50 * 50 * 200, rel=1e-6)
    assert intersect_all([box(100, 100, 100),
                          box(100, 100, 100, (50, 0, 0))]).volume == \
        pytest.approx(50 * 100 * 100, rel=1e-6)


def test_separation_de_volumes_disjoints():
    morceaux = union_all([box(10, 10, 10), box(10, 10, 10, (100, 0, 0))]).separate()
    assert len(morceaux) == 2
    assert all(m.volume == pytest.approx(1000) for m in morceaux)


def test_detection_dinterference():
    rapport = interfere([box(100, 100, 100), box(100, 100, 100, (50, 0, 0)),
                         box(10, 10, 10, (900, 0, 0))])
    assert rapport["collisions"] == 1
    assert rapport["details"][0]["volume_mm3"] == pytest.approx(500000, rel=1e-6)


def test_proprietes_mecaniques(cube):
    fiche = cube.mass_properties(2400.0)
    assert fiche["volume_m3"] == pytest.approx(0.001)
    assert fiche["masse_kg"] == pytest.approx(2.4)
    assert fiche["centre_gravite"] == [50.0, 50.0, 50.0]
    assert fiche["faces"] == 6


def test_transformations_conservent_le_volume(cube):
    assert cube.translated((10, 20, 30)).volume == pytest.approx(cube.volume)
    assert cube.rotated(Z_AXIS, 0.7).volume == pytest.approx(cube.volume)
    assert cube.scaled(2).volume == pytest.approx(cube.volume * 8)
    miroir = cube.mirrored(Plane.from_point_normal((0, 0, 0), (1, 0, 0)))
    assert miroir.volume == pytest.approx(cube.volume)
    assert miroir.signed_volume > 0


def test_inversion_et_reorientation(cube):
    envers = cube.inverted()
    assert envers.signed_volume < 0
    assert envers.outward().signed_volume > 0


def test_triangulation_dun_contour_concave():
    contour = [Vec3(0, 0, 0), Vec3(4, 0, 0), Vec3(4, 4, 0), Vec3(2, 1, 0),
               Vec3(0, 4, 0)]
    triangles = Polygon(contour).triangulate()
    aire = sum(Polygon(list(t)).area for t in triangles)
    assert aire == pytest.approx(Polygon(contour).area, rel=1e-9)


def test_maillage_indexe(cube):
    sommets, faces = cube.to_mesh()
    assert len(sommets) == 8
    assert len(faces) == 6


def test_operation_sur_un_solide_vide(cube):
    vide = Solid([], "vide")
    assert cube.union(vide).volume == pytest.approx(cube.volume)
    assert cube.subtract(vide).volume == pytest.approx(cube.volume)
    assert cube.intersect(vide).polygons == []


def test_reparation_des_jonctions_en_t():
    brut = box(100, 100, 100).union(box(50, 50, 50, (75, 25, 25)))
    assert brut.heal().check()["aretes_libres"] == 0
