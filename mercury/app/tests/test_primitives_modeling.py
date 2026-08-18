"""Primitives volumiques et outils de creation a partir d'un profil."""
from __future__ import annotations

import math

import pytest

from CAD_Core.math3d import Vec3, Z_AXIS
from CAD_Core.mesh_tools import (smooth, statistics, subdivide, triangulate,
                                 unify_normals, vertex_normals)
from CAD_Core.modeling import (coons_surface, extrude, loft, planar_surface,
                               presspull, revolve, ruled_surface, sweep,
                               tabulated_surface, thicken)
from CAD_Core.primitives import (box, cone, cylinder, mesh_box, polysolid,
                                 pyramid, sphere, torus, wedge)
from CAD_Core.profiles import Curve, Profile


@pytest.mark.parametrize("solide,attendu,tolerance", [
    (box(100, 200, 300), 6e6, 1e-9),
    (wedge(100, 100, 100), 5e5, 1e-9),
    (cylinder(50, 100, segments=180), math.pi * 2500 * 100, 1e-3),
    (cone(50, 100, segments=180), math.pi * 2500 * 100 / 3, 1e-3),
    (sphere(50, segments=64, rings=32), 4 / 3 * math.pi * 125000, 5e-3),
    (torus(100, 20, segments=64, tube_segments=32),
     2 * math.pi ** 2 * 100 * 400, 1e-2),
    (pyramid(50, 100, 4), 2 * 2500 * 100 / 3, 1e-9),
])
def test_volume_des_primitives(solide, attendu, tolerance):
    assert solide.volume == pytest.approx(attendu, rel=max(tolerance, 1e-9))
    assert solide.signed_volume > 0, "les faces doivent regarder vers l'exterieur"
    assert solide.check()["ferme"]


@pytest.mark.parametrize("fabrique,arguments", [
    (box, {"length": 0}), (wedge, {"width": -5}), (cylinder, {"radius": 0}),
    (sphere, {"radius": -1}), (torus, {"tube_radius": 0}),
    (pyramid, {"sides": 2}),
])
def test_primitives_refusent_des_dimensions_absurdes(fabrique, arguments):
    with pytest.raises(ValueError):
        fabrique(**arguments)


def test_boite_centree():
    centree = box(100, 100, 100, centered=True)
    assert centree.centroid.rounded(6) == (0.0, 0.0, 0.0)


def test_polysolide_suit_la_polyligne():
    mur = polysolid([(0, 0, 0), (1000, 0, 0), (1000, 1000, 0)], 200, 2500)
    assert mur.check()["ferme"]
    assert mur.volume == pytest.approx(2 * 1000 * 200 * 2500 - 100 * 100 * 2500,
                                       rel=1e-6)


def test_polysolide_refuse_une_justification_inconnue():
    with pytest.raises(ValueError):
        polysolid([(0, 0, 0), (100, 0, 0)], justify="milieu")


def test_extrusion_simple_et_percee():
    plein = extrude(Profile.rectangle(100, 50), 200)
    assert plein.volume == pytest.approx(1e6)
    perce = extrude(Profile.rectangle(100, 50).with_hole(
        Profile.rectangle(20, 20, (40, 15, 0)).outline), 100)
    assert perce.volume == pytest.approx(460000)
    assert perce.check()["ferme"]


def test_extrusion_avec_depouille():
    hauteur, angle = 100.0, 10.0
    solide = extrude(Profile.rectangle(100, 100), hauteur, taper=angle)
    cote = 100 - 2 * hauteur * math.tan(math.radians(angle))
    attendu = hauteur / 3 * (10000 + cote ** 2 + math.sqrt(10000 * cote ** 2))
    assert solide.volume == pytest.approx(attendu, rel=1e-6)


def test_extrusion_refuse_une_hauteur_nulle():
    with pytest.raises(ValueError):
        extrude(Profile.rectangle(10, 10), 0.0)


def test_revolution_totale_et_partielle():
    profil = Profile.polyline([(50, 0, 0), (100, 0, 0), (100, 0, 80),
                               (50, 0, 80)])
    complet = math.pi * (100 ** 2 - 50 ** 2) * 80
    assert revolve(profil, (0, 0, 0), Z_AXIS, 2 * math.pi, 72).volume == \
        pytest.approx(complet, rel=3e-3)
    quart = revolve(profil, (0, 0, 0), Z_AXIS, math.pi / 2, 72)
    assert quart.volume == pytest.approx(complet / 4, rel=3e-3)
    assert quart.check()["ferme"]


def test_balayage_droit_et_helicoidal():
    droit = sweep(Profile.circle(10, segments=64), Curve.line((0, 0, 0),
                                                              (0, 0, 500)))
    assert droit.volume == pytest.approx(math.pi * 100 * 500, rel=3e-3)
    assert droit.check()["ferme"]
    helicoidal = sweep(Profile.circle(10, segments=24),
                       Curve.helix(turns=2, height=200, base_radius=80))
    assert helicoidal.check()["ferme"]
    assert helicoidal.volume > 0


def test_balayage_avec_torsion_reste_ferme():
    vrille = sweep(Profile.rectangle(40, 20, centered=True),
                   Curve.line((0, 0, 0), (0, 0, 400)), twist=90)
    assert vrille.check()["ferme"]
    assert vrille.volume == pytest.approx(40 * 20 * 400, rel=0.06)


def test_lissage_entre_deux_sections():
    resultat = loft([Profile.rectangle(100, 100, (0, 0, 0), centered=True),
                     Profile.rectangle(50, 50, (0, 0, 200), centered=True)])
    attendu = 200 / 3 * (10000 + 2500 + math.sqrt(10000 * 2500))
    assert resultat.volume == pytest.approx(attendu, rel=1e-6)
    assert resultat.check()["ferme"]


def test_lissage_exige_deux_sections():
    with pytest.raises(ValueError):
        loft([Profile.rectangle(10, 10)])


def test_appuyer_tirer_et_epaissir():
    assert presspull(Profile.rectangle(200, 100), 50).volume == \
        pytest.approx(1e6)
    epaissi = thicken(planar_surface(Profile.rectangle(200, 100)).polygons, 20)
    assert epaissi.volume == pytest.approx(400000)
    assert epaissi.check()["ferme"]


def test_surfaces_reglees_et_coons():
    reglee = ruled_surface(Curve.line((0, 0, 0), (100, 0, 0)),
                           Curve.line((0, 100, 0), (100, 100, 0)))
    assert reglee.area == pytest.approx(10000, rel=1e-6)
    tabulee = tabulated_surface(Curve.line((0, 0, 0), (100, 0, 0)), (0, 0, 50))
    assert tabulee.area == pytest.approx(5000, rel=1e-6)
    carreau = coons_surface([Curve.line((0, 0, 0), (100, 0, 0)),
                             Curve.line((100, 0, 0), (100, 100, 0)),
                             Curve.line((0, 100, 0), (100, 100, 0)),
                             Curve.line((0, 0, 0), (0, 100, 0))])
    assert carreau.area == pytest.approx(10000, rel=1e-6)


def test_coons_exige_quatre_courbes():
    with pytest.raises(ValueError):
        coons_surface([Curve.line((0, 0, 0), (1, 0, 0))])


def test_outils_de_maillage():
    cube = box(100, 100, 100)
    assert len(triangulate(cube).polygons) == 12
    assert len(subdivide(cube, 1).polygons) == 24
    lisse = smooth(cube, 1)
    assert len(lisse.polygons) == 24
    assert lisse.volume < cube.volume        # le lissage rentre les coins
    assert len(vertex_normals(cube)) == 8
    assert unify_normals(cube.inverted()).signed_volume > 0
    fiche = statistics(cube)
    assert fiche["ferme"] and fiche["sommets"] == 8


def test_primitive_de_maillage():
    assert len(mesh_box(100, 100, 100, divisions=2).polygons) == 24


def test_profils_et_courbes():
    assert Profile.rectangle(100, 50).area == pytest.approx(5000)
    assert Profile.circle(50, segments=360).area == pytest.approx(math.pi * 2500,
                                                                  rel=1e-4)
    assert Profile.regular_polygon(6, 100).area == pytest.approx(
        3 * math.sqrt(3) / 2 * 100 ** 2, rel=1e-9)
    assert Profile.rounded_rectangle(100, 60, 10).area == pytest.approx(
        100 * 60 - (4 - math.pi) * 100, rel=1e-3)
    with pytest.raises(ValueError):
        Profile.regular_polygon(2, 10)
    helice = Curve.helix(turns=2, height=100, base_radius=50)
    assert helice.length > 2 * math.pi * 50 * 2
    assert len(Curve.circle((0, 0, 0), 10, segments=32).points) == 32
    assert Curve.line((0, 0, 0), (30, 40, 0)).length == pytest.approx(50.0)
    assert len(Curve.line((0, 0, 0), (100, 0, 0)).resampled(11).points) == 11
