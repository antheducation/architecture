"""Document CAO, accrochages, annotation, vues et rendu."""
from __future__ import annotations

import math

import pytest

from CAD_Core.annotate import (angular_dimension, arc_length_dimension,
                               baseline_dimensions, continuous_dimensions,
                               dimension_from_solid, hatch, hatch_lines, leader,
                               linear_dimension, mtext, ordinate_dimension,
                               radial_dimension, revision_cloud, table)
from CAD_Core.document import CadDocument, Layer
from CAD_Core.math3d import BBox3, Plane, Vec3, Z_AXIS
from CAD_Core.primitives import box, cylinder
from CAD_Core.profiles import Curve, Profile
from CAD_Core.render_engine import Framebuffer, Renderer3D, render_thumbnail
from CAD_Core.snapping import OSNAP_MODES, SnapEngine
from CAD_Core.view3d import Camera, STANDARD_VIEWS, VISUAL_STYLES, Viewport


@pytest.fixture()
def document():
    doc = CadDocument("Essai")
    doc.add_layer("MURS", 1, "CONTINUOUS", 35)
    doc.set_current_layer("MURS")
    doc.add(box(1000, 200, 2500))
    doc.add(cylinder(150, 3000, (2000, 0, 0), segments=24))
    return doc


def test_calques(document):
    assert document.current_layer == "MURS"
    assert document.layers["MURS"].color == 1
    assert len(document.layer_entities("MURS")) == 2
    assert not document.delete_layer("0")
    with pytest.raises(ValueError):
        document.delete_layer("MURS")
    with pytest.raises(ValueError):
        document.add_layer("X", linetype="POINTILLE")


def test_unites_invalides():
    with pytest.raises(ValueError):
        CadDocument("X", "lieues")


def test_annuler_retablir(document):
    depart = len(document.entities)
    document.snapshot()
    document.remove(list(document.entities)[0])
    assert len(document.entities) == depart - 1
    assert document.undo()
    assert len(document.entities) == depart
    assert document.redo()
    assert len(document.entities) == depart - 1
    document.undo()


def test_blocs(document):
    handle = list(document.entities)[0]
    bloc = document.define_block("POTEAU", [handle], (0, 0, 0))
    assert bloc.name == "POTEAU"
    place = document.insert_block("POTEAU", (5000, 0, 0))
    assert len(place) == 1
    assert round(place[0].geometry.centroid.x) == 5500
    assert document.explode_block([place[0].handle]) == 1
    with pytest.raises(ValueError):
        document.insert_block("INCONNU")
    with pytest.raises(ValueError):
        document.define_block("VIDE", [])


def test_selection(document):
    assert len(document.select_all()) == 2
    assert len(document.select_window((-10, -10, -10), (1500, 1500, 3000))) == 1
    assert len(document.select_window((-10, -10, -10), (1500, 1500, 3000),
                                      crossing=True)) >= 1
    assert len(document.select_by_layer("MURS")) == 2
    assert len(document.selected_entities()) == 2


def test_scu_presentations_et_vues(document):
    scu = document.set_ucs("CHANTIER", (100, 200, 0))
    assert scu.z_axis.rounded(6) == (0.0, 0.0, 1.0)
    assert scu.to_local(scu.to_world((5, 5, 5))).rounded(6) == (5.0, 5.0, 5.0)
    assert document.add_layout("PLAN", "A1", 0.02).width_mm == 841.0
    with pytest.raises(ValueError):
        document.add_layout("X", "A9")
    document.save_view("ISO", {"azimut_deg": 315})
    assert "ISO" in document.named_views


def test_statistiques_et_fusion(document):
    fiche = document.statistics()
    assert fiche["objets"] == 2
    assert fiche["volume_total_mm3"] > 0
    autre = CadDocument("Autre")
    autre.add(box(100, 100, 100))
    assert document.merge(autre, "EXT_") == 1
    assert len(document.entities) == 3


def test_accrochages():
    moteur = SnapEngine(aperture=60, modes=sum(OSNAP_MODES.values()))
    cube = box(1000, 1000, 1000)
    assert moteur.snap((5, 5, 5), [cube]).mode == "extremite"
    assert moteur.snap((500, 4, 0), [cube]).mode == "milieu"
    assert moteur.snap((510, 510, 1000), [cube]).mode == "centre"
    assert moteur.snap((9000, 9000, 9000), [cube]) is None
    moteur.ortho = True
    accroche = moteur.snap((1005, 30, 0), [cube], last_point=(1000, 0, 0))
    assert accroche.point.rounded(3) == (1000.0, 0.0, 0.0)
    moteur.ortho = False
    moteur.grid_snap = True
    moteur.grid_spacing = 250
    assert moteur.snap((5300, 5100, 0), [cube]).mode == "resolution"
    assert moteur.polar_track((0, 0, 0), (100, 30, 0)).rounded(3)[1] == 0.0
    croisements = moteur.intersections(
        [Curve.line((0, 0, 0), (100, 0, 0)), Curve.line((50, -50, 0),
                                                        (50, 50, 0))],
        (50, 0, 0))
    assert croisements[0].rounded(3) == (50.0, 0.0, 0.0)
    assert "extremite" in moteur.to_dict()["modes_actifs"]


def test_cotations():
    lineaire = linear_dimension((0, 0, 0), (3000, 0, 0))
    assert lineaire["mesure_mm"] == 3000.0 and lineaire["texte"] == "3000"
    assert angular_dimension((0, 0, 0), (100, 0, 0),
                             (0, 100, 0))["mesure_deg"] == pytest.approx(90.0)
    assert radial_dimension((0, 0, 0), 250, diameter=True)["texte"] == "Ø500"
    assert arc_length_dimension((0, 0, 0), 100, 0, 90)["mesure_mm"] == \
        pytest.approx(math.pi * 50, rel=1e-6)
    assert ordinate_dimension((1250, 0, 0))["mesure_mm"] == 1250.0
    assert len(continuous_dimensions([(0, 0, 0), (1000, 0, 0), (2500, 0, 0)])) == 2
    assert len(baseline_dimensions([(0, 0, 0), (1000, 0, 0), (2500, 0, 0)])) == 2
    assert dimension_from_solid(box(1200, 800, 300), "y")["texte"] == "800"
    with pytest.raises(ValueError):
        angular_dimension((0, 0, 0), (0, 0, 0), (1, 0, 0))
    with pytest.raises(ValueError):
        continuous_dimensions([(0, 0, 0)])


def test_hachures_texte_tableau_et_nuage():
    profil = Profile.rectangle(1000, 600).with_hole(
        Profile.rectangle(200, 200, (400, 200, 0)).outline)
    remplissage = hatch(profil, "ANSI31", 10)
    assert remplissage["aire_mm2"] == pytest.approx(560000)
    assert len(remplissage["lignes"]) > 5
    assert len(hatch_lines(profil, "AR-CONC", 4)) > 0
    with pytest.raises(ValueError):
        hatch(profil, "MOTIF_INCONNU")
    assert mtext((0, 0, 0), "ligne1\nligne2")["lignes"] == ["ligne1", "ligne2"]
    assert leader([(0, 0, 0), (100, 100, 0)], "Poteau")["texte"] == "Poteau"
    with pytest.raises(ValueError):
        leader([(0, 0, 0)], "x")
    tableau = table((0, 0, 0), [["Lot", "Qte"], ["Beton", "12"]], title="METRE")
    assert tableau["colonnes"] == 2
    assert len(revision_cloud([(0, 0, 0), (900, 0, 0), (900, 900, 0)])["points"]) > 6
    with pytest.raises(ValueError):
        revision_cloud([(0, 0, 0)])


def test_camera_et_projection():
    camera = Camera(width=800, height=600)
    camera.zoom_extents(BBox3.of([(0, 0, 0), (5000, 4000, 3000)]))
    x, y, _ = camera.project((2500, 2000, 1500))
    assert x == pytest.approx(400.0, abs=1.0)
    assert y == pytest.approx(300.0, abs=1.0)
    camera.set_standard_view("dessus")
    assert camera.elevation_deg > 80
    camera.set_standard_view("face")
    assert camera.position.y < 0
    with pytest.raises(ValueError):
        camera.set_standard_view("dedans")
    camera.orbit(45, 10)
    camera.pan(100, 50)
    camera.dolly(2.0)
    with pytest.raises(ValueError):
        camera.dolly(0)
    assert Camera.from_dict(camera.to_dict()).width == camera.width
    assert len(camera.add_clip_plane(
        Plane.from_point_normal((0, 0, 0), Z_AXIS)).clip_planes) == 1


def test_styles_visuels():
    fenetre = Viewport()
    assert fenetre.set_style("realiste").visual_style == "realiste"
    with pytest.raises(ValueError):
        fenetre.set_style("aquarelle")
    assert set(VISUAL_STYLES) >= {"filaire_2d", "realiste", "conceptuel"}
    assert "iso_sud_ouest" in STANDARD_VIEWS


@pytest.mark.parametrize("style", sorted(VISUAL_STYLES))
def test_rendu_de_chaque_style(style):
    solides = [box(2000, 1500, 800), cylinder(300, 2500, (2600, 700, 0),
                                              segments=16)]
    camera = Camera(width=160, height=120)
    boite = BBox3()
    for solide in solides:
        boite.add(solide.bbox.min).add(solide.bbox.max)
    camera.zoom_extents(boite)
    image = Renderer3D().render(solides, camera, style)
    png = image.to_png()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png) > 100


def test_rendu_refuse_un_style_inconnu():
    with pytest.raises(ValueError):
        Renderer3D().render([box(10, 10, 10)], Camera(width=64, height=64),
                            "gouache")


def test_lignes_cachees_et_vignette():
    solides = [box(1000, 1000, 1000)]
    camera = Camera(width=200, height=150)
    camera.zoom_extents(solides[0].bbox)
    svg = Renderer3D().hidden_line_svg(solides, camera)
    assert svg.startswith("<svg") and "polyline" in svg
    assert Renderer3D().wireframe_svg(solides, camera).count("<line") == 12
    assert render_thumbnail(solides, 120, 90)[:4] == b"\x89PNG"


def test_tampon_image():
    tampon = Framebuffer(4, 3, (10, 20, 30))
    assert tampon.get(0, 0) == (10, 20, 30)
    tampon.set(1, 1, (200, 100, 50), 0.0)
    assert tampon.get(1, 1) == (200, 100, 50)
    tampon.set(1, 1, (0, 0, 0), 5.0)             # plus loin : ignore
    assert tampon.get(1, 1) == (200, 100, 50)
    tampon.blend(2, 2, (255, 255, 255), 1.0)
    assert tampon.get(2, 2) == (255, 255, 255)
    assert tampon.to_ppm().startswith(b"P6")
    with pytest.raises(ValueError):
        Framebuffer(0, 10)
