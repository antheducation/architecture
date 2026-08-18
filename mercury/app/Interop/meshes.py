"""Formats de maillage et d'echange 3D.

STL (ASCII et binaire), OBJ avec MTL, PLY (ASCII et binaire), OFF, 3MF, AMF,
VRML 2.0, X3D, COLLADA, glTF 2.0, GLB et 3DS. Ce sont les formats attendus
par les visionneuses, les imprimantes 3D, les moteurs de rendu et les
plateformes de partage de maquettes.

Toutes les fonctions travaillent sur des `Solid` : lire un fichier rend une
liste de solides, en ecrire un consomme la meme liste.
"""
from __future__ import annotations

import base64
import json
import math
import struct
import zipfile
import io
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from CAD_Core.math3d import Vec3
from CAD_Core.mesh_tools import triangulate
from CAD_Core.render_engine import MATERIAL_COLORS
from CAD_Core.solid import Polygon, Solid


class MeshFormatError(ValueError):
    """Fichier de maillage illisible."""


def _merge(solids: Sequence[Solid]) -> Tuple[List[Tuple[float, float, float]],
                                             List[Tuple[int, ...]], List[str]]:
    """Fusionne plusieurs solides en un seul jeu sommets / faces / materiaux."""
    vertices: List[Tuple[float, float, float]] = []
    faces: List[Tuple[int, ...]] = []
    materials: List[str] = []
    index: Dict[Tuple[float, ...], int] = {}
    for solid in solids:
        for polygon in solid.polygons:
            face: List[int] = []
            for vertex in polygon.vertices:
                key = vertex.rounded(5)
                if key not in index:
                    index[key] = len(vertices)
                    vertices.append((vertex.x, vertex.y, vertex.z))
                if not face or face[-1] != index[key]:
                    face.append(index[key])
            if len(face) >= 3:
                faces.append(tuple(face))
                materials.append(polygon.material)
    return vertices, faces, materials


def _triangles(solids: Sequence[Solid]) -> List[Tuple[Vec3, Vec3, Vec3]]:
    out: List[Tuple[Vec3, Vec3, Vec3]] = []
    for solid in solids:
        out.extend(solid.to_triangles())
    return out


def _color_of(material: str) -> Tuple[float, float, float]:
    r, g, b = MATERIAL_COLORS.get(material, MATERIAL_COLORS["default"])
    return (r / 255.0, g / 255.0, b / 255.0)


# ---------------------------------------------------------------------------
# STL
# ---------------------------------------------------------------------------
def write_stl(solids: Sequence[Solid], binary: bool = True,
              name: str = "MERCURY") -> bytes:
    """Ecrit un STL. Le binaire est le choix par defaut : dix fois plus compact."""
    triangles = _triangles(solids)
    if binary:
        out = bytearray()
        header = ("MERCURY CAD AI X - %s" % name)[:79].encode("ascii", "replace")
        out += header.ljust(80, b"\x00")
        out += struct.pack("<I", len(triangles))
        for a, b, c in triangles:
            normal = (b - a).cross(c - a).unit()
            out += struct.pack("<12fH", normal.x, normal.y, normal.z,
                               a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z, 0)
        return bytes(out)
    lines = ["solid %s" % name]
    for a, b, c in triangles:
        normal = (b - a).cross(c - a).unit()
        lines.append("  facet normal %.6e %.6e %.6e" % (normal.x, normal.y,
                                                        normal.z))
        lines.append("    outer loop")
        for point in (a, b, c):
            lines.append("      vertex %.6e %.6e %.6e" % (point.x, point.y,
                                                          point.z))
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid %s" % name)
    return "\n".join(lines).encode("utf-8")


def read_stl(data: bytes, name: str = "stl") -> List[Solid]:
    """Lit un STL, binaire ou ASCII, en detectant le format automatiquement."""
    if len(data) < 15:
        raise MeshFormatError("fichier STL trop court")
    header = data[:80]
    is_binary = True
    if data[:5].lower() == b"solid":
        expected = 84 + 50 * struct.unpack_from("<I", data, 80)[0] \
            if len(data) >= 84 else -1
        is_binary = len(data) == expected
    polygons: List[Polygon] = []
    if is_binary:
        count = struct.unpack_from("<I", data, 80)[0]
        if 84 + count * 50 > len(data):
            raise MeshFormatError("STL binaire tronque (%d triangles annonces)"
                                  % count)
        for index in range(count):
            offset = 84 + index * 50
            values = struct.unpack_from("<12f", data, offset)
            points = [Vec3(*values[3:6]), Vec3(*values[6:9]),
                      Vec3(*values[9:12])]
            polygons.append(Polygon(points))
    else:
        current: List[Vec3] = []
        for line in data.decode("utf-8", "replace").splitlines():
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "vertex" and len(parts) >= 4:
                current.append(Vec3(float(parts[1]), float(parts[2]),
                                    float(parts[3])))
            elif parts[0] == "endloop":
                if len(current) >= 3:
                    polygons.append(Polygon(current))
                current = []
    if not polygons:
        raise MeshFormatError("aucun triangle trouve dans le STL")
    return [Solid.from_polygons(polygons, name=name)]


# ---------------------------------------------------------------------------
# OBJ + MTL
# ---------------------------------------------------------------------------
def write_obj(solids: Sequence[Solid], scale: float = 0.001,
              mtl_name: str = "mercury.mtl",
              swap_axes: bool = True) -> str:
    """OBJ en metres, axe Y vers le haut : convention des moteurs 3D."""
    vertices, faces, materials = _merge(solids)
    lines = ["# MERCURY CAD AI X - export OBJ", "mtllib " + mtl_name]
    for x, y, z in vertices:
        if swap_axes:
            lines.append("v %.6f %.6f %.6f" % (x * scale, z * scale, -y * scale))
        else:
            lines.append("v %.6f %.6f %.6f" % (x * scale, y * scale, z * scale))
    current = None
    for face, material in zip(faces, materials):
        if material != current:
            current = material
            lines.append("usemtl " + material)
        lines.append("f " + " ".join(str(i + 1) for i in face))
    return "\n".join(lines) + "\n"


def write_mtl(materials: Optional[Iterable[str]] = None) -> str:
    names = list(materials) if materials else list(MATERIAL_COLORS)
    out = ["# MERCURY CAD AI X - bibliotheque de materiaux"]
    for name in names:
        r, g, b = _color_of(name)
        out += ["newmtl " + name, "Ka %.3f %.3f %.3f" % (r * 0.3, g * 0.3, b * 0.3),
                "Kd %.3f %.3f %.3f" % (r, g, b), "Ks 0.08 0.08 0.08",
                "Ns 24", "d 1.0", "illum 2", ""]
    return "\n".join(out)


def read_obj(text: str, scale: float = 1000.0, swap_axes: bool = True,
             name: str = "obj") -> List[Solid]:
    """Lit un OBJ (sommets, faces, groupes, materiaux)."""
    vertices: List[Vec3] = []
    polygons: List[Polygon] = []
    material = "default"
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        if parts[0] == "v" and len(parts) >= 4:
            x, y, z = (float(parts[1]), float(parts[2]), float(parts[3]))
            if swap_axes:
                vertices.append(Vec3(x * scale, -z * scale, y * scale))
            else:
                vertices.append(Vec3(x * scale, y * scale, z * scale))
        elif parts[0] == "usemtl" and len(parts) >= 2:
            material = parts[1]
        elif parts[0] == "f" and len(parts) >= 4:
            indices: List[int] = []
            for token in parts[1:]:
                raw = token.split("/")[0]
                try:
                    value = int(raw)
                except ValueError:
                    continue
                indices.append(value - 1 if value > 0 else len(vertices) + value)
            points = [vertices[i] for i in indices if 0 <= i < len(vertices)]
            if len(points) >= 3:
                polygons.append(Polygon(points, material=material))
    if not polygons:
        raise MeshFormatError("aucune face exploitable dans l'OBJ")
    return [Solid.from_polygons(polygons, name=name)]


# ---------------------------------------------------------------------------
# PLY et OFF
# ---------------------------------------------------------------------------
def write_ply(solids: Sequence[Solid], binary: bool = False) -> bytes:
    vertices, faces, _ = _merge(solids)
    header = ["ply",
              "format %s 1.0" % ("binary_little_endian" if binary else "ascii"),
              "comment MERCURY CAD AI X",
              "element vertex %d" % len(vertices),
              "property float x", "property float y", "property float z",
              "element face %d" % len(faces),
              "property list uchar int vertex_index", "end_header"]
    if binary:
        out = bytearray("\n".join(header).encode("ascii") + b"\n")
        for x, y, z in vertices:
            out += struct.pack("<3f", x, y, z)
        for face in faces:
            out += struct.pack("<B", len(face))
            out += struct.pack("<%di" % len(face), *face)
        return bytes(out)
    lines = list(header)
    lines += ["%.6f %.6f %.6f" % v for v in vertices]
    lines += ["%d %s" % (len(f), " ".join(str(i) for i in f)) for f in faces]
    return ("\n".join(lines) + "\n").encode("utf-8")


def read_ply(data: bytes, name: str = "ply") -> List[Solid]:
    text_end = data.find(b"end_header")
    if text_end < 0:
        raise MeshFormatError("en-tete PLY absent")
    header = data[:text_end].decode("ascii", "replace").splitlines()
    binary = any("binary" in line for line in header)
    vertex_count = face_count = 0
    properties = 0
    element = ""
    for line in header:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "element" and len(parts) >= 3:
            element = parts[1]
            if element == "vertex":
                vertex_count = int(parts[2])
            elif element == "face":
                face_count = int(parts[2])
        elif parts[0] == "property" and element == "vertex":
            properties += 1
    offset = data.find(b"\n", text_end) + 1
    vertices: List[Vec3] = []
    polygons: List[Polygon] = []
    if binary:
        cursor = offset
        for _ in range(vertex_count):
            x, y, z = struct.unpack_from("<3f", data, cursor)
            cursor += 4 * max(3, properties)
            vertices.append(Vec3(x, y, z))
        for _ in range(face_count):
            count = data[cursor]
            cursor += 1
            indices = struct.unpack_from("<%di" % count, data, cursor)
            cursor += 4 * count
            points = [vertices[i] for i in indices if 0 <= i < len(vertices)]
            if len(points) >= 3:
                polygons.append(Polygon(points))
    else:
        body = data[offset:].decode("utf-8", "replace").split()
        cursor = 0
        for _ in range(vertex_count):
            values = body[cursor:cursor + max(3, properties)]
            cursor += max(3, properties)
            vertices.append(Vec3(float(values[0]), float(values[1]),
                                 float(values[2])))
        for _ in range(face_count):
            count = int(body[cursor])
            cursor += 1
            indices = [int(v) for v in body[cursor:cursor + count]]
            cursor += count
            points = [vertices[i] for i in indices if 0 <= i < len(vertices)]
            if len(points) >= 3:
                polygons.append(Polygon(points))
    if not polygons:
        raise MeshFormatError("aucune face dans le PLY")
    return [Solid.from_polygons(polygons, name=name)]


def write_off(solids: Sequence[Solid]) -> str:
    vertices, faces, _ = _merge(solids)
    lines = ["OFF", "%d %d 0" % (len(vertices), len(faces))]
    lines += ["%.6f %.6f %.6f" % v for v in vertices]
    lines += ["%d %s" % (len(f), " ".join(str(i) for i in f)) for f in faces]
    return "\n".join(lines) + "\n"


def read_off(text: str, name: str = "off") -> List[Solid]:
    tokens = [t for t in text.split() if t]
    if not tokens or not tokens[0].upper().startswith("OFF"):
        raise MeshFormatError("en-tete OFF absent")
    cursor = 1
    vertex_count, face_count = int(tokens[cursor]), int(tokens[cursor + 1])
    cursor += 3
    vertices: List[Vec3] = []
    for _ in range(vertex_count):
        vertices.append(Vec3(float(tokens[cursor]), float(tokens[cursor + 1]),
                             float(tokens[cursor + 2])))
        cursor += 3
    polygons: List[Polygon] = []
    for _ in range(face_count):
        count = int(tokens[cursor])
        cursor += 1
        indices = [int(tokens[cursor + i]) for i in range(count)]
        cursor += count
        points = [vertices[i] for i in indices if 0 <= i < len(vertices)]
        if len(points) >= 3:
            polygons.append(Polygon(points))
    return [Solid.from_polygons(polygons, name=name)]


# ---------------------------------------------------------------------------
# glTF 2.0 et GLB
# ---------------------------------------------------------------------------
def _gltf_document(solids: Sequence[Solid], scale: float = 0.001,
                   embed: bool = True) -> Tuple[Dict[str, Any], bytes]:
    positions: List[float] = []
    indices: List[int] = []
    for solid in solids:
        for a, b, c in solid.to_triangles():
            base = len(positions) // 3
            for point in (a, b, c):
                positions += [point.x * scale, point.z * scale,
                              -point.y * scale]
            indices += [base, base + 1, base + 2]
    if not positions:
        positions = [0.0, 0.0, 0.0]
        indices = [0, 0, 0]
    position_bytes = struct.pack("<%df" % len(positions), *positions)
    index_bytes = struct.pack("<%dI" % len(indices), *indices)
    padding = (4 - len(position_bytes) % 4) % 4
    buffer = position_bytes + b"\x00" * padding + index_bytes
    document: Dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "MERCURY CAD AI X"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "Maquette"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                    "indices": 1, "material": 0}]}],
        "materials": [{"name": "mercury",
                       "pbrMetallicRoughness": {
                           "baseColorFactor": [0.78, 0.78, 0.76, 1.0],
                           "metallicFactor": 0.05, "roughnessFactor": 0.8}}],
        "buffers": [{"byteLength": len(buffer)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(position_bytes),
             "target": 34962},
            {"buffer": 0, "byteOffset": len(position_bytes) + padding,
             "byteLength": len(index_bytes), "target": 34963}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126,
             "count": len(positions) // 3, "type": "VEC3",
             "min": [min(positions[i::3]) for i in range(3)],
             "max": [max(positions[i::3]) for i in range(3)]},
            {"bufferView": 1, "componentType": 5125, "count": len(indices),
             "type": "SCALAR"}],
    }
    if embed:
        document["buffers"][0]["uri"] = ("data:application/octet-stream;base64,"
                                         + base64.b64encode(buffer).decode())
    return document, buffer


def write_gltf(solids: Sequence[Solid], scale: float = 0.001) -> str:
    document, _ = _gltf_document(solids, scale, embed=True)
    return json.dumps(document)


def write_glb(solids: Sequence[Solid], scale: float = 0.001) -> bytes:
    """GLB : glTF binaire, un seul fichier, lu par tous les visualiseurs web."""
    document, buffer = _gltf_document(solids, scale, embed=False)
    json_bytes = json.dumps(document, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    buffer += b"\x00" * ((4 - len(buffer) % 4) % 4)
    total = 12 + 8 + len(json_bytes) + 8 + len(buffer)
    out = bytearray()
    out += struct.pack("<III", 0x46546C67, 2, total)
    out += struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
    out += struct.pack("<II", len(buffer), 0x004E4942) + buffer
    return bytes(out)


def read_gltf(data, scale: float = 1000.0, name: str = "gltf") -> List[Solid]:
    """Lit un glTF JSON ou un GLB et reconstruit les triangles."""
    if isinstance(data, bytes) and data[:4] == b"glTF":
        length = struct.unpack_from("<I", data, 12)[0]
        document = json.loads(data[20:20 + length].decode("utf-8"))
        binary = b""
        cursor = 20 + length
        while cursor + 8 <= len(data):
            chunk_length, chunk_type = struct.unpack_from("<II", data, cursor)
            payload = data[cursor + 8:cursor + 8 + chunk_length]
            if chunk_type == 0x004E4942:
                binary = payload
            cursor += 8 + chunk_length
    else:
        text = data.decode("utf-8") if isinstance(data, bytes) else data
        document = json.loads(text)
        binary = b""
        for buffer in document.get("buffers", []):
            uri = buffer.get("uri", "")
            if uri.startswith("data:"):
                binary = base64.b64decode(uri.split(",", 1)[1])
    if not binary:
        raise MeshFormatError("glTF sans donnees binaires exploitables")
    views = document.get("bufferViews", [])
    accessors = document.get("accessors", [])

    def read_accessor(index: int) -> List[float]:
        accessor = accessors[index]
        view = views[accessor["bufferView"]]
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        count = accessor["count"]
        kind = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[accessor["type"]]
        code = {5126: "f", 5125: "I", 5123: "H", 5121: "B"}[
            accessor["componentType"]]
        size = struct.calcsize("<" + code)
        return list(struct.unpack_from("<%d%s" % (count * kind, code), binary,
                                       offset))

    polygons: List[Polygon] = []
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            position_index = primitive.get("attributes", {}).get("POSITION")
            if position_index is None:
                continue
            flat = read_accessor(position_index)
            points = [Vec3(flat[i] * scale, -flat[i + 2] * scale,
                           flat[i + 1] * scale)
                      for i in range(0, len(flat), 3)]
            if "indices" in primitive:
                indices = [int(v) for v in read_accessor(primitive["indices"])]
            else:
                indices = list(range(len(points)))
            for i in range(0, len(indices) - 2, 3):
                triangle = [points[indices[i + k]] for k in range(3)
                            if indices[i + k] < len(points)]
                if len(triangle) == 3:
                    polygons.append(Polygon(triangle))
    if not polygons:
        raise MeshFormatError("aucun triangle dans le glTF")
    return [Solid.from_polygons(polygons, name=name)]


# ---------------------------------------------------------------------------
# 3MF, AMF (impression 3D)
# ---------------------------------------------------------------------------
def write_3mf(solids: Sequence[Solid]) -> bytes:
    """3MF : format d'impression 3D de la 3MF Consortium (archive ZIP + XML)."""
    vertices, faces, _ = _merge(solids)
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<model unit="millimeter" '
            'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
            '<metadata name="Application">MERCURY CAD AI X</metadata>',
            '<resources><object id="1" type="model"><mesh><vertices>']
    for x, y, z in vertices:
        rows.append('<vertex x="%.5f" y="%.5f" z="%.5f"/>' % (x, y, z))
    rows.append("</vertices><triangles>")
    for face in faces:
        for k in range(1, len(face) - 1):
            rows.append('<triangle v1="%d" v2="%d" v3="%d"/>'
                        % (face[0], face[k], face[k + 1]))
    rows += ["</triangles></mesh></object></resources>",
             '<build><item objectid="1"/></build>', "</model>"]
    model = "\n".join(rows)
    relationships = ('<?xml version="1.0" encoding="UTF-8"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/'
                     'package/2006/relationships">'
                     '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
                     'Type="http://schemas.microsoft.com/3dmanufacturing/'
                     '2013/01/3dmodel"/></Relationships>')
    content_types = ('<?xml version="1.0" encoding="UTF-8"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/'
                     'package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/'
                     'vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="model" ContentType="application/'
                     'vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("3D/3dmodel.model", model)
    return buffer.getvalue()


def read_3mf(data: bytes, name: str = "3mf") -> List[Solid]:
    import xml.etree.ElementTree as ElementTree
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        candidates = [n for n in archive.namelist() if n.endswith(".model")]
        if not candidates:
            raise MeshFormatError("archive 3MF sans modele")
        root = ElementTree.fromstring(archive.read(candidates[0]))
    namespace = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
    polygons: List[Polygon] = []
    for mesh in root.iter(namespace + "mesh"):
        vertices: List[Vec3] = []
        for vertex in mesh.iter(namespace + "vertex"):
            vertices.append(Vec3(float(vertex.get("x", 0)),
                                 float(vertex.get("y", 0)),
                                 float(vertex.get("z", 0))))
        for triangle in mesh.iter(namespace + "triangle"):
            indices = [int(triangle.get(key, 0)) for key in ("v1", "v2", "v3")]
            points = [vertices[i] for i in indices if 0 <= i < len(vertices)]
            if len(points) == 3:
                polygons.append(Polygon(points))
    if not polygons:
        raise MeshFormatError("aucun triangle dans le 3MF")
    return [Solid.from_polygons(polygons, name=name)]


def write_amf(solids: Sequence[Solid]) -> str:
    """AMF : format additif normalise ISO/ASTM 52915."""
    vertices, faces, _ = _merge(solids)
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<amf unit="millimeter" version="1.1">',
            '<metadata type="producer">MERCURY CAD AI X</metadata>',
            '<object id="1"><mesh><vertices>']
    for x, y, z in vertices:
        rows.append("<vertex><coordinates><x>%.5f</x><y>%.5f</y><z>%.5f</z>"
                    "</coordinates></vertex>" % (x, y, z))
    rows.append("</vertices><volume>")
    for face in faces:
        for k in range(1, len(face) - 1):
            rows.append("<triangle><v1>%d</v1><v2>%d</v2><v3>%d</v3></triangle>"
                        % (face[0], face[k], face[k + 1]))
    rows += ["</volume></mesh></object></amf>"]
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# VRML, X3D, COLLADA
# ---------------------------------------------------------------------------
def write_vrml(solids: Sequence[Solid], scale: float = 0.001) -> str:
    """VRML 2.0 : encore la reference pour les echanges avec les SIG."""
    rows = ["#VRML V2.0 utf8", "# MERCURY CAD AI X"]
    for solid in solids:
        vertices, faces, _ = _merge([solid])
        r, g, b = _color_of(solid.material)
        rows += ["Shape {", "  appearance Appearance { material Material {",
                 "    diffuseColor %.3f %.3f %.3f" % (r, g, b), "  } }",
                 "  geometry IndexedFaceSet {", "    coord Coordinate { point ["]
        rows += ["      %.5f %.5f %.5f," % (x * scale, z * scale, -y * scale)
                 for x, y, z in vertices]
        rows += ["    ] }", "    coordIndex ["]
        rows += ["      %s, -1," % ", ".join(str(i) for i in face)
                 for face in faces]
        rows += ["    ]", "    solid TRUE", "  }", "}"]
    return "\n".join(rows) + "\n"


def write_x3d(solids: Sequence[Solid], scale: float = 0.001) -> str:
    """X3D : successeur XML de VRML, lu par les navigateurs et les visionneuses."""
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<X3D profile="Interchange" version="3.3">', "<Scene>"]
    for solid in solids:
        vertices, faces, _ = _merge([solid])
        r, g, b = _color_of(solid.material)
        points = " ".join("%.5f %.5f %.5f" % (x * scale, z * scale, -y * scale)
                          for x, y, z in vertices)
        index = " ".join("%s -1" % " ".join(str(i) for i in face)
                         for face in faces)
        rows += ['<Shape><Appearance><Material diffuseColor="%.3f %.3f %.3f"/>'
                 "</Appearance>" % (r, g, b),
                 '<IndexedFaceSet solid="true" coordIndex="%s">' % index,
                 '<Coordinate point="%s"/></IndexedFaceSet></Shape>' % points]
    rows += ["</Scene>", "</X3D>"]
    return "\n".join(rows)


def write_collada(solids: Sequence[Solid], scale: float = 0.001) -> str:
    """COLLADA (.dae) : echange avec SketchUp, Blender, 3ds Max, Unity."""
    vertices, faces, _ = _merge(solids)
    triangles: List[Tuple[int, int, int]] = []
    for face in faces:
        for k in range(1, len(face) - 1):
            triangles.append((face[0], face[k], face[k + 1]))
    positions = " ".join("%.5f %.5f %.5f" % (x * scale, z * scale, -y * scale)
                         for x, y, z in vertices)
    index = " ".join("%d %d %d" % t for t in triangles)
    return """<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset><contributor><authoring_tool>MERCURY CAD AI X</authoring_tool></contributor>
    <unit meter="1" name="meter"/><up_axis>Y_UP</up_axis></asset>
  <library_geometries>
    <geometry id="maquette" name="maquette"><mesh>
      <source id="positions"><float_array id="positions-array" count="%d">%s</float_array>
        <technique_common><accessor source="#positions-array" count="%d" stride="3">
          <param name="X" type="float"/><param name="Y" type="float"/>
          <param name="Z" type="float"/></accessor></technique_common></source>
      <vertices id="verts"><input semantic="POSITION" source="#positions"/></vertices>
      <triangles count="%d"><input semantic="VERTEX" source="#verts" offset="0"/>
        <p>%s</p></triangles>
    </mesh></geometry>
  </library_geometries>
  <library_visual_scenes><visual_scene id="scene" name="scene">
    <node id="maquette-node" name="maquette">
      <instance_geometry url="#maquette"/></node></visual_scene></library_visual_scenes>
  <scene><instance_visual_scene url="#scene"/></scene>
</COLLADA>
""" % (len(vertices) * 3, positions, len(vertices), len(triangles), index)


def read_collada(text: str, scale: float = 1000.0,
                 name: str = "dae") -> List[Solid]:
    import xml.etree.ElementTree as ElementTree
    root = ElementTree.fromstring(text)
    namespace = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
    polygons: List[Polygon] = []
    for mesh in root.iter(namespace + "mesh"):
        floats: List[float] = []
        for array in mesh.iter(namespace + "float_array"):
            floats = [float(v) for v in (array.text or "").split()]
            break
        points = [Vec3(floats[i] * scale, -floats[i + 2] * scale,
                       floats[i + 1] * scale)
                  for i in range(0, len(floats) - 2, 3)]
        for triangles in mesh.iter(namespace + "triangles"):
            inputs = len(list(triangles.iter(namespace + "input"))) or 1
            values = [int(v) for v in
                      (triangles.find(namespace + "p").text or "").split()]
            stride = inputs
            indices = values[::stride]
            for i in range(0, len(indices) - 2, 3):
                face = [points[indices[i + k]] for k in range(3)
                        if indices[i + k] < len(points)]
                if len(face) == 3:
                    polygons.append(Polygon(face))
    if not polygons:
        raise MeshFormatError("aucun triangle dans le COLLADA")
    return [Solid.from_polygons(polygons, name=name)]


# ---------------------------------------------------------------------------
# 3DS (Autodesk 3D Studio)
# ---------------------------------------------------------------------------
def write_3ds(solids: Sequence[Solid], scale: float = 0.001) -> bytes:
    """3DS : format historique d'Autodesk, encore lu par de nombreux outils.

    Limite du format : 65 535 sommets et 65 535 faces par objet. Les solides
    sont donc ecrits en objets successifs.
    """
    def chunk(identifier: int, payload: bytes) -> bytes:
        return struct.pack("<HI", identifier, len(payload) + 6) + payload

    objects = b""
    for order, solid in enumerate(solids):
        mesh = triangulate(solid)
        vertices, faces, _ = _merge([mesh])
        if not vertices or len(vertices) > 65535 or len(faces) > 65535:
            if len(vertices) > 65535 or len(faces) > 65535:
                raise MeshFormatError(
                    "3DS : %d sommets et %d faces depassent la limite de "
                    "65535 du format ; exportez en OBJ, glTF ou STL"
                    % (len(vertices), len(faces)))
            continue
        vertex_payload = struct.pack("<H", len(vertices))
        for x, y, z in vertices:
            vertex_payload += struct.pack("<3f", x * scale, y * scale, z * scale)
        face_payload = struct.pack("<H", len(faces))
        for face in faces:
            face_payload += struct.pack("<4H", face[0], face[1], face[2], 7)
        mesh_payload = (chunk(0x4110, vertex_payload)
                        + chunk(0x4120, face_payload))
        name = ("objet%d" % order).encode("ascii")[:10] + b"\x00"
        objects += chunk(0x4000, name + chunk(0x4100, mesh_payload))
    editor = chunk(0x3D3D, struct.pack("<HIi", 0x0100, 10, 1) + objects)
    return chunk(0x4D4D, chunk(0x0002, struct.pack("<I", 3)) + editor)


FORMATS_3D = {
    "stl": ("STL", True), "obj": ("Wavefront OBJ", True),
    "ply": ("Stanford PLY", True), "off": ("Object File Format", True),
    "gltf": ("glTF 2.0", True), "glb": ("glTF binaire", True),
    "3mf": ("3D Manufacturing Format", True), "amf": ("Additive MF", False),
    "wrl": ("VRML 2.0", False), "x3d": ("X3D", False),
    "dae": ("COLLADA", True), "3ds": ("Autodesk 3D Studio", False),
}
