"""Annotation : cotation, lignes de repere, texte, hachures, tableaux.

Reprend les commandes COTLIN, COTALI, COTANG, COTRAYON, COTDIA, COTARC,
COTORD, LIGNEDEREPERE, TEXTMULT, HACHURES, TABLEAU et NUAGEREV. Chaque
fonction produit une annotation serialisable, dessinable aussi bien en SVG
qu'en DXF ou en PDF.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .math3d import Plane, TOL, Vec3, X_AXIS, Y_AXIS, Z_AXIS
from .profiles import Curve, Profile, arc_points

HATCH_PATTERNS = {
    "SOLID": {"angle": 0.0, "espacement": 0.0, "trait": "plein"},
    "ANSI31": {"angle": 45.0, "espacement": 3.175, "trait": "simple"},
    "ANSI32": {"angle": 45.0, "espacement": 6.35, "trait": "double"},
    "ANSI37": {"angle": 45.0, "espacement": 3.175, "trait": "croise"},
    "AR-CONC": {"angle": 0.0, "espacement": 12.7, "trait": "beton"},
    "AR-B816": {"angle": 0.0, "espacement": 20.3, "trait": "brique"},
    "EARTH": {"angle": 45.0, "espacement": 6.35, "trait": "terre"},
    "GRAVEL": {"angle": 0.0, "espacement": 6.35, "trait": "gravier"},
    "HONEY": {"angle": 0.0, "espacement": 6.35, "trait": "nid_abeille"},
    "NET": {"angle": 0.0, "espacement": 6.35, "trait": "quadrille"},
    "STEEL": {"angle": 45.0, "espacement": 3.175, "trait": "acier"},
    "GRASS": {"angle": 0.0, "espacement": 12.7, "trait": "herbe"},
}

ARROW_HEADS = ["ferme_plein", "ferme_vide", "point", "oblique", "ouvert",
               "origine", "boite", "integrale", "aucun"]


def _format_length(value: float, decimals: int = 2, unit: str = "mm",
                   scale: float = 1.0) -> str:
    """Texte de cote respectant les unites et la precision du style."""
    converted = value * scale
    if unit == "m":
        converted /= 1000.0
    elif unit == "cm":
        converted /= 10.0
    text = ("%%.%df" % decimals) % converted
    if decimals > 0:
        text = text.rstrip("0").rstrip(".") or "0"
    return text


def linear_dimension(start, end, offset: float = 200.0, direction=None,
                     style: str = "ISO-25", decimals: int = 2,
                     unit: str = "mm", text: Optional[str] = None,
                     layer: str = "COTATION") -> Dict[str, Any]:
    """Commande COTLIN : cote lineaire projetee sur un axe."""
    a, b = Vec3.of(start), Vec3.of(end)
    delta = b - a
    if direction is not None:
        axis = Vec3.of(direction).unit()
        measure = abs(delta.dot(axis))
    else:
        axis = delta.unit()
        measure = delta.norm()
    normal = Vec3(-axis.y, axis.x, 0.0)
    if normal.norm() < TOL:
        normal = Y_AXIS
    normal = normal.unit()
    line_a = a + normal * offset
    line_b = b + normal * offset
    return {
        "type": "cotation_lineaire", "style": style, "calque": layer,
        "points": [list(a), list(b), list(line_a), list(line_b)],
        "mesure_mm": round(measure, 4),
        "texte": text or _format_length(measure, decimals, unit),
        "unite": unit, "fleche": "ferme_plein",
        "ligne_attache": [[list(a), list(line_a)], [list(b), list(line_b)]],
    }


def aligned_dimension(start, end, offset: float = 200.0, style: str = "ISO-25",
                      decimals: int = 2, unit: str = "mm",
                      layer: str = "COTATION") -> Dict[str, Any]:
    """Commande COTALI : cote parallele au segment mesure."""
    dimension = linear_dimension(start, end, offset, None, style, decimals,
                                 unit, None, layer)
    dimension["type"] = "cotation_alignee"
    return dimension


def angular_dimension(center, first, second, radius: float = 300.0,
                      style: str = "ISO-25", decimals: int = 1,
                      layer: str = "COTATION") -> Dict[str, Any]:
    """Commande COTANG : angle entre deux directions."""
    c, a, b = Vec3.of(center), Vec3.of(first), Vec3.of(second)
    va, vb = (a - c), (b - c)
    if va.norm() < TOL or vb.norm() < TOL:
        raise ValueError("COTANG : points confondus avec le sommet")
    angle = math.degrees(va.angle_to(vb))
    start_angle = math.atan2(va.y, va.x)
    end_angle = math.atan2(vb.y, vb.x)
    if end_angle < start_angle:
        end_angle += 2 * math.pi
    arc = arc_points(c, radius, start_angle, end_angle, 48)
    return {"type": "cotation_angulaire", "style": style, "calque": layer,
            "sommet": list(c), "points": [list(a), list(b)],
            "arc": [list(p) for p in arc],
            "mesure_deg": round(angle, 4),
            "texte": ("%%.%df" % decimals) % angle + "°"}


def radial_dimension(center, radius: float, angle_deg: float = 45.0,
                     diameter: bool = False, style: str = "ISO-25",
                     decimals: int = 1, layer: str = "COTATION"
                     ) -> Dict[str, Any]:
    """Commandes COTRAYON et COTDIA."""
    c = Vec3.of(center)
    angle = math.radians(angle_deg)
    edge = c + Vec3(radius * math.cos(angle), radius * math.sin(angle), 0.0)
    value = radius * (2.0 if diameter else 1.0)
    prefix = "Ø" if diameter else "R"
    return {"type": "cotation_diametre" if diameter else "cotation_rayon",
            "style": style, "calque": layer, "centre": list(c),
            "points": [list(c), list(edge)], "mesure_mm": round(value, 4),
            "texte": prefix + _format_length(value, decimals)}


def arc_length_dimension(center, radius: float, start_deg: float,
                         end_deg: float, style: str = "ISO-25",
                         layer: str = "COTATION") -> Dict[str, Any]:
    """Commande COTLONGARC."""
    span = math.radians(abs(end_deg - start_deg))
    length = radius * span
    arc = arc_points(center, radius, math.radians(start_deg),
                     math.radians(end_deg), 48)
    return {"type": "cotation_longueur_arc", "style": style, "calque": layer,
            "arc": [list(p) for p in arc], "mesure_mm": round(length, 4),
            "texte": "⌒" + _format_length(length, 1)}


def ordinate_dimension(point, origin=(0, 0, 0), axis: str = "x",
                       leader: float = 300.0, style: str = "ISO-25",
                       layer: str = "COTATION") -> Dict[str, Any]:
    """Commande COTORD : cote d'abscisse ou d'ordonnee."""
    if axis not in ("x", "y", "z"):
        raise ValueError("COTORD : axe inconnu %r" % axis)
    p, o = Vec3.of(point), Vec3.of(origin)
    value = {"x": p.x - o.x, "y": p.y - o.y, "z": p.z - o.z}[axis]
    end = p + (Y_AXIS if axis == "x" else X_AXIS) * leader
    return {"type": "cotation_ordonnee", "style": style, "calque": layer,
            "axe": axis, "points": [list(p), list(end)],
            "mesure_mm": round(value, 4), "texte": _format_length(value, 2)}


def continuous_dimensions(points: Sequence, offset: float = 200.0,
                          style: str = "ISO-25",
                          layer: str = "COTATION") -> List[Dict[str, Any]]:
    """Commande COTCONT : chaine de cotes successives."""
    pts = [Vec3.of(p) for p in points]
    if len(pts) < 2:
        raise ValueError("COTCONT : au moins deux points")
    return [linear_dimension(pts[i], pts[i + 1], offset, None, style,
                             layer=layer) for i in range(len(pts) - 1)]


def baseline_dimensions(points: Sequence, offset: float = 200.0,
                        step: float = 150.0, style: str = "ISO-25",
                        layer: str = "COTATION") -> List[Dict[str, Any]]:
    """Commande COTLIGN : cotes cumulees depuis une meme origine."""
    pts = [Vec3.of(p) for p in points]
    if len(pts) < 2:
        raise ValueError("COTLIGN : au moins deux points")
    return [linear_dimension(pts[0], pts[i], offset + step * (i - 1), None,
                             style, layer=layer) for i in range(1, len(pts))]


def leader(points: Sequence, text: str, arrow: str = "ferme_plein",
           height: float = 25.0, layer: str = "ANNOTATION") -> Dict[str, Any]:
    """Commande LIGNEDEREPERE : fleche de renvoi avec texte."""
    if arrow not in ARROW_HEADS:
        raise ValueError("pointe de fleche inconnue : %s" % arrow)
    pts = [Vec3.of(p) for p in points]
    if len(pts) < 2:
        raise ValueError("LIGNEDEREPERE : au moins deux points")
    return {"type": "ligne_repere", "calque": layer, "fleche": arrow,
            "points": [list(p) for p in pts], "texte": text,
            "hauteur_texte": height}


def mtext(position, text: str, height: float = 25.0, width: float = 0.0,
          rotation_deg: float = 0.0, style: str = "Standard",
          justify: str = "gauche", layer: str = "ANNOTATION") -> Dict[str, Any]:
    """Commande TEXTMULT : texte multiligne."""
    lines = text.split("\n")
    return {"type": "texte", "calque": layer, "style": style,
            "position": list(Vec3.of(position)), "texte": text,
            "lignes": lines, "hauteur": height, "largeur": width,
            "rotation_deg": rotation_deg, "justification": justify}


def hatch(profile: Profile, pattern: str = "ANSI31", scale: float = 1.0,
          angle_deg: float = 0.0, layer: str = "HACHURES",
          color: int = 8) -> Dict[str, Any]:
    """Commande HACHURES : remplit un contour ferme, ouvertures respectees."""
    if pattern not in HATCH_PATTERNS:
        raise ValueError("motif de hachures inconnu : %s" % pattern)
    definition = HATCH_PATTERNS[pattern]
    return {"type": "hachures", "calque": layer, "motif": pattern,
            "echelle": scale, "angle_deg": angle_deg + definition["angle"],
            "couleur": color,
            "contour": [list(p) for p in profile.outline],
            "ouvertures": [[list(p) for p in hole] for hole in profile.holes],
            "aire_mm2": round(profile.area, 3),
            "lignes": hatch_lines(profile, pattern, scale, angle_deg)}


def hatch_lines(profile: Profile, pattern: str = "ANSI31", scale: float = 1.0,
                angle_deg: float = 0.0, limit: int = 400
                ) -> List[List[List[float]]]:
    """Segments reellement traces par un motif : rendu SVG, PDF et DXF."""
    definition = HATCH_PATTERNS[pattern]
    spacing = definition["espacement"] * max(0.05, scale)
    if spacing <= 0:
        return []
    angle = math.radians(angle_deg + definition["angle"])
    direction = Vec3(math.cos(angle), math.sin(angle), 0.0)
    normal = Vec3(-direction.y, direction.x, 0.0)
    points = [p for ring in profile.rings() for p in ring]
    if not points:
        return []
    projections = [p.dot(normal) for p in points]
    along = [p.dot(direction) for p in points]
    low, high = min(projections), max(projections)
    start, end = min(along), max(along)
    elevation = points[0].z
    segments: List[List[List[float]]] = []
    count = int((high - low) / spacing) + 1
    for index in range(min(count, limit)):
        level = low + index * spacing
        crossings: List[float] = []
        for ring in profile.rings():
            size = len(ring)
            for i in range(size):
                a, b = ring[i], ring[(i + 1) % size]
                da = a.dot(normal) - level
                db = b.dot(normal) - level
                if (da > 0) == (db > 0) or abs(da - db) < TOL:
                    continue
                t = da / (da - db)
                crossings.append((a.lerp(b, t)).dot(direction))
        crossings.sort()
        for i in range(0, len(crossings) - 1, 2):
            p0 = direction * crossings[i] + normal * level
            p1 = direction * crossings[i + 1] + normal * level
            segments.append([[p0.x, p0.y, elevation], [p1.x, p1.y, elevation]])
        if definition["trait"] == "croise":
            pass
    return segments


def table(position, rows: Sequence[Sequence[str]], column_widths=None,
          row_height: float = 60.0, title: str = "",
          layer: str = "ANNOTATION") -> Dict[str, Any]:
    """Commande TABLEAU : nomenclature, metre, legende."""
    data = [list(map(str, row)) for row in rows]
    if not data:
        raise ValueError("TABLEAU : aucune ligne")
    columns = max(len(row) for row in data)
    widths = list(column_widths) if column_widths else [300.0] * columns
    return {"type": "tableau", "calque": layer, "titre": title,
            "position": list(Vec3.of(position)), "lignes": data,
            "colonnes": columns, "largeurs": widths,
            "hauteur_ligne": row_height,
            "largeur_totale": sum(widths),
            "hauteur_totale": row_height * (len(data) + (1 if title else 0))}


def revision_cloud(points: Sequence, arc_length: float = 150.0,
                   layer: str = "REVISION") -> Dict[str, Any]:
    """Commande NUAGEREV : nuage de revision autour d'une zone."""
    pts = [Vec3.of(p) for p in points]
    if len(pts) < 3:
        raise ValueError("NUAGEREV : au moins trois points")
    outline: List[Vec3] = []
    count = len(pts)
    for i in range(count):
        a, b = pts[i], pts[(i + 1) % count]
        span = a.distance_to(b)
        bumps = max(1, int(span / max(TOL, arc_length)))
        for k in range(bumps):
            start = a.lerp(b, k / float(bumps))
            end = a.lerp(b, (k + 1) / float(bumps))
            middle = (start + end) * 0.5
            direction = (end - start)
            normal = Vec3(-direction.y, direction.x, 0.0).unit()
            outline.append(start)
            outline.append(middle + normal * (span / bumps * 0.25))
    return {"type": "nuage_revision", "calque": layer,
            "points": [list(p) for p in outline], "longueur_arc": arc_length}


def dimension_from_solid(solid, axis: str = "x", offset: float = 200.0
                         ) -> Dict[str, Any]:
    """Cote automatique de l'encombrement d'un solide selon un axe."""
    box = solid.bbox
    if not box.valid:
        raise ValueError("solide vide : rien a coter")
    start = box.min
    end = {"x": Vec3(box.max.x, box.min.y, box.min.z),
           "y": Vec3(box.min.x, box.max.y, box.min.z),
           "z": Vec3(box.min.x, box.min.y, box.max.z)}[axis]
    return linear_dimension(start, end, offset)
