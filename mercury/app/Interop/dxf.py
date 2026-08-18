"""Lecture et ecriture DXF, du R12 a l'AC1032 (AutoCAD 2018-2021).

Le DXF est le format d'echange documente d'Autodesk : tout ce qui entre ou
sort de MERCURY passe par lui, y compris les DWG convertis. L'ecriture vise
la compatibilite maximale (sections HEADER, TABLES, BLOCKS, ENTITIES,
OBJECTS) et la lecture tolere les fichiers partiels produits par les
exportateurs tiers.

Entites gerees : POINT, LINE, LWPOLYLINE, POLYLINE (2D, 3D, maillage et
polyface), CIRCLE, ARC, ELLIPSE, SPLINE, TEXT, MTEXT, 3DFACE, SOLID, INSERT,
DIMENSION, HATCH, MESH.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from CAD_Core.document import ACI_COLORS, CadDocument, Layer
from CAD_Core.math3d import TOL, Vec3
from CAD_Core.profiles import Curve, Profile, bulge_arc, arc_points
from CAD_Core.solid import Polygon, Solid

DXF_VERSIONS = {
    "R12": "AC1009", "R13": "AC1012", "R14": "AC1014", "2000": "AC1015",
    "2004": "AC1018", "2007": "AC1021", "2010": "AC1024", "2013": "AC1027",
    "2018": "AC1032", "2021": "AC1032",
}
DEFAULT_VERSION = "2018"


class DxfError(ValueError):
    """Fichier DXF illisible ou incoherent."""


# ---------------------------------------------------------------------------
# Ecriture
# ---------------------------------------------------------------------------
class DxfWriter:
    """Construit un fichier DXF complet a partir d'un document CAO."""

    def __init__(self, version: str = DEFAULT_VERSION) -> None:
        if version not in DXF_VERSIONS:
            raise DxfError("version DXF inconnue : %s" % version)
        self.version = version
        self.release = DXF_VERSIONS[version]
        self._lines: List[str] = []
        self._handle = 0x200

    # -- primitives d'ecriture --------------------------------------------
    def tag(self, code: int, value) -> None:
        if isinstance(value, float):
            self._lines.append("%d\n%.9g" % (code, value))
        else:
            self._lines.append("%d\n%s" % (code, value))

    def next_handle(self) -> str:
        self._handle += 1
        return "%X" % self._handle

    def _entity_header(self, kind: str, layer: str, color: int = 256,
                       linetype: str = "PARCALQUE", subclass: str = "") -> None:
        self.tag(0, kind)
        if self.release != "AC1009":
            self.tag(5, self.next_handle())
            self.tag(100, "AcDbEntity")
        self.tag(8, layer)
        if color != 256:
            self.tag(62, color)
        if linetype not in ("PARCALQUE", "BYLAYER"):
            self.tag(6, linetype)
        if subclass and self.release != "AC1009":
            self.tag(100, subclass)

    # -- entites -----------------------------------------------------------
    def point(self, position, layer: str = "0", color: int = 256) -> None:
        p = Vec3.of(position)
        self._entity_header("POINT", layer, color, subclass="AcDbPoint")
        self.tag(10, p.x)
        self.tag(20, p.y)
        self.tag(30, p.z)

    def line(self, start, end, layer: str = "0", color: int = 256,
             linetype: str = "PARCALQUE") -> None:
        a, b = Vec3.of(start), Vec3.of(end)
        self._entity_header("LINE", layer, color, linetype, "AcDbLine")
        for code, value in ((10, a.x), (20, a.y), (30, a.z),
                            (11, b.x), (21, b.y), (31, b.z)):
            self.tag(code, value)

    def polyline(self, points: Sequence, closed: bool = False,
                 layer: str = "0", color: int = 256,
                 elevation: Optional[float] = None) -> None:
        """LWPOLYLINE si la polyligne est plane, POLYLINE 3D sinon."""
        pts = [Vec3.of(p) for p in points]
        if len(pts) < 2:
            return
        planar = all(abs(p.z - pts[0].z) < 1e-6 for p in pts)
        if planar and self.release != "AC1009":
            self._entity_header("LWPOLYLINE", layer, color,
                                subclass="AcDbPolyline")
            self.tag(90, len(pts))
            self.tag(70, 1 if closed else 0)
            self.tag(38, pts[0].z if elevation is None else elevation)
            for point in pts:
                self.tag(10, point.x)
                self.tag(20, point.y)
            return
        self._entity_header("POLYLINE", layer, color, subclass="AcDb3dPolyline")
        self.tag(66, 1)
        self.tag(10, 0.0)
        self.tag(20, 0.0)
        self.tag(30, 0.0)
        self.tag(70, (1 if closed else 0) | 8)
        for point in pts:
            self._entity_header("VERTEX", layer, color,
                                subclass="AcDb3dPolylineVertex")
            self.tag(10, point.x)
            self.tag(20, point.y)
            self.tag(30, point.z)
            self.tag(70, 32)
        self.tag(0, "SEQEND")
        if self.release != "AC1009":
            self.tag(5, self.next_handle())
        self.tag(8, layer)

    def circle(self, center, radius: float, layer: str = "0",
               color: int = 256) -> None:
        c = Vec3.of(center)
        self._entity_header("CIRCLE", layer, color, subclass="AcDbCircle")
        self.tag(10, c.x)
        self.tag(20, c.y)
        self.tag(30, c.z)
        self.tag(40, radius)

    def arc(self, center, radius: float, start_deg: float, end_deg: float,
            layer: str = "0", color: int = 256) -> None:
        c = Vec3.of(center)
        self._entity_header("ARC", layer, color, subclass="AcDbCircle")
        self.tag(10, c.x)
        self.tag(20, c.y)
        self.tag(30, c.z)
        self.tag(40, radius)
        if self.release != "AC1009":
            self.tag(100, "AcDbArc")
        self.tag(50, start_deg)
        self.tag(51, end_deg)

    def text(self, position, value: str, height: float = 25.0,
             rotation: float = 0.0, layer: str = "0", color: int = 256,
             style: str = "Standard") -> None:
        p = Vec3.of(position)
        self._entity_header("TEXT", layer, color, subclass="AcDbText")
        self.tag(10, p.x)
        self.tag(20, p.y)
        self.tag(30, p.z)
        self.tag(40, height)
        self.tag(1, value.replace("\n", " "))
        self.tag(50, rotation)
        self.tag(7, style)

    def mtext(self, position, value: str, height: float = 25.0,
              width: float = 0.0, layer: str = "0", color: int = 256) -> None:
        p = Vec3.of(position)
        self._entity_header("MTEXT", layer, color, subclass="AcDbMText")
        self.tag(10, p.x)
        self.tag(20, p.y)
        self.tag(30, p.z)
        self.tag(40, height)
        self.tag(41, width)
        self.tag(71, 1)
        self.tag(1, value.replace("\n", r"\P"))

    def face3d(self, points: Sequence, layer: str = "0",
               color: int = 256) -> None:
        pts = [Vec3.of(p) for p in points][:4]
        while len(pts) < 4:
            pts.append(pts[-1])
        self._entity_header("3DFACE", layer, color, subclass="AcDbFace")
        for index, point in enumerate(pts):
            self.tag(10 + index, point.x)
            self.tag(20 + index, point.y)
            self.tag(30 + index, point.z)

    def polyface_mesh(self, vertices: Sequence, faces: Sequence,
                      layer: str = "0", color: int = 256) -> None:
        """Maillage polyface : la facon standard d'ecrire un solide en DXF."""
        points = [Vec3.of(v) for v in vertices]
        if not points or not faces:
            return
        self._entity_header("POLYLINE", layer, color,
                            subclass="AcDbPolyFaceMesh")
        self.tag(66, 1)
        self.tag(10, 0.0)
        self.tag(20, 0.0)
        self.tag(30, 0.0)
        self.tag(70, 64)
        self.tag(71, len(points))
        self.tag(72, len(faces))
        for point in points:
            self._entity_header("VERTEX", layer, color,
                                subclass="AcDbPolyFaceMeshVertex")
            self.tag(10, point.x)
            self.tag(20, point.y)
            self.tag(30, point.z)
            self.tag(70, 192)
        for face in faces:
            indices = list(face)[:4]
            self._entity_header("VERTEX", layer, color,
                                subclass="AcDbFaceRecord")
            self.tag(10, 0.0)
            self.tag(20, 0.0)
            self.tag(30, 0.0)
            self.tag(70, 128)
            for position, index in enumerate(indices):
                self.tag(71 + position, index + 1)
        self.tag(0, "SEQEND")
        if self.release != "AC1009":
            self.tag(5, self.next_handle())
        self.tag(8, layer)

    def solid(self, solid: Solid, layer: Optional[str] = None,
              color: int = 256, triangulate: bool = False) -> None:
        """Ecrit un solide : maillage polyface, decoupe en triangles au besoin."""
        source = solid
        if triangulate:
            from CAD_Core.mesh_tools import triangulate as to_triangles
            source = to_triangles(solid)
        vertices, faces = source.to_mesh()
        usable: List[Tuple[int, ...]] = []
        for face in faces:
            if len(face) <= 4:
                usable.append(face)
            else:                            # DXF plafonne a quatre sommets
                for k in range(1, len(face) - 1):
                    usable.append((face[0], face[k], face[k + 1]))
        self.polyface_mesh(vertices, usable, layer or solid.layer, color)

    def insert(self, name: str, position, scale: float = 1.0,
               rotation: float = 0.0, layer: str = "0") -> None:
        p = Vec3.of(position)
        self._entity_header("INSERT", layer, subclass="AcDbBlockReference")
        self.tag(2, name)
        self.tag(10, p.x)
        self.tag(20, p.y)
        self.tag(30, p.z)
        self.tag(41, scale)
        self.tag(42, scale)
        self.tag(43, scale)
        self.tag(50, rotation)

    def hatch(self, profile: Profile, pattern: str = "ANSI31",
              scale: float = 1.0, angle_deg: float = 0.0, layer: str = "0",
              color: int = 8) -> None:
        """Hachures : contour ferme et ouvertures, motif nomme."""
        if self.release == "AC1009":
            return                           # HATCH n'existe pas en R12
        self._entity_header("HATCH", layer, color, subclass="AcDbHatch")
        self.tag(10, 0.0)
        self.tag(20, 0.0)
        self.tag(30, profile.outline[0].z if profile.outline else 0.0)
        self.tag(210, 0.0)
        self.tag(220, 0.0)
        self.tag(230, 1.0)
        self.tag(2, pattern)
        self.tag(70, 1 if pattern == "SOLID" else 0)
        self.tag(71, 0)
        rings = profile.rings()
        self.tag(91, len(rings))
        for ring in rings:
            self.tag(92, 7)
            self.tag(72, 0)
            self.tag(73, 1)
            self.tag(93, len(ring))
            for point in ring:
                self.tag(10, point.x)
                self.tag(20, point.y)
            self.tag(97, 0)
        self.tag(75, 1)
        self.tag(76, 1)
        self.tag(52, angle_deg)
        self.tag(41, scale)
        self.tag(77, 0)
        self.tag(78, 0)
        self.tag(98, 0)

    # -- assemblage du fichier --------------------------------------------
    def build(self, document: CadDocument,
              annotations: Optional[Sequence[Dict[str, Any]]] = None) -> str:
        """Serialise un document complet."""
        self._lines = []
        self._header(document)
        self._tables(document)
        self._blocks(document)
        self._entities(document, annotations or [])
        self._objects()
        self.tag(0, "EOF")
        return "\n".join(self._lines) + "\n"

    def _header(self, document: CadDocument) -> None:
        box = document.bbox
        insunits = {"mm": 4, "cm": 5, "m": 6, "in": 1, "ft": 2}
        self.tag(0, "SECTION")
        self.tag(2, "HEADER")
        for name, code, value in (
                ("$ACADVER", 1, self.release),
                ("$HANDSEED", 5, "FFFF"),
                ("$INSUNITS", 70, insunits.get(document.units, 4)),
                ("$LUNITS", 70, 2),
                ("$LUPREC", 70, 4),
                ("$AUNITS", 70, 0),
                ("$AUPREC", 70, 2),
                ("$CLAYER", 8, document.current_layer),
                ("$DIMSCALE", 40, 1.0),
                ("$LTSCALE", 40, 1.0),
                ("$PDMODE", 70, 34),
                ("$PDSIZE", 40, 0.0),
                ("$MEASUREMENT", 70, 1)):
            self.tag(9, name)
            self.tag(code, value)
        if box.valid:
            self.tag(9, "$EXTMIN")
            self.tag(10, box.min.x)
            self.tag(20, box.min.y)
            self.tag(30, box.min.z)
            self.tag(9, "$EXTMAX")
            self.tag(10, box.max.x)
            self.tag(20, box.max.y)
            self.tag(30, box.max.z)
        self.tag(0, "ENDSEC")

    def _tables(self, document: CadDocument) -> None:
        self.tag(0, "SECTION")
        self.tag(2, "TABLES")

        self.tag(0, "TABLE")
        self.tag(2, "LTYPE")
        self.tag(70, 4)
        for name, pattern in (("CONTINUOUS", []), ("DASHED", [12.7, -6.35]),
                              ("CENTER", [31.75, -6.35, 6.35, -6.35]),
                              ("HIDDEN", [6.35, -3.175]),
                              ("DASHDOT", [12.7, -6.35, 0.0, -6.35])):
            self.tag(0, "LTYPE")
            if self.release != "AC1009":
                self.tag(5, self.next_handle())
                self.tag(100, "AcDbSymbolTableRecord")
                self.tag(100, "AcDbLinetypeTableRecord")
            self.tag(2, name)
            self.tag(70, 0)
            self.tag(3, name.title())
            self.tag(72, 65)
            self.tag(73, len(pattern))
            self.tag(40, sum(abs(v) for v in pattern))
            for value in pattern:
                self.tag(49, value)
                if self.release != "AC1009":
                    self.tag(74, 0)
        self.tag(0, "ENDTAB")

        self.tag(0, "TABLE")
        self.tag(2, "LAYER")
        self.tag(70, len(document.layers))
        for layer in document.layers.values():
            self.tag(0, "LAYER")
            if self.release != "AC1009":
                self.tag(5, self.next_handle())
                self.tag(100, "AcDbSymbolTableRecord")
                self.tag(100, "AcDbLayerTableRecord")
            self.tag(2, layer.name)
            self.tag(70, 4 if layer.locked else 0)
            self.tag(62, -abs(layer.color) if not layer.on else layer.color)
            self.tag(6, layer.linetype)
            if self.release != "AC1009":
                self.tag(370, layer.lineweight)
                self.tag(390, "F")
        self.tag(0, "ENDTAB")

        self.tag(0, "TABLE")
        self.tag(2, "STYLE")
        self.tag(70, len(document.text_styles))
        for name, style in document.text_styles.items():
            self.tag(0, "STYLE")
            if self.release != "AC1009":
                self.tag(5, self.next_handle())
                self.tag(100, "AcDbSymbolTableRecord")
                self.tag(100, "AcDbTextStyleTableRecord")
            self.tag(2, name)
            self.tag(70, 0)
            self.tag(40, 0.0)
            self.tag(41, style.get("largeur", 1.0))
            self.tag(50, style.get("oblique", 0.0))
            self.tag(71, 0)
            self.tag(42, style.get("hauteur", 2.5))
            self.tag(3, style.get("police", "arial.ttf"))
            self.tag(4, "")
        self.tag(0, "ENDTAB")
        self.tag(0, "ENDSEC")

    def _blocks(self, document: CadDocument) -> None:
        self.tag(0, "SECTION")
        self.tag(2, "BLOCKS")
        for name in ("*Model_Space", "*Paper_Space"):
            self._block_start(name, (0.0, 0.0, 0.0))
            self._block_end(name)
        for block in document.blocks.values():
            self._block_start(block.name, block.base_point)
            for member in block.entities:
                self._write_entity(member)
            self._block_end(block.name)
        self.tag(0, "ENDSEC")

    def _block_start(self, name: str, base_point) -> None:
        p = Vec3.of(base_point)
        self.tag(0, "BLOCK")
        if self.release != "AC1009":
            self.tag(5, self.next_handle())
            self.tag(100, "AcDbEntity")
        self.tag(8, "0")
        if self.release != "AC1009":
            self.tag(100, "AcDbBlockBegin")
        self.tag(2, name)
        self.tag(70, 0)
        self.tag(10, p.x)
        self.tag(20, p.y)
        self.tag(30, p.z)
        self.tag(3, name)
        self.tag(1, "")

    def _block_end(self, name: str) -> None:
        self.tag(0, "ENDBLK")
        if self.release != "AC1009":
            self.tag(5, self.next_handle())
            self.tag(100, "AcDbEntity")
        self.tag(8, "0")
        if self.release != "AC1009":
            self.tag(100, "AcDbBlockEnd")

    def _entities(self, document: CadDocument,
                  annotations: Sequence[Dict[str, Any]]) -> None:
        self.tag(0, "SECTION")
        self.tag(2, "ENTITIES")
        for entity in document.entities.values():
            self._write_entity(entity)
        for annotation in annotations:
            self._write_annotation(annotation)
        self.tag(0, "ENDSEC")

    def _write_entity(self, entity) -> None:
        geometry = entity.geometry
        layer, color = entity.layer, entity.color
        if isinstance(geometry, Solid):
            self.solid(geometry, layer, color)
        elif isinstance(geometry, Curve):
            self.polyline(geometry.points, geometry.closed, layer, color)
        elif isinstance(geometry, Profile):
            for ring in geometry.rings():
                self.polyline(ring, True, layer, color)
        elif isinstance(geometry, dict):
            self._write_annotation(geometry, layer)

    def _write_annotation(self, annotation: Dict[str, Any],
                          layer: Optional[str] = None) -> None:
        kind = annotation.get("type", "")
        layer = layer or annotation.get("calque", "0")
        points = [Vec3.of(p) for p in annotation.get("points", [])]
        if kind == "texte":
            self.mtext(annotation.get("position", (0, 0, 0)),
                       annotation.get("texte", ""),
                       annotation.get("hauteur", 25.0), layer=layer)
        elif kind.startswith("cotation"):
            if len(points) >= 2:
                self.line(points[0], points[1], layer)
            if len(points) >= 4:
                self.line(points[2], points[3], layer)
                self.line(points[0], points[2], layer)
                self.line(points[1], points[3], layer)
            for arc_point in annotation.get("arc", []):
                pass
            if annotation.get("arc"):
                self.polyline(annotation["arc"], False, layer)
            middle = ((points[2] + points[3]) * 0.5 if len(points) >= 4
                      else (points[0] + points[1]) * 0.5 if len(points) >= 2
                      else Vec3())
            self.text(middle, annotation.get("texte", ""), 25.0, layer=layer)
        elif kind == "hachures":
            outline = annotation.get("contour", [])
            if outline:
                profile = Profile([Vec3.of(p) for p in outline],
                                  [[Vec3.of(p) for p in hole]
                                   for hole in annotation.get("ouvertures", [])])
                self.hatch(profile, annotation.get("motif", "ANSI31"),
                           annotation.get("echelle", 1.0),
                           annotation.get("angle_deg", 0.0), layer,
                           annotation.get("couleur", 8))
        elif kind in ("ligne_repere", "nuage_revision"):
            self.polyline(points, kind == "nuage_revision", layer)
            if kind == "ligne_repere" and points:
                self.text(points[-1], annotation.get("texte", ""),
                          annotation.get("hauteur_texte", 25.0), layer=layer)
        elif kind == "tableau":
            self._write_table(annotation, layer)
        elif points:
            self.polyline(points, False, layer)

    def _write_table(self, annotation: Dict[str, Any], layer: str) -> None:
        origin = Vec3.of(annotation.get("position", (0, 0, 0)))
        widths = annotation.get("largeurs", [])
        height = annotation.get("hauteur_ligne", 60.0)
        rows = annotation.get("lignes", [])
        total = sum(widths)
        for index, row in enumerate(rows):
            y = origin.y - index * height
            self.line((origin.x, y, origin.z), (origin.x + total, y, origin.z),
                      layer)
            x = origin.x
            for column, cell in enumerate(row):
                self.text((x + 10, y - height * 0.7, origin.z), str(cell),
                          height * 0.45, layer=layer)
                x += widths[column] if column < len(widths) else 300.0
        y = origin.y - len(rows) * height
        self.line((origin.x, y, origin.z), (origin.x + total, y, origin.z), layer)
        x = origin.x
        for width in list(widths) + [0.0]:
            self.line((x, origin.y, origin.z), (x, y, origin.z), layer)
            x += width

    def _objects(self) -> None:
        if self.release == "AC1009":
            return
        self.tag(0, "SECTION")
        self.tag(2, "OBJECTS")
        self.tag(0, "DICTIONARY")
        self.tag(5, self.next_handle())
        self.tag(100, "AcDbDictionary")
        self.tag(3, "ACAD_GROUP")
        self.tag(350, self.next_handle())
        self.tag(0, "ENDSEC")


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------
class DxfReader:
    """Analyse un DXF ASCII et reconstruit un document CAO."""

    def __init__(self, text: str) -> None:
        self.tags = self._tokenize(text)
        self.version = "inconnue"

    @staticmethod
    def _tokenize(text: str) -> List[Tuple[int, str]]:
        raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        tags: List[Tuple[int, str]] = []
        index = 0
        while index + 1 < len(raw):
            code_text = raw[index].strip()
            value = raw[index + 1]
            index += 2
            if not code_text:
                continue
            try:
                code = int(code_text)
            except ValueError:
                raise DxfError("code de groupe invalide : %r" % code_text)
            tags.append((code, value.strip()))
        if not tags:
            raise DxfError("fichier DXF vide")
        return tags

    def sections(self) -> Dict[str, List[Tuple[int, str]]]:
        out: Dict[str, List[Tuple[int, str]]] = {}
        current: Optional[str] = None
        buffer: List[Tuple[int, str]] = []
        index = 0
        while index < len(self.tags):
            code, value = self.tags[index]
            if code == 0 and value == "SECTION":
                if index + 1 < len(self.tags) and self.tags[index + 1][0] == 2:
                    current = self.tags[index + 1][1]
                    buffer = []
                    index += 2
                    continue
            if code == 0 and value == "ENDSEC" and current:
                out[current] = buffer
                current = None
                index += 1
                continue
            if current:
                buffer.append((code, value))
            index += 1
        return out

    def read(self, name: str = "importe") -> CadDocument:
        """Renvoie un document contenant calques, courbes, solides et textes."""
        document = CadDocument(name)
        sections = self.sections()
        for code, value in sections.get("HEADER", []):
            if code == 1 and value.startswith("AC"):
                self.version = value
        self._read_layers(sections.get("TABLES", []), document)
        self._read_entities(sections.get("ENTITIES", []), document)
        return document

    @staticmethod
    def _read_layers(tags: Sequence[Tuple[int, str]],
                     document: CadDocument) -> None:
        current: Optional[Dict[str, Any]] = None
        for code, value in tags:
            if code == 0:
                if current and current.get("nom"):
                    name = current["nom"]
                    color = int(current.get("couleur", 7))
                    layer = Layer(name, abs(color) or 7,
                                  current.get("type_ligne", "CONTINUOUS"),
                                  int(current.get("epaisseur", 25)),
                                  on=color >= 0)
                    document.layers[name] = layer
                current = {} if value == "LAYER" else None
                continue
            if current is None:
                continue
            if code == 2:
                current["nom"] = value
            elif code == 62:
                current["couleur"] = _as_int(value, 7)
            elif code == 6:
                current["type_ligne"] = value or "CONTINUOUS"
            elif code == 370:
                current["epaisseur"] = _as_int(value, 25)
        if current and current.get("nom"):
            name = current["nom"]
            document.layers[name] = Layer(name, abs(_as_int(
                current.get("couleur", 7), 7)) or 7)

    def _read_entities(self, tags: Sequence[Tuple[int, str]],
                       document: CadDocument) -> None:
        groups = _split_entities(tags)
        index = 0
        while index < len(groups):
            kind, body = groups[index]
            if kind == "POLYLINE":
                consumed, entity = self._read_polyline(groups, index)
                index += consumed
                if entity is not None:
                    document.add(entity[0], layer=entity[1])
                continue
            self._read_simple(kind, body, document)
            index += 1

    @staticmethod
    def _read_simple(kind: str, body: Dict[int, List[str]],
                     document: CadDocument) -> None:
        layer = _first(body, 8, "0")
        if layer not in document.layers:
            document.add_layer(layer)
        color = _as_int(_first(body, 62, "256"), 256)
        if kind == "LINE":
            a = _point(body, 0)
            b = Vec3(_as_float(_first(body, 11, "0")),
                     _as_float(_first(body, 21, "0")),
                     _as_float(_first(body, 31, "0")))
            document.add(Curve([a, b], False, "ligne"), layer=layer, color=color)
        elif kind == "POINT":
            document.add(Curve([_point(body, 0)], False, "point"), layer=layer,
                         color=color)
        elif kind == "LWPOLYLINE":
            xs = [float(v) for v in body.get(10, [])]
            ys = [float(v) for v in body.get(20, [])]
            elevation = _as_float(_first(body, 38, "0"))
            bulges = [float(v) for v in body.get(42, [])]
            closed = bool(_as_int(_first(body, 70, "0"), 0) & 1)
            points = [Vec3(x, y, elevation) for x, y in zip(xs, ys)]
            if len(bulges) == len(points) and any(abs(b) > 1e-9 for b in bulges):
                refined: List[Vec3] = []
                count = len(points)
                for i in range(count if closed else count - 1):
                    j = (i + 1) % count
                    refined.extend(bulge_arc(points[i], points[j], bulges[i])[:-1])
                if refined:
                    refined.append(points[0] if closed else points[-1])
                    points = refined
            if len(points) >= 2:
                document.add(Curve(points, closed, "polyligne"), layer=layer,
                             color=color)
        elif kind == "CIRCLE":
            center = _point(body, 0)
            radius = _as_float(_first(body, 40, "0"))
            if radius > 0:
                document.add(Curve.circle(center, radius), layer=layer,
                             color=color)
        elif kind == "ARC":
            center = _point(body, 0)
            radius = _as_float(_first(body, 40, "0"))
            start = math.radians(_as_float(_first(body, 50, "0")))
            end = math.radians(_as_float(_first(body, 51, "360")))
            if end <= start:
                end += 2 * math.pi
            if radius > 0:
                document.add(Curve(arc_points(center, radius, start, end),
                                   False, "arc"), layer=layer, color=color)
        elif kind == "ELLIPSE":
            center = _point(body, 0)
            major = Vec3(_as_float(_first(body, 11, "0")),
                         _as_float(_first(body, 21, "0")),
                         _as_float(_first(body, 31, "0")))
            ratio = _as_float(_first(body, 40, "1"))
            radius = major.norm()
            if radius > TOL:
                points = []
                for i in range(72):
                    angle = 2 * math.pi * i / 72.0
                    points.append(center + major * math.cos(angle)
                                  + Vec3(-major.y, major.x, 0.0) * ratio
                                  * math.sin(angle))
                document.add(Curve(points, True, "ellipse"), layer=layer,
                             color=color)
        elif kind == "SPLINE":
            xs = [float(v) for v in body.get(10, [])]
            ys = [float(v) for v in body.get(20, [])]
            zs = [float(v) for v in body.get(30, [])] or [0.0] * len(xs)
            control = [Vec3(x, y, z) for x, y, z in zip(xs, ys, zs)]
            if len(control) >= 2:
                document.add(Curve.spline(control), layer=layer, color=color)
        elif kind in ("TEXT", "MTEXT"):
            document.add({"type": "texte",
                          "position": list(_point(body, 0)),
                          "texte": _first(body, 1, "").replace(r"\P", "\n"),
                          "hauteur": _as_float(_first(body, 40, "25")),
                          "calque": layer},
                         kind="annotation", layer=layer, color=color)
        elif kind in ("3DFACE", "SOLID"):
            points = []
            for corner in range(4):
                if str(10 + corner) or True:
                    x = _first(body, 10 + corner, None)
                    if x is None:
                        continue
                    points.append(Vec3(_as_float(x),
                                       _as_float(_first(body, 20 + corner, "0")),
                                       _as_float(_first(body, 30 + corner, "0"))))
            unique: List[Vec3] = []
            for point in points:
                if not unique or unique[-1].distance_to(point) > 1e-9:
                    unique.append(point)
            if len(unique) >= 3:
                document.add(Solid.from_polygons([Polygon(unique)],
                                                 name="face"), layer=layer,
                             color=color)
        elif kind == "INSERT":
            document.add({"type": "insertion", "bloc": _first(body, 2, ""),
                          "position": list(_point(body, 0)),
                          "echelle": _as_float(_first(body, 41, "1")),
                          "rotation": _as_float(_first(body, 50, "0")),
                          "calque": layer, "points": [list(_point(body, 0))]},
                         kind="annotation", layer=layer, color=color)

    @staticmethod
    def _read_polyline(groups, index: int):
        """Reconstitue POLYLINE + VERTEX + SEQEND (3D, maillage, polyface)."""
        _, header = groups[index]
        layer = _first(header, 8, "0")
        flags = _as_int(_first(header, 70, "0"), 0)
        vertices: List[Vec3] = []
        faces: List[Tuple[int, ...]] = []
        consumed = 1
        cursor = index + 1
        while cursor < len(groups):
            kind, body = groups[cursor]
            consumed += 1
            cursor += 1
            if kind == "SEQEND":
                break
            if kind != "VERTEX":
                consumed -= 1
                cursor -= 1
                break
            vertex_flags = _as_int(_first(body, 70, "0"), 0)
            if vertex_flags & 128 and not vertex_flags & 64:
                indices = []
                for code in (71, 72, 73, 74):
                    value = _as_int(_first(body, code, "0"), 0)
                    if value:
                        indices.append(abs(value) - 1)
                if len(indices) >= 3:
                    faces.append(tuple(indices))
            else:
                vertices.append(_point(body, 0))
        if flags & 64 and faces and vertices:
            polygons = []
            for face in faces:
                points = [vertices[i] for i in face if 0 <= i < len(vertices)]
                if len(points) >= 3:
                    polygons.append(Polygon(points))
            if polygons:
                return consumed, (Solid.from_polygons(polygons,
                                                      name="maillage"), layer)
            return consumed, None
        if len(vertices) >= 2:
            return consumed, (Curve(vertices, bool(flags & 1), "polyligne"),
                              layer)
        return consumed, None


def _split_entities(tags: Sequence[Tuple[int, str]]
                    ) -> List[Tuple[str, Dict[int, List[str]]]]:
    groups: List[Tuple[str, Dict[int, List[str]]]] = []
    current: Optional[Dict[int, List[str]]] = None
    name = ""
    for code, value in tags:
        if code == 0:
            if current is not None:
                groups.append((name, current))
            name = value
            current = {}
            continue
        if current is None:
            continue
        current.setdefault(code, []).append(value)
    if current is not None:
        groups.append((name, current))
    return groups


def _first(body: Dict[int, List[str]], code: int, default=None):
    values = body.get(code)
    return values[0] if values else default


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _point(body: Dict[int, List[str]], offset: int) -> Vec3:
    return Vec3(_as_float(_first(body, 10 + offset, "0")),
                _as_float(_first(body, 20 + offset, "0")),
                _as_float(_first(body, 30 + offset, "0")))


# ---------------------------------------------------------------------------
# Interface courte
# ---------------------------------------------------------------------------
def write_dxf(document: CadDocument, version: str = DEFAULT_VERSION,
              annotations: Optional[Sequence[Dict[str, Any]]] = None) -> str:
    return DxfWriter(version).build(document, annotations)


def read_dxf(text: str, name: str = "importe") -> CadDocument:
    return DxfReader(text).read(name)


def probe_dxf(text: str) -> Dict[str, Any]:
    """Identification rapide : version, sections, nombre d'entites."""
    reader = DxfReader(text)
    sections = reader.sections()
    entities = _split_entities(sections.get("ENTITIES", []))
    kinds: Dict[str, int] = {}
    for kind, _ in entities:
        kinds[kind] = kinds.get(kind, 0) + 1
    version = "inconnue"
    for code, value in sections.get("HEADER", []):
        if code == 1 and value.startswith("AC"):
            version = value
            break
    label = next((k for k, v in DXF_VERSIONS.items() if v == version), version)
    return {"format": "DXF", "version": version, "release": label,
            "sections": sorted(sections), "entites": len(entities),
            "par_type": kinds}
