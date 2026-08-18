"""SVG : export vectoriel du dessin et import des traces d'un logiciel de DAO.

L'export sert aux notices, aux sites web et aux echanges avec les graphistes.
L'import recupere les contours d'un logo, d'un detail ou d'un plan dessine
dans Illustrator ou Inkscape pour les extruder ensuite.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from CAD_Core.document import ACI_COLORS, CadDocument
from CAD_Core.math3d import BBox3, Vec3
from CAD_Core.profiles import Curve, Profile
from CAD_Core.solid import Solid


class SvgError(ValueError):
    """SVG illisible."""


def _hex_color(aci: int) -> str:
    r, g, b = ACI_COLORS.get(aci if aci != 256 else 7, (30, 34, 40))
    if aci in (7, 256):
        r = g = b = 24
    return "#%02x%02x%02x" % (r, g, b)


def write_svg(document: CadDocument, width_px: int = 1600, margin: int = 40,
              annotations: Optional[Sequence[Dict[str, Any]]] = None,
              background: str = "#ffffff", plane: str = "xy") -> str:
    """Projette le document sur un plan et ecrit un SVG a l'echelle."""
    if plane not in ("xy", "xz", "yz"):
        raise SvgError("plan de projection inconnu : %s" % plane)

    def flatten(point) -> Tuple[float, float]:
        p = Vec3.of(point)
        return {"xy": (p.x, p.y), "xz": (p.x, p.z), "yz": (p.y, p.z)}[plane]

    box = document.bbox
    if not box.valid:
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="10" '
                'height="10"/>')
    x0, y0 = flatten(box.min)
    x1, y1 = flatten(box.max)
    span_x = max(1.0, x1 - x0)
    span_y = max(1.0, y1 - y0)
    k = (width_px - 2 * margin) / span_x
    height_px = int(span_y * k + 2 * margin)

    def sx(x: float) -> float:
        return margin + (x - x0) * k

    def sy(y: float) -> float:
        return height_px - margin - (y - y0) * k

    parts: List[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d">' % (width_px, height_px, width_px, height_px),
        '<rect width="100%%" height="100%%" fill="%s"/>' % background,
        '<!-- MERCURY CAD AI X : %s, echelle %.4f px/mm -->'
        % (document.name, k)]

    for layer_name, layer in document.layers.items():
        if not layer.on or layer.frozen:
            continue
        entities = [e for e in document.visible_entities()
                    if e.layer == layer_name]
        if not entities:
            continue
        stroke = _hex_color(layer.color)
        thickness = max(0.4, layer.lineweight / 100.0 * k * 10)
        dash = ' stroke-dasharray="6 3"' if layer.linetype != "CONTINUOUS" else ""
        parts.append('<g id="%s" stroke="%s" stroke-width="%.2f" fill="none"%s>'
                     % (layer_name, stroke, min(4.0, thickness), dash))
        for entity in entities:
            geometry = entity.geometry
            if isinstance(geometry, Solid):
                for a, b in geometry.edges():
                    ax, ay = flatten(a)
                    bx, by = flatten(b)
                    parts.append('<line x1="%.2f" y1="%.2f" x2="%.2f" '
                                 'y2="%.2f"/>' % (sx(ax), sy(ay), sx(bx), sy(by)))
            elif isinstance(geometry, Curve):
                points = " ".join("%.2f,%.2f" % (sx(flatten(p)[0]),
                                                 sy(flatten(p)[1]))
                                  for p in geometry.points)
                tag = "polygon" if geometry.closed else "polyline"
                parts.append('<%s points="%s"/>' % (tag, points))
            elif isinstance(geometry, Profile):
                for ring in geometry.rings():
                    points = " ".join("%.2f,%.2f" % (sx(flatten(p)[0]),
                                                     sy(flatten(p)[1]))
                                      for p in ring)
                    parts.append('<polygon points="%s"/>' % points)
        parts.append("</g>")

    for annotation in annotations or []:
        parts.extend(_annotation_svg(annotation, sx, sy, flatten))
    parts.append("</svg>")
    return "\n".join(parts)


def _annotation_svg(annotation: Dict[str, Any], sx, sy, flatten) -> List[str]:
    kind = annotation.get("type", "")
    out: List[str] = []
    points = [flatten(p) for p in annotation.get("points", [])]
    if kind == "texte":
        x, y = flatten(annotation.get("position", (0, 0, 0)))
        for index, line in enumerate(annotation.get("lignes", [])):
            out.append('<text x="%.2f" y="%.2f" font-family="sans-serif" '
                       'font-size="13" fill="#20242c">%s</text>'
                       % (sx(x), sy(y) + index * 16, _escape(line)))
    elif kind.startswith("cotation"):
        if len(points) >= 4:
            out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" '
                       'stroke="#c0392b" stroke-width="1"/>'
                       % (sx(points[2][0]), sy(points[2][1]),
                          sx(points[3][0]), sy(points[3][1])))
            middle = ((points[2][0] + points[3][0]) / 2,
                      (points[2][1] + points[3][1]) / 2)
            out.append('<text x="%.2f" y="%.2f" font-family="sans-serif" '
                       'font-size="12" fill="#c0392b" text-anchor="middle">%s'
                       '</text>' % (sx(middle[0]), sy(middle[1]) - 4,
                                    _escape(annotation.get("texte", ""))))
    elif kind == "hachures":
        for segment in annotation.get("lignes", []):
            a, b = flatten(segment[0]), flatten(segment[1])
            out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" '
                       'stroke="#8a8f98" stroke-width="0.6"/>'
                       % (sx(a[0]), sy(a[1]), sx(b[0]), sy(b[1])))
    elif points:
        out.append('<polyline points="%s" stroke="#2b6cb0" fill="none" '
                   'stroke-width="1"/>'
                   % " ".join("%.2f,%.2f" % (sx(p[0]), sy(p[1]))
                              for p in points))
    return out


def _escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


NUMBER_RE = re.compile(r"-?\d*\.?\d+(?:[eE][-+]?\d+)?")


def read_svg(text: str, scale: float = 1.0, name: str = "svg",
             flip_y: bool = True) -> CadDocument:
    """Importe les traces d'un SVG : lignes, polylignes, rectangles, cercles,
    et chemins (segments droits et courbes de Bezier)."""
    import xml.etree.ElementTree as ElementTree
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        raise SvgError("SVG illisible : %s" % error)
    document = CadDocument(name)
    document.add_layer("SVG", 3)
    document.set_current_layer("SVG")
    height = _length(root.get("height", "0"))

    def point(x: float, y: float) -> Vec3:
        return Vec3(x * scale, (height - y) * scale if flip_y else y * scale, 0.0)

    for element in root.iter():
        tag = element.tag.split("}")[-1]
        if tag == "line":
            document.add(Curve([point(_length(element.get("x1", "0")),
                                      _length(element.get("y1", "0"))),
                                point(_length(element.get("x2", "0")),
                                      _length(element.get("y2", "0")))],
                               False, "ligne"))
        elif tag in ("polyline", "polygon"):
            values = [float(v) for v in NUMBER_RE.findall(element.get("points", ""))]
            points = [point(values[i], values[i + 1])
                      for i in range(0, len(values) - 1, 2)]
            if len(points) >= 2:
                document.add(Curve(points, tag == "polygon", tag))
        elif tag == "rect":
            x = _length(element.get("x", "0"))
            y = _length(element.get("y", "0"))
            w = _length(element.get("width", "0"))
            h = _length(element.get("height", "0"))
            if w > 0 and h > 0:
                document.add(Curve([point(x, y), point(x + w, y),
                                    point(x + w, y + h), point(x, y + h)],
                                   True, "rectangle"))
        elif tag in ("circle", "ellipse"):
            cx = _length(element.get("cx", "0"))
            cy = _length(element.get("cy", "0"))
            rx = _length(element.get("r", element.get("rx", "0")))
            ry = _length(element.get("r", element.get("ry", "0")))
            if rx > 0 and ry > 0:
                points = []
                for index in range(64):
                    angle = 2 * math.pi * index / 64.0
                    points.append(point(cx + rx * math.cos(angle),
                                        cy + ry * math.sin(angle)))
                document.add(Curve(points, True, tag))
        elif tag == "path":
            for chain in _parse_path(element.get("d", "")):
                points = [point(x, y) for x, y in chain[0]]
                if len(points) >= 2:
                    document.add(Curve(points, chain[1], "chemin"))
    return document


def _length(value: str) -> float:
    match = NUMBER_RE.search(value or "0")
    return float(match.group(0)) if match else 0.0


def _parse_path(data: str) -> List[Tuple[List[Tuple[float, float]], bool]]:
    """Interprete l'attribut d d'un chemin SVG (M, L, H, V, C, Q, Z)."""
    tokens = re.findall(r"[MmLlHhVvCcQqZzAaSsTt]|-?\d*\.?\d+(?:[eE][-+]?\d+)?",
                        data or "")
    chains: List[Tuple[List[Tuple[float, float]], bool]] = []
    current: List[Tuple[float, float]] = []
    x = y = start_x = start_y = 0.0
    index = 0
    command = ""
    while index < len(tokens):
        token = tokens[index]
        if re.match(r"[A-Za-z]", token):
            command = token
            index += 1
            if command in ("Z", "z"):
                if len(current) >= 2:
                    chains.append((current, True))
                current = []
                x, y = start_x, start_y
            continue

        def number() -> float:
            nonlocal index
            value = float(tokens[index])
            index += 1
            return value

        relative = command.islower()
        upper = command.upper()
        if upper == "M":
            nx, ny = number(), number()
            x, y = (x + nx, y + ny) if relative else (nx, ny)
            if len(current) >= 2:
                chains.append((current, False))
            current = [(x, y)]
            start_x, start_y = x, y
            command = "l" if relative else "L"
        elif upper == "L":
            nx, ny = number(), number()
            x, y = (x + nx, y + ny) if relative else (nx, ny)
            current.append((x, y))
        elif upper == "H":
            nx = number()
            x = x + nx if relative else nx
            current.append((x, y))
        elif upper == "V":
            ny = number()
            y = y + ny if relative else ny
            current.append((x, y))
        elif upper in ("C", "Q", "S", "T", "A"):
            count = {"C": 6, "Q": 4, "S": 4, "T": 2, "A": 7}[upper]
            values = [number() for _ in range(count)]
            control: List[Tuple[float, float]] = [(x, y)]
            pairs = [(values[i], values[i + 1])
                     for i in range(0, count - 1, 2)]
            if upper == "A":
                pairs = pairs[-1:]
            for px, py in pairs:
                control.append((x + px, y + py) if relative else (px, py))
            for step in range(1, 13):
                t = step / 12.0
                points = list(control)
                while len(points) > 1:
                    points = [(points[i][0] + (points[i + 1][0] - points[i][0]) * t,
                               points[i][1] + (points[i + 1][1] - points[i][1]) * t)
                              for i in range(len(points) - 1)]
                current.append(points[0])
            x, y = current[-1]
        else:
            index += 1
    if len(current) >= 2:
        chains.append((current, False))
    return chains
