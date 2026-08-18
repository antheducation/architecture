"""Interoperabilite : tous les formats de fichiers lus et ecrits."""
from __future__ import annotations

import math
import os
import struct
import tempfile

import pytest

import Interop
from CAD_Core.document import CadDocument
from CAD_Core.math3d import Vec3
from CAD_Core.primitives import box, cylinder
from CAD_Core.profiles import Curve, Profile
from Interop.dwg import DwgError, describe_backends, probe_dwg
from Interop.dxf import probe_dxf, read_dxf, write_dxf
from Interop.images import (Raster, read_bmp, read_image, read_png, read_ppm,
                            write_bmp, write_png, write_ppm, write_tga, underlay)
from Interop.meshes import (read_3mf, read_collada, read_gltf, read_obj,
                            read_off, read_ply, read_stl, write_3ds, write_3mf,
                            write_amf, write_collada, write_glb, write_gltf,
                            write_obj, write_off, write_ply, write_stl,
                            write_vrml, write_x3d)
from Interop.native import read_native, write_native
from Interop.pdf import PdfDocument, probe_pdf
from Interop.pointcloud import (PointCloud, probe_las, read_las, read_xyz,
                                write_csv, write_las, write_xyz)
from Interop.step import read_step, write_iges, write_step, probe_step
from Interop.svg import read_svg, write_svg


@pytest.fixture()
def document():
    doc = CadDocument("Essai")
    doc.add_layer("MURS", 1, "CONTINUOUS", 35)
    doc.set_current_layer("MURS")
    doc.add(box(1000, 500, 300))
    doc.add(cylinder(200, 600, (2000, 0, 0), segments=24))
    doc.add(Curve.polyline([(0, 0, 0), (1000, 0, 0), (1000, 1000, 0)], True))
    return doc


@pytest.fixture()
def solides():
    return [box(1000, 500, 300), cylinder(200, 600, (2000, 0, 0), segments=24)]


def test_registre_des_formats():
    capacites = Interop.capabilities()
    assert capacites["formats"] >= 25
    assert "dwg" in capacites["lecture"] and "dxf" in capacites["ecriture"]
    assert ".dwg" in capacites["extensions"] and ".step" in capacites["extensions"]
    assert Interop.spec_for("plan.dxf").key == "dxf"
    assert Interop.spec_for("stl").key == "stl"
    with pytest.raises(Interop.InteropError):
        Interop.spec_for("machin.xyzt")


@pytest.mark.parametrize("version", ["R12", "2000", "2018"])
def test_dxf_aller_retour(document, version):
    texte = write_dxf(document, version)
    fiche = probe_dxf(texte)
    assert fiche["entites"] > 0
    assert fiche["release"] == version or fiche["version"].startswith("AC")
    relu = read_dxf(texte)
    assert relu.statistics()["volume_total_mm3"] == pytest.approx(
        document.statistics()["volume_total_mm3"], rel=1e-6)
    assert "MURS" in relu.layers


def test_dxf_refuse_un_contenu_invalide():
    from Interop.dxf import DxfError
    with pytest.raises(DxfError):
        read_dxf("")
    with pytest.raises(DxfError):
        write_dxf(CadDocument(), "R99")


def test_identification_dwg_sans_convertisseur():
    entete = (b"AC1032" + b"\x00" * 7 + struct.pack("<I", 0) + b"\x00" * 8
              + struct.pack("<H", 30) + b"\x00" * 200)
    fiche = probe_dwg(entete)
    assert fiche["version"] == "AC1032"
    assert "2018" in fiche["release"]
    assert fiche["lisible_nativement"] is False
    assert "installation" in describe_backends()
    with pytest.raises(DwgError):
        probe_dwg(b"PASDWG" + b"\x00" * 200)
    with pytest.raises(DwgError):
        probe_dwg(b"AC1032")


@pytest.mark.parametrize("ecrire,lire,binaire", [
    (lambda s: write_stl(s, True), read_stl, True),
    (lambda s: write_stl(s, False), read_stl, True),
    (lambda s: write_obj(s), lambda d: read_obj(d), False),
    (lambda s: write_ply(s, False), read_ply, True),
    (lambda s: write_ply(s, True), read_ply, True),
    (lambda s: write_off(s), lambda d: read_off(d), False),
    (lambda s: write_gltf(s), lambda d: read_gltf(d), False),
    (lambda s: write_glb(s), read_gltf, True),
    (lambda s: write_3mf(s), read_3mf, True),
    (lambda s: write_collada(s), lambda d: read_collada(d), False),
])
def test_maillages_aller_retour(solides, ecrire, lire, binaire):
    attendu = sum(s.volume for s in solides)
    donnees = ecrire(solides)
    relus = lire(donnees)
    assert sum(s.volume for s in relus) == pytest.approx(attendu, rel=1e-3)


@pytest.mark.parametrize("ecrire", [write_amf, write_vrml, write_x3d, write_3ds])
def test_formats_en_ecriture_seule(solides, ecrire):
    donnees = ecrire(solides)
    assert len(donnees) > 100


def test_stl_tronque_est_signale():
    from Interop.meshes import MeshFormatError
    with pytest.raises(MeshFormatError):
        read_stl(b"court")
    with pytest.raises(MeshFormatError):
        read_stl(b"\x00" * 80 + struct.pack("<I", 1000) + b"\x00" * 20)


def test_step_aller_retour_et_iges(solides):
    for schema in ("AP203", "AP214", "AP242"):
        texte = write_step(solides, schema)
        fiche = probe_step(texte)
        assert fiche["norme"] == schema
        assert fiche["solides"] == 2
    relus = read_step(write_step(solides))
    assert sum(s.volume for s in relus) == pytest.approx(
        sum(s.volume for s in solides), rel=1e-6)
    assert len(write_iges(solides)) > 500


def test_step_courbe_donne_un_message_clair():
    from Interop.step import StepError
    with pytest.raises(StepError) as erreur:
        read_step("ISO-10303-21;\nDATA;\n#1=CYLINDRICAL_SURFACE('',#2,5.);\n"
                  "ENDSEC;")
    assert "facettis" in str(erreur.value)


def test_ifc_aller_retour(solides):
    from BIM_Engine.ifc_handler import IFCHandler
    texte = IFCHandler().export_solids(solides, "Maquette")
    assert "IFCFACETEDBREP" in texte and "IFC4" in texte
    relus = IFCHandler().read_solids(texte)
    assert sum(s.volume for s in relus) == pytest.approx(
        sum(s.volume for s in solides), rel=1e-6)


@pytest.mark.parametrize("ecrire,lire", [
    (write_png, read_png), (write_bmp, read_bmp), (write_ppm, read_ppm),
])
def test_images_aller_retour_exact(ecrire, lire):
    image = Raster(24, 16)
    for y in range(16):
        for x in range(24):
            image.set_pixel(x, y, (x * 10 % 256, y * 15 % 256, 128))
    relue = lire(ecrire(image))
    assert relue.width == 24 and relue.height == 16
    assert all(image.pixel(x, y) == relue.pixel(x, y)
               for y in range(16) for x in range(24))


def test_image_detection_et_calage():
    image = Raster(8, 4)
    assert read_image(write_png(image)).width == 8
    assert read_image(write_bmp(image)).height == 4
    assert len(write_tga(image)) > 18
    fiche = underlay(write_png(image), 4000)
    assert fiche["largeur_mm"] == 4000
    assert fiche["hauteur_mm"] == pytest.approx(2000.0)
    assert image.resized(4, 2).width == 4
    assert len(image.grayscale()) == 4


def test_pdf_multipage(document):
    pdf = PdfDocument("Planche")
    page = pdf.add_page("A3", True)
    page.line_width(0.5).rectangle((20, 20), 200, 150)
    page.circle((120, 95), 40)
    page.polyline([(20, 20), (220, 20), (220, 170)], True)
    page.dash([4, 2]).line((20, 95), (220, 95))
    page.text((30, 180), "PLAN RDC", 6)
    page.title_block("Residence", "A3-01", "1:100", "2026-01-01")
    pdf.add_page("A4", False).text((20, 270), "Note", 5)
    donnees = pdf.build()
    fiche = probe_pdf(donnees)
    assert fiche["pages"] == 2 and fiche["compresse"]
    assert donnees.startswith(b"%PDF-") and donnees.rstrip().endswith(b"%%EOF")
    from Interop.pdf import PdfError
    with pytest.raises(PdfError):
        PdfDocument().build()
    with pytest.raises(PdfError):
        pdf.add_page("A9")


def test_svg_export_et_import(document):
    texte = write_svg(document)
    assert texte.startswith("<svg") and "<line" in texte
    relu = read_svg(texte)
    assert len(relu.entities) > 0
    chemins = read_svg('<svg xmlns="http://www.w3.org/2000/svg" width="100" '
                       'height="100"><path d="M10,10 L90,10 L90,90 Z"/>'
                       '<path d="M10,50 C30,20 70,20 90,50"/>'
                       '<rect x="5" y="5" width="20" height="20"/>'
                       '<circle cx="50" cy="50" r="20"/></svg>')
    assert len(chemins.entities) == 4


def test_nuages_de_points():
    points = [Vec3(x * 100.0, y * 100.0, 500 + 200 * math.sin(x / 5.0))
              for x in range(20) for y in range(20)]
    nuage = PointCloud(points, [(120, 90, 60)] * len(points),
                       [1000.0] * len(points), "releve")
    assert nuage.statistics()["points"] == 400
    relu = read_xyz(write_xyz(nuage))
    assert len(relu) == 400 and relu.colors
    assert len(read_xyz(write_csv(nuage))) == 400
    donnees = write_las(nuage)
    assert probe_las(donnees)["points"] == 400
    depuis_las = read_las(donnees)
    assert len(depuis_las) == 400
    assert max(a.distance_to(b) for a, b in zip(nuage.points,
                                                depuis_las.points)) < 0.01
    terrain = nuage.to_terrain(20)
    assert terrain.area > 0
    assert len(nuage.decimated(10)) == 40


def test_format_natif_sans_perte(document):
    document.define_block("PLOT", [list(document.entities)[0]])
    document.set_ucs("CHANTIER", (10, 20, 30))
    document.add_layout("PLANCHE", "A1", 0.02)
    avant = document.statistics()
    relu = read_native(write_native(document))
    apres = relu.statistics()
    for cle in ("objets", "par_type", "calques", "blocs", "presentations"):
        assert avant[cle] == apres[cle]
    assert apres["volume_total_mm3"] == pytest.approx(avant["volume_total_mm3"],
                                                      rel=1e-9)
    assert relu.layers["MURS"].lineweight == 35
    assert relu.ucs_table["CHANTIER"].origin.rounded(3) == (10.0, 20.0, 30.0)


def test_format_natif_refuse_un_autre_json():
    from Interop.native import NativeFormatError
    with pytest.raises(NativeFormatError):
        read_native('{"format": "AUTRE"}')
    with pytest.raises(NativeFormatError):
        read_native("pas du json")


def test_identification_par_signature(document, solides):
    echantillons = {
        "dxf": write_dxf(document).encode(), "stl": write_stl(solides),
        "png": write_png(Raster(4, 4)), "glb": write_glb(solides),
        "step": write_step(solides).encode(), "las": write_las(
            PointCloud([Vec3(0, 0, 0), Vec3(1, 1, 1)])),
        "3mf": write_3mf(solides), "json": write_native(document).encode(),
        "svg": write_svg(document).encode(),
    }
    for attendu, donnees in echantillons.items():
        assert Interop.identify(donnees, "essai." + attendu)["format"] == attendu
    with pytest.raises(Interop.InteropError):
        Interop.identify(b"\x01\x02\x03\x04", "inconnu.zzz")


def test_ifc_et_step_ne_sont_pas_confondus(solides):
    from BIM_Engine.ifc_handler import IFCHandler
    ifc = IFCHandler().export_solids(solides, "M").encode()
    assert Interop.identify(ifc, "m.ifc")["format"] == "ifc"
    assert Interop.identify(write_step(solides).encode(), "m.step")["format"] \
        == "step"


def test_export_et_import_par_fichier(document):
    dossier = tempfile.mkdtemp(prefix="mercury_interop_")
    for cle in ("dxf", "stl", "obj", "ply", "step", "gltf", "glb", "3mf", "off",
                "json", "svg", "ifc", "pdf", "png", "xyz", "csv", "las", "dae",
                "amf", "wrl", "x3d", "3ds", "iges", "bmp", "ppm", "tga", "mtl"):
        spec = Interop.BY_KEY[cle]
        chemin = os.path.join(dossier, "sortie" + spec.extensions[0])
        Interop.export_file(document, chemin)
        assert os.path.getsize(chemin) > 0
        if spec.read:
            resultat = Interop.import_file(chemin)
            assert resultat["document"] is not None


def test_conversion_entre_formats(document):
    dossier = tempfile.mkdtemp(prefix="mercury_conv_")
    source = os.path.join(dossier, "source.dxf")
    Interop.export_file(document, source)
    rapport = Interop.convert(source, os.path.join(dossier, "cible.stl"))
    assert rapport["format_source"] == "dxf" and rapport["format_cible"] == "stl"
    assert rapport["objets"] > 0


def test_import_dwg_sans_moteur_donne_un_message_utile(document):
    dossier = tempfile.mkdtemp(prefix="mercury_dwg_")
    chemin = os.path.join(dossier, "essai.dwg")
    with open(chemin, "wb") as handle:
        handle.write(b"AC1032" + b"\x00" * 500)
    if describe_backends()["lecture_dwg"]:
        pytest.skip("un moteur de conversion DWG est installe sur cette machine")
    with pytest.raises(DwgError) as erreur:
        Interop.import_file(chemin)
    assert "moteur" in str(erreur.value).lower()
