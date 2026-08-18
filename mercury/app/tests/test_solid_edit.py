"""Edition de solides : raccords, chanfreins, gaine, coupe, section."""
from __future__ import annotations

import math

import pytest

from CAD_Core.math3d import Plane, Vec3, Z_AXIS
from CAD_Core.primitives import box, cylinder
from CAD_Core.solid_edit import (chamfer_all_edges, chamfer_edge,
                                 convert_to_solid, convert_to_surface,
                                 dihedral_angle, extract_edges, face_report,
                                 fillet_all_edges, fillet_edge, imprint,
                                 offset_solid, section_loops,
                                 section_plane_view, section_profile,
                                 sharp_edges, shell, slice_solid, taper_faces)


@pytest.fixture()
def cube():
    return box(200, 200, 200)


def test_aretes_vives_dun_cube(cube):
    aretes = sharp_edges(cube)
    assert len(aretes) == 12
    assert all(abs(dihedral_angle(cube, faces) - 90.0) < 1e-6
               for _, _, faces in aretes)


def test_chanfrein_dune_seule_arete(cube):
    arete = sharp_edges(cube)[0][:2]
    resultat = chamfer_edge(cube, arete, 20)
    assert resultat.volume == pytest.approx(200 ** 3 - 0.5 * 20 * 20 * 200,
                                            rel=1e-6)


def test_raccord_dune_seule_arete(cube):
    arete = sharp_edges(cube)[0][:2]
    resultat = fillet_edge(cube, arete, 20, segments=16)
    attendu = 200 ** 3 - (400 - math.pi * 100) * 200
    assert resultat.volume == pytest.approx(attendu, rel=5e-3)


def test_raccord_de_toutes_les_aretes_reste_etanche(cube):
    arrondi = fillet_all_edges(cube, 20, segments=8)
    minkowski = (160 ** 3 + 6 * 160 ** 2 * 20 + 3 * math.pi * 160 * 400
                 + 4 / 3 * math.pi * 8000)
    assert arrondi.volume == pytest.approx(minkowski, rel=0.01)
    assert arrondi.check()["ferme"]


def test_chanfrein_de_toutes_les_aretes(cube):
    chanfreine = chamfer_all_edges(cube, 20)
    assert chanfreine.volume < cube.volume
    assert chanfreine.volume > cube.volume * 0.9
    assert chanfreine.check()["ferme"]


def test_rayon_ou_distance_invalide(cube):
    arete = sharp_edges(cube)[0][:2]
    with pytest.raises(ValueError):
        fillet_edge(cube, arete, 0)
    with pytest.raises(ValueError):
        chamfer_edge(cube, arete, -5)


def test_gaine_fermee_et_ouverte():
    creuse = shell(box(200, 200, 200), 20)
    assert creuse.volume == pytest.approx(200 ** 3 - 160 ** 3, rel=1e-6)
    assert creuse.check()["ferme"]
    ouverte = shell(box(200, 200, 200), 20, open_faces=[1])
    assert ouverte.volume == pytest.approx(200 ** 3 - 160 ** 3 - 160 * 160 * 20,
                                           rel=1e-6)


def test_gaine_refuse_une_epaisseur_impossible():
    with pytest.raises(ValueError):
        shell(box(100, 100, 100), 0)
    with pytest.raises(ValueError):
        shell(box(100, 100, 100), 200)
    with pytest.raises(ValueError):
        shell(box(100, 100, 100), 20, open_faces=[99])


def test_coupe_par_un_plan(cube):
    plan = Plane.from_point_normal((0, 0, 100), Z_AXIS)
    haut, bas = slice_solid(cube, plan)
    assert haut.volume == pytest.approx(4e6, rel=1e-6)
    assert bas.volume == pytest.approx(4e6, rel=1e-6)
    assert len(slice_solid(cube, plan, "positif")) == 1
    with pytest.raises(ValueError):
        slice_solid(cube, plan, "dessus")


def test_section_dun_cube_et_dun_cylindre(cube):
    plan = Plane.from_point_normal((0, 0, 100), Z_AXIS)
    boucles = section_loops(cube, plan)
    assert len(boucles) == 1
    assert boucles[0].length == pytest.approx(800.0, rel=1e-6)
    profil = section_profile(cylinder(100, 300, segments=64),
                             Plane.from_point_normal((0, 0, 150), Z_AXIS))
    assert profil.area == pytest.approx(math.pi * 10000, rel=1e-2)
    vue = section_plane_view(cube, plan)
    assert vue["contours"] == 1 and vue["aire_mm2"] == pytest.approx(40000)


def test_decalage_de_solide():
    assert offset_solid(box(100, 100, 100), 10).volume == pytest.approx(120 ** 3,
                                                                        rel=1e-6)
    assert offset_solid(box(100, 100, 100), -10).volume == pytest.approx(80 ** 3,
                                                                         rel=1e-6)


def test_depouille_reduit_la_matiere():
    incline = taper_faces(box(100, 100, 100),
                          Plane.from_point_normal((0, 0, 0), Z_AXIS), 10)
    assert incline.volume < 1e6
    assert incline.volume > 0.5e6


def test_empreinte_et_conversions(cube):
    marque = imprint(cube, box(50, 50, 300, (75, 75, -50)))
    assert marque.metadata["empreintes"] == 1
    surface = convert_to_surface(cube)
    assert surface.metadata["type"] == "surface"
    referme = convert_to_solid(surface)
    assert referme.volume == pytest.approx(cube.volume)


def test_extraction_du_filaire_et_fiche_des_faces(cube):
    assert len(extract_edges(cube)) == 12
    faces = face_report(cube)
    assert len(faces) == 6
    assert all(face["aire_mm2"] == pytest.approx(40000) for face in faces)
