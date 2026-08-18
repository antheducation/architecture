"""Couche d'interoperabilite : un registre unique pour tous les formats.

Point d'entree du module :

    from Interop import import_file, export_file, formats, identify

`formats()` decrit ce que MERCURY sait lire et ecrire, `identify()` reconnait
un fichier a sa signature, `import_file()` et `export_file()` font le travail.
Le registre est aussi la source de la matrice de compatibilite affichee dans
l'interface et publiee par l'API.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from CAD_Core.document import CadDocument
from CAD_Core.profiles import Curve, Profile
from CAD_Core.solid import Solid

from . import dwg as dwg_module
from . import dxf as dxf_module
from . import images as image_module
from . import meshes as mesh_module
from . import pdf as pdf_module
from . import pointcloud as cloud_module
from . import native as native_module
from . import step as step_module
from . import svg as svg_module

VERSION = "1.0.0"


class InteropError(ValueError):
    """Format inconnu, ou operation impossible sur ce format."""


@dataclass
class FormatSpec:
    """Fiche d'un format : extensions, capacites, categorie, remarques."""

    key: str
    label: str
    extensions: Tuple[str, ...]
    category: str
    read: bool = False
    write: bool = False
    kind: str = "3d"                      # 3d, 2d, image, nuage, document
    binary: bool = False
    note: str = ""
    requires: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"cle": self.key, "libelle": self.label,
                "extensions": list(self.extensions), "categorie": self.category,
                "lecture": self.read, "ecriture": self.write, "nature": self.kind,
                "binaire": self.binary, "remarque": self.note,
                "prerequis": self.requires}


FORMATS: List[FormatSpec] = [
    FormatSpec("dwg", "AutoCAD DWG", (".dwg",), "CAO", True, True, "2d", True,
               "Identification, version et apercu en natif ; la geometrie "
               "passe par un moteur de conversion installe sur la machine.",
               "ODA File Converter, LibreDWG ou ezdxf[odafc]"),
    FormatSpec("dxf", "AutoCAD DXF (R12 a 2021)", (".dxf",), "CAO", True, True,
               "2d", False, "Lecture et ecriture natives, toutes versions."),
    FormatSpec("ifc", "IFC 4 (BIM)", (".ifc",), "BIM", True, True, "3d", False,
               "Echange BIM normalise ISO 16739."),
    FormatSpec("step", "STEP AP203/AP214/AP242", (".step", ".stp"), "Mecanique",
               True, True, "3d", False, "BREP facettise, lu par tous les CAO."),
    FormatSpec("iges", "IGES 5.3", (".iges", ".igs"), "Mecanique", False, True,
               "3d", False, "Surfaces planes, entite 106."),
    FormatSpec("stl", "STL", (".stl",), "Impression 3D", True, True, "3d", True,
               "ASCII et binaire, detection automatique."),
    FormatSpec("obj", "Wavefront OBJ", (".obj",), "3D", True, True, "3d", False,
               "Materiaux exportes dans un fichier .mtl associe."),
    FormatSpec("mtl", "Bibliotheque de materiaux OBJ", (".mtl",), "3D", False,
               True, "3d", False),
    FormatSpec("ply", "Stanford PLY", (".ply",), "3D", True, True, "3d", True,
               "ASCII et binaire."),
    FormatSpec("off", "Object File Format", (".off",), "3D", True, True, "3d"),
    FormatSpec("gltf", "glTF 2.0", (".gltf",), "3D web", True, True, "3d"),
    FormatSpec("glb", "glTF binaire", (".glb",), "3D web", True, True, "3d",
               True),
    FormatSpec("3mf", "3D Manufacturing Format", (".3mf",), "Impression 3D",
               True, True, "3d", True),
    FormatSpec("amf", "Additive Manufacturing Format", (".amf",),
               "Impression 3D", False, True, "3d"),
    FormatSpec("dae", "COLLADA", (".dae",), "3D", True, True, "3d"),
    FormatSpec("wrl", "VRML 2.0", (".wrl", ".vrml"), "3D", False, True, "3d"),
    FormatSpec("x3d", "X3D", (".x3d",), "3D", False, True, "3d"),
    FormatSpec("3ds", "Autodesk 3D Studio", (".3ds",), "3D", False, True, "3d",
               True, "Limite du format : 65 535 sommets par objet."),
    FormatSpec("svg", "SVG", (".svg",), "Vectoriel", True, True, "2d", False,
               "Export de plans et import de traces."),
    FormatSpec("pdf", "PDF vectoriel", (".pdf",), "Document", False, True,
               "document", True, "Planches multipages avec cartouche."),
    FormatSpec("png", "PNG", (".png",), "Image", True, True, "image", True),
    FormatSpec("bmp", "Windows Bitmap", (".bmp",), "Image", True, True, "image",
               True),
    FormatSpec("ppm", "Portable Pixmap", (".ppm",), "Image", True, True,
               "image", True),
    FormatSpec("tga", "Targa", (".tga",), "Image", False, True, "image", True),
    FormatSpec("jpg", "JPEG", (".jpg", ".jpeg"), "Image", True, True, "image",
               True, "Lecture et ecriture via Pillow.", "Pillow"),
    FormatSpec("xyz", "Nuage de points XYZ / PTS", (".xyz", ".pts", ".asc"),
               "Releve", True, True, "nuage"),
    FormatSpec("csv", "Points CSV", (".csv",), "Releve", True, True, "nuage"),
    FormatSpec("las", "LiDAR LAS", (".las",), "Releve", True, True, "nuage",
               True, "LAS 1.0 a 1.4, formats de point 0 a 5."),
    FormatSpec("json", "Modele MERCURY (JSON)", (".json",), "Natif", True, True,
               "3d", False, "Format natif : tout le document, sans perte."),
]

BY_KEY: Dict[str, FormatSpec] = {spec.key: spec for spec in FORMATS}
BY_EXTENSION: Dict[str, FormatSpec] = {}
for _spec in FORMATS:
    for _extension in _spec.extensions:
        BY_EXTENSION[_extension] = _spec

SIGNATURES: List[Tuple[bytes, str]] = [
    (b"AC10", "dwg"), (b"\x89PNG\r\n\x1a\n", "png"), (b"BM", "bmp"),
    (b"P6", "ppm"), (b"%PDF-", "pdf"), (b"glTF", "glb"), (b"LASF", "las"),
    (b"PK\x03\x04", "3mf"), (b"ISO-10303-21", "step"), (b"solid", "stl"),
    (b"ply", "ply"), (b"OFF", "off"), (b"\xff\xd8\xff", "jpg"),
    (b"#VRML", "wrl"),
]


def formats(kind: Optional[str] = None,
            capability: Optional[str] = None) -> List[Dict[str, Any]]:
    """Matrice des formats. `capability` vaut « lecture » ou « ecriture »."""
    out = []
    for spec in FORMATS:
        if kind and spec.kind != kind:
            continue
        if capability == "lecture" and not spec.read:
            continue
        if capability == "ecriture" and not spec.write:
            continue
        out.append(spec.to_dict())
    return out


def capabilities() -> Dict[str, Any]:
    """Resume publiable : ce que le logiciel sait faire, format par format."""
    return {
        "version": VERSION,
        "formats": len(FORMATS),
        "lecture": sorted(s.key for s in FORMATS if s.read),
        "ecriture": sorted(s.key for s in FORMATS if s.write),
        "extensions": sorted(BY_EXTENSION),
        "categories": sorted({s.category for s in FORMATS}),
        "dwg": dwg_module.describe_backends(),
        "detail": [s.to_dict() for s in FORMATS],
    }


def spec_for(path_or_key: str) -> FormatSpec:
    """Retrouve la fiche d'un format par sa cle ou par l'extension d'un chemin."""
    key = (path_or_key or "").lower().strip()
    if key in BY_KEY:
        return BY_KEY[key]
    extension = os.path.splitext(key)[1]
    if extension in BY_EXTENSION:
        return BY_EXTENSION[extension]
    if "." + key in BY_EXTENSION:
        return BY_EXTENSION["." + key]
    raise InteropError(
        "format inconnu : %r. Formats acceptes : %s"
        % (path_or_key, ", ".join(sorted(BY_KEY))))


def identify(data: bytes, filename: str = "") -> Dict[str, Any]:
    """Reconnait un fichier par sa signature, l'extension servant d'appoint."""
    head = data[:64] if isinstance(data, bytes) else b""
    detected: Optional[str] = None
    for signature, key in SIGNATURES:
        if head.startswith(signature):
            detected = key
            break
    if detected == "step":
        # IFC et STEP partagent l'enveloppe ISO 10303 : c'est le schema
        # declare dans l'en-tete qui les distingue.
        head_text = data[:4096].decode("utf-8", "replace").upper()
        if "IFC" in head_text and "FILE_SCHEMA" in head_text:
            detected = "ifc"
    if detected is None and head[:5].lower() == b"<?xml":
        lowered = data[:4096].lower()
        if b"<svg" in lowered:
            detected = "svg"
        elif b"collada" in lowered:
            detected = "dae"
        elif b"<amf" in lowered:
            detected = "amf"
        elif b"x3d" in lowered:
            detected = "x3d"
    if detected is None and head.lstrip()[:1] in (b"{", b"["):
        detected = "gltf" if b'"asset"' in data[:512] else "json"
    if detected is None:
        text = data[:4096].decode("utf-8", "replace")
        if "SECTION" in text and "\n  2\n" in text.replace("\r", ""):
            detected = "dxf"
        elif text.lstrip().startswith("999") or "\n0\nSECTION" in text:
            detected = "dxf"
    if detected is None and filename:
        extension = os.path.splitext(filename)[1].lower()
        if extension in BY_EXTENSION:
            detected = BY_EXTENSION[extension].key
    if detected is None:
        raise InteropError(
            "format non reconnu%s. Extensions acceptees : %s"
            % (" pour %s" % filename if filename else "",
               ", ".join(sorted(BY_EXTENSION))))
    spec = BY_KEY[detected]
    report: Dict[str, Any] = {"format": spec.key, "libelle": spec.label,
                              "categorie": spec.category, "nature": spec.kind,
                              "taille_octets": len(data)}
    probe: Dict[str, Any] = {}
    try:
        if spec.key == "dwg":
            probe = dwg_module.probe_dwg(data)
        elif spec.key == "dxf":
            probe = dxf_module.probe_dxf(data.decode("utf-8", "replace"))
        elif spec.key == "step":
            probe = step_module.probe_step(data.decode("utf-8", "replace"))
        elif spec.key == "pdf":
            probe = pdf_module.probe_pdf(data)
        elif spec.key == "las":
            probe = cloud_module.probe_las(data)
    except Exception as error:                # identification au mieux
        report["avertissement"] = str(error)
    # La sonde detaille le fichier mais ne redefinit pas la cle du registre :
    # c'est elle qui pilote l'aiguillage des imports.
    probe.pop("format", None)
    report.update(probe)
    return report


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------
def import_data(data, filename: str = "", format_key: Optional[str] = None,
                name: Optional[str] = None) -> Dict[str, Any]:
    """Importe un contenu et renvoie document, solides et nuage eventuels."""
    if isinstance(data, str):
        raw = data.encode("utf-8")
    else:
        raw = bytes(data)
    key = (spec_for(format_key).key if format_key
           else identify(raw, filename)["format"])
    spec = BY_KEY[key]
    if not spec.read:
        raise InteropError("le format %s est ecrit mais pas lu par MERCURY"
                           % spec.label)
    label = name or (os.path.splitext(os.path.basename(filename))[0]
                     if filename else key)
    text = raw.decode("utf-8", "replace")

    document: Optional[CadDocument] = None
    solids: List[Solid] = []
    cloud = None

    if key == "dxf":
        document = dxf_module.read_dxf(text, label)
    elif key == "svg":
        document = svg_module.read_svg(text, name=label)
    elif key == "ifc":
        from BIM_Engine.ifc_handler import IFCHandler
        solids = _ifc_solids(text, label)
    elif key == "step":
        solids = step_module.read_step(text, label)
    elif key == "stl":
        solids = mesh_module.read_stl(raw, label)
    elif key == "obj":
        solids = mesh_module.read_obj(text, name=label)
    elif key == "ply":
        solids = mesh_module.read_ply(raw, label)
    elif key == "off":
        solids = mesh_module.read_off(text, label)
    elif key in ("gltf", "glb"):
        solids = mesh_module.read_gltf(raw, name=label)
    elif key == "3mf":
        solids = mesh_module.read_3mf(raw, label)
    elif key == "dae":
        solids = mesh_module.read_collada(text, name=label)
    elif key in ("xyz", "csv"):
        cloud = cloud_module.read_xyz(text, name=label)
    elif key == "las":
        cloud = cloud_module.read_las(raw, label)
    elif key in ("png", "bmp", "ppm", "jpg"):
        raster = image_module.read_image(raw)
        document = CadDocument(label)
        document.add_layer("IMAGE", 8)
        attachment = image_module.underlay(raw, float(
            options_width(raster.width)))
        document.add(attachment, kind="annotation", layer="IMAGE",
                     name="image_" + label)
        return {"format": key, "nom": label, "image": raster.to_dict(),
                "raster": raster, "document": document, "solides": [],
                "nuage": None, "statistiques": document.statistics()}
    elif key == "json":
        document = native_module.read_native(text, label)
        return {"format": key, "nom": label, "document": document,
                "solides": document.solids(), "nuage": None,
                "statistiques": document.statistics()}
    elif key == "dwg":
        raise InteropError(
            "un DWG doit etre importe depuis un fichier (import_file) : la "
            "conversion appelle un moteur externe.\n"
            + dwg_module.describe_backends()["installation"])
    else:
        raise InteropError("import non implemente pour %s" % spec.label)

    if document is None:
        document = CadDocument(label)
        for solid in solids:
            document.add(solid)
    else:
        solids = document.solids()
    if cloud is not None:
        document.add_layer("RELEVE", 3)
        document.add({"type": "nuage_points", "points": [list(p)
                                                         for p in cloud.points],
                      "statistiques": cloud.statistiques()
                      if hasattr(cloud, "statistiques") else cloud.statistics()},
                     kind="annotation", layer="RELEVE",
                     name="nuage_" + label)
        document.variables["points_importes"] = len(cloud)
    return {"format": key, "nom": label, "document": document,
            "solides": solids, "nuage": cloud,
            "statistiques": document.statistics()}


def options_width(pixels: int, dots_per_mm: float = 4.0) -> float:
    """Largeur reelle par defaut d'une image importee, en millimetres.

    Faute d'echelle connue, une resolution de 4 points par millimetre (une
    centaine de points par pouce) donne un calage plausible ; l'utilisateur
    ajuste ensuite avec la commande ECHELLE.
    """
    return max(1.0, pixels / max(0.1, dots_per_mm))


def _ifc_solids(text: str, label: str) -> List[Solid]:
    """Extrait les volumes d'un IFC : parallelepipedes et extrusions simples."""
    from BIM_Engine.ifc_handler import IFCHandler
    return IFCHandler().read_solids(text, label)


def import_file(path: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Importe un fichier du disque, DWG compris."""
    if not os.path.isfile(path):
        raise InteropError("fichier introuvable : %s" % path)
    extension = os.path.splitext(path)[1].lower()
    if extension == ".dwg":
        document = dwg_module.read_dwg(path, name)
        return {"format": "dwg", "nom": name or os.path.basename(path),
                "document": document, "solides": document.solids(),
                "nuage": None, "statistiques": document.statistics(),
                "identification": dwg_module.inspect(path)}
    with open(path, "rb") as handle:
        return import_data(handle.read(), path, name=name)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export_data(document: CadDocument, format_key: str,
                annotations: Optional[Sequence[Dict[str, Any]]] = None,
                **options):
    """Exporte un document. Renvoie du texte ou des octets selon le format."""
    spec = spec_for(format_key)
    if not spec.write:
        raise InteropError("le format %s est lu mais pas ecrit par MERCURY"
                           % spec.label)
    key = spec.key
    solids = document.solids()
    if key == "dxf":
        return dxf_module.write_dxf(document, options.get("version", "2018"),
                                    annotations)
    if key == "svg":
        return svg_module.write_svg(document, options.get("largeur", 1600),
                                    annotations=annotations,
                                    plane=options.get("plan", "xy"))
    if key == "ifc":
        from BIM_Engine.ifc_handler import IFCHandler
        return IFCHandler().export_solids(solids, document.name)
    if key == "step":
        return step_module.write_step(solids, options.get("schema", "AP214"),
                                      document.name)
    if key == "iges":
        return step_module.write_iges(solids, product=document.name)
    if key == "stl":
        return mesh_module.write_stl(solids, options.get("binaire", True),
                                     document.name)
    if key == "obj":
        return mesh_module.write_obj(solids)
    if key == "mtl":
        return mesh_module.write_mtl()
    if key == "ply":
        return mesh_module.write_ply(solids, options.get("binaire", False))
    if key == "off":
        return mesh_module.write_off(solids)
    if key == "gltf":
        return mesh_module.write_gltf(solids)
    if key == "glb":
        return mesh_module.write_glb(solids)
    if key == "3mf":
        return mesh_module.write_3mf(solids)
    if key == "amf":
        return mesh_module.write_amf(solids)
    if key == "dae":
        return mesh_module.write_collada(solids)
    if key == "wrl":
        return mesh_module.write_vrml(solids)
    if key == "x3d":
        return mesh_module.write_x3d(solids)
    if key == "3ds":
        return mesh_module.write_3ds(solids)
    if key == "pdf":
        return _export_pdf(document, annotations, **options)
    if key in ("png", "bmp", "ppm", "tga", "jpg"):
        return _export_image(document, key, **options)
    if key in ("xyz", "csv", "las"):
        return _export_points(document, key, **options)
    if key == "json":
        return native_module.write_native(document)
    raise InteropError("export non implemente pour %s" % spec.label)


def _export_pdf(document: CadDocument,
                annotations: Optional[Sequence[Dict[str, Any]]] = None,
                **options) -> bytes:
    """Planche PDF : projection du modele, cartouche, cotes."""
    from CAD_Core.math3d import Vec3
    paper = options.get("format", "A3")
    scale = float(options.get("echelle", 0.0))
    pdf = pdf_module.PdfDocument(document.name)
    page = pdf.add_page(paper, options.get("paysage", True))
    box = document.bbox
    width_mm = page.width / pdf_module.MM_TO_PT
    height_mm = page.height / pdf_module.MM_TO_PT
    if box.valid:
        if scale <= 0:
            scale = min((width_mm - 60.0) / max(1.0, box.size.x),
                        (height_mm - 70.0) / max(1.0, box.size.y))
        offset_x = 20.0 - box.min.x * scale
        offset_y = 55.0 - box.min.y * scale
    else:
        scale, offset_x, offset_y = 1.0, 20.0, 20.0

    def place(point) -> Tuple[float, float]:
        p = Vec3.of(point)
        return (offset_x + p.x * scale, offset_y + p.y * scale)

    page.line_width(0.25).stroke_color(0.1, 0.12, 0.15)
    for entity in document.visible_entities():
        geometry = entity.geometry
        if isinstance(geometry, Solid):
            for a, b in geometry.edges():
                page.line(place(a), place(b))
        elif isinstance(geometry, Curve):
            page.polyline([place(p) for p in geometry.points], geometry.closed)
        elif isinstance(geometry, Profile):
            for ring in geometry.rings():
                page.polyline([place(p) for p in ring], True)
    page.stroke_color(0.75, 0.15, 0.12).line_width(0.2)
    for annotation in annotations or []:
        points = annotation.get("points", [])
        if annotation.get("type", "").startswith("cotation") and len(points) >= 4:
            page.line(place(points[2]), place(points[3]))
            middle = ((Vec3.of(points[2]) + Vec3.of(points[3])) * 0.5)
            x, y = place(middle)
            page.fill_color(0.75, 0.15, 0.12).text((x, y + 1.5),
                                                   annotation.get("texte", ""), 2.5)
        elif annotation.get("type") == "texte":
            x, y = place(annotation.get("position", (0, 0, 0)))
            page.fill_color(0.1, 0.12, 0.15).text((x, y),
                                                  annotation.get("texte", ""), 3.5)
    denominator = int(round(1.0 / scale)) if scale > 0 else 1
    page.title_block(document.name, options.get("planche", "Plan general"),
                     "1:%d" % max(1, denominator),
                     options.get("date", ""))
    return pdf.build()


def _export_image(document: CadDocument, key: str, **options) -> bytes:
    from CAD_Core.render_engine import Renderer3D
    from CAD_Core.view3d import Camera
    camera = Camera(width=int(options.get("largeur", 1280)),
                    height=int(options.get("hauteur", 800)))
    camera.zoom_extents(document.bbox)
    if "vue" in options:
        camera.set_standard_view(options["vue"])
        camera.zoom_extents(document.bbox)
    frame = Renderer3D().render(document.solids(), camera,
                                options.get("style", "ombre_avec_aretes"))
    raster = image_module.Raster.from_framebuffer(frame)
    if key == "png":
        return image_module.write_png(raster)
    if key == "bmp":
        return image_module.write_bmp(raster)
    if key == "ppm":
        return image_module.write_ppm(raster)
    if key == "tga":
        return image_module.write_tga(raster)
    return image_module.write_jpeg(raster, int(options.get("qualite", 85)))


def _export_points(document: CadDocument, key: str, **options):
    cloud = cloud_module.PointCloud(name=document.name)
    for solid in document.solids():
        cloud.points.extend(solid.vertices())
    for entity in document.visible_entities():
        if isinstance(entity.geometry, Curve):
            cloud.points.extend(entity.geometry.points)
    if not cloud.points:
        raise InteropError("aucun point a exporter")
    if key == "xyz":
        return cloud_module.write_xyz(cloud)
    if key == "csv":
        return cloud_module.write_csv(cloud)
    return cloud_module.write_las(cloud)


def export_file(document: CadDocument, path: str,
                annotations: Optional[Sequence[Dict[str, Any]]] = None,
                **options) -> str:
    """Exporte vers un fichier du disque, DWG compris."""
    extension = os.path.splitext(path)[1].lower()
    if extension == ".dwg":
        return dwg_module.write_dwg(document, path,
                                    options.get("version_dwg", "ACAD2018"))
    spec = spec_for(path)
    payload = export_data(document, spec.key, annotations, **options)
    mode = "wb" if isinstance(payload, (bytes, bytearray)) else "w"
    with open(path, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) \
            as handle:
        handle.write(payload)
    return path


def convert(source: str, target: str, **options) -> Dict[str, Any]:
    """Convertit un fichier d'un format vers un autre."""
    imported = import_file(source)
    document = imported["document"]
    export_file(document, target, **options)
    return {"source": os.path.basename(source),
            "cible": os.path.basename(target),
            "format_source": imported["format"],
            "format_cible": spec_for(target).key,
            "objets": len(document.entities),
            "statistiques": document.statistics()}


__all__ = ["FORMATS", "FormatSpec", "InteropError", "capabilities", "convert",
           "export_data", "export_file", "formats", "identify", "import_data",
           "import_file", "spec_for"]
