"""Primitives volumiques du ruban Modelisation 3D.

Reprend un pour un les commandes de creation de solides d'AutoCAD :
BOITE, BISEAU, CONE, SPHERE, CYLINDRE, TORE, PYRAMIDE, POLYSOLIDE, plus
les primitives de maillage du menu Maillage.

Toutes les fonctions renvoient un `Solid` ferme, immediatement utilisable
par les operations booleennes et les exports.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence

from .math3d import (Mat4, ORIGIN, Plane, TOL, Vec3, X_AXIS, XY_PLANE, Y_AXIS,
                     Z_AXIS)
from .profiles import DEFAULT_SEGMENTS, Curve, Profile, arc_points
from .solid import Polygon, Solid


def _quad(a: Vec3, b: Vec3, c: Vec3, d: Vec3, material: str) -> Polygon:
    return Polygon([a, b, c, d], material=material)


def _build(polygons: List[Polygon], name: str, material: str) -> Solid:
    """Assemble un solide ferme dont les faces regardent vers l'exterieur.

    Le controle du volume signe est le garde-fou qui evite qu'une primitive
    mal enroulee ne renverse le resultat d'une SOUSTRACTION.
    """
    solid = Solid.from_polygons(polygons, name=name, material=material)
    return solid.outward().apply_appearance()


def box(length: float = 1000.0, width: float = 1000.0, height: float = 1000.0,
        origin=ORIGIN, centered: bool = False, material: str = "default",
        name: str = "boite") -> Solid:
    """Commande BOITE : paves droits, murs, semelles, blocs de coffrage."""
    if min(length, width, height) <= 0:
        raise ValueError("BOITE : les trois dimensions doivent etre positives")
    o = Vec3.of(origin)
    if centered:
        o = o - Vec3(length / 2.0, width / 2.0, height / 2.0)
    x, y, z = length, width, height
    v = [o, o + Vec3(x, 0, 0), o + Vec3(x, y, 0), o + Vec3(0, y, 0),
         o + Vec3(0, 0, z), o + Vec3(x, 0, z), o + Vec3(x, y, z),
         o + Vec3(0, y, z)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7)]
    return _build([_quad(v[i], v[j], v[k], v[l], material)
                   for i, j, k, l in faces], name, material)


def wedge(length: float = 1000.0, width: float = 1000.0, height: float = 1000.0,
          origin=ORIGIN, material: str = "default", name: str = "biseau") -> Solid:
    """Commande BISEAU : demi-boite coupee selon la diagonale (rampes, pentes)."""
    if min(length, width, height) <= 0:
        raise ValueError("BISEAU : les trois dimensions doivent etre positives")
    o = Vec3.of(origin)
    a = o
    b = o + Vec3(length, 0, 0)
    c = o + Vec3(length, width, 0)
    d = o + Vec3(0, width, 0)
    e = o + Vec3(0, 0, height)
    f = o + Vec3(0, width, height)
    return _build([
        Polygon([a, d, c, b], material=material),      # base
        Polygon([a, e, f, d], material=material),      # dos vertical
        Polygon([b, c, f, e], material=material),      # plan incline
        Polygon([a, b, e], material=material),         # pignon avant
        Polygon([d, f, c], material=material),         # pignon arriere
    ], name, material)


def cylinder(radius: float = 500.0, height: float = 1000.0, origin=ORIGIN,
             segments: int = DEFAULT_SEGMENTS, top_radius: Optional[float] = None,
             axis=Z_AXIS, material: str = "default", name: str = "cylindre"
             ) -> Solid:
    """Commande CYLINDRE : poteaux, canalisations, forages, percements."""
    if radius <= 0 or height <= 0:
        raise ValueError("CYLINDRE : rayon et hauteur doivent etre positifs")
    top = radius if top_radius is None else top_radius
    segments = max(3, segments)
    o = Vec3.of(origin)
    direction = Vec3.of(axis).unit()
    plane = Plane.from_point_normal(ORIGIN, direction)
    u, v = plane.basis()
    bottom_ring: List[Vec3] = []
    top_ring: List[Vec3] = []
    for i in range(segments):
        angle = 2 * math.pi * i / float(segments)
        c, s = math.cos(angle), math.sin(angle)
        bottom_ring.append(o + u * (radius * c) + v * (radius * s))
        top_ring.append(o + direction * height + u * (top * c) + v * (top * s))
    polygons = [Polygon(list(reversed(bottom_ring)), material=material)]
    if top > TOL:
        polygons.append(Polygon(list(top_ring), material=material))
    for i in range(segments):
        j = (i + 1) % segments
        if top > TOL:
            polygons.append(_quad(bottom_ring[i], bottom_ring[j], top_ring[j],
                                  top_ring[i], material))
        else:
            polygons.append(Polygon([bottom_ring[i], bottom_ring[j],
                                     top_ring[0]], material=material))
    return _build(polygons, name, material)


def cone(radius: float = 500.0, height: float = 1000.0, origin=ORIGIN,
         segments: int = DEFAULT_SEGMENTS, top_radius: float = 0.0,
         axis=Z_AXIS, material: str = "default", name: str = "cone") -> Solid:
    """Commande CONE, y compris le cone tronque (option Rayon superieur)."""
    return cylinder(radius, height, origin, segments, top_radius, axis,
                    material, name)


def sphere(radius: float = 500.0, center=ORIGIN, segments: int = DEFAULT_SEGMENTS,
           rings: Optional[int] = None, material: str = "default",
           name: str = "sphere") -> Solid:
    """Commande SPHERE : coupoles, luminaires, noeuds de structure."""
    if radius <= 0:
        raise ValueError("SPHERE : le rayon doit etre positif")
    segments = max(3, segments)
    rings = max(2, rings if rings is not None else max(2, segments // 2))
    c = Vec3.of(center)

    def point(i: int, j: int) -> Vec3:
        theta = math.pi * j / float(rings)
        phi = 2 * math.pi * i / float(segments)
        return c + Vec3(radius * math.sin(theta) * math.cos(phi),
                        radius * math.sin(theta) * math.sin(phi),
                        radius * math.cos(theta))

    polygons: List[Polygon] = []
    for j in range(rings):
        for i in range(segments):
            i2 = (i + 1) % segments
            a, b = point(i, j), point(i2, j)
            d, e = point(i, j + 1), point(i2, j + 1)
            if j == 0:
                polygons.append(Polygon([a, d, e], material=material))
            elif j == rings - 1:
                polygons.append(Polygon([a, d, b], material=material))
            else:
                polygons.append(_quad(a, d, e, b, material))
    return _build(polygons, name, material)


def torus(radius: float = 500.0, tube_radius: float = 100.0, center=ORIGIN,
          segments: int = DEFAULT_SEGMENTS, tube_segments: int = 24,
          material: str = "default", name: str = "tore") -> Solid:
    """Commande TORE : joints, anneaux, conduits circulaires."""
    if radius <= 0 or tube_radius <= 0:
        raise ValueError("TORE : les deux rayons doivent etre positifs")
    segments, tube_segments = max(3, segments), max(3, tube_segments)
    c = Vec3.of(center)

    def point(i: int, j: int) -> Vec3:
        u = 2 * math.pi * i / float(segments)
        v = 2 * math.pi * j / float(tube_segments)
        r = radius + tube_radius * math.cos(v)
        return c + Vec3(r * math.cos(u), r * math.sin(u),
                        tube_radius * math.sin(v))

    polygons: List[Polygon] = []
    for i in range(segments):
        for j in range(tube_segments):
            i2, j2 = (i + 1) % segments, (j + 1) % tube_segments
            polygons.append(_quad(point(i, j), point(i2, j), point(i2, j2),
                                  point(i, j2), material))
    return _build(polygons, name, material)


def pyramid(radius: float = 500.0, height: float = 1000.0, sides: int = 4,
            origin=ORIGIN, top_radius: float = 0.0, inscribed: bool = True,
            material: str = "default", name: str = "pyramide") -> Solid:
    """Commande PYRAMIDE : de 3 a 32 cotes, pleine ou tronquee."""
    if sides < 3:
        raise ValueError("PYRAMIDE : au moins 3 cotes")
    if radius <= 0 or height <= 0:
        raise ValueError("PYRAMIDE : rayon et hauteur doivent etre positifs")
    o = Vec3.of(origin)
    base = Profile.regular_polygon(sides, radius, o, XY_PLANE, inscribed).outline
    polygons = [Polygon(list(reversed(base)), material=material)]
    apex = o + Vec3(0, 0, height)
    if top_radius > TOL:
        top = Profile.regular_polygon(sides, top_radius, apex, XY_PLANE,
                                      inscribed).outline
        polygons.append(Polygon(list(top), material=material))
        for i in range(sides):
            j = (i + 1) % sides
            polygons.append(_quad(base[i], base[j], top[j], top[i], material))
    else:
        for i in range(sides):
            j = (i + 1) % sides
            polygons.append(Polygon([base[i], base[j], apex], material=material))
    return _build(polygons, name, material)


def polysolid(points: Sequence, width: float = 200.0, height: float = 2500.0,
              closed: bool = False, justify: str = "centre",
              elevation: float = 0.0, material: str = "default",
              name: str = "polysolide") -> Solid:
    """Commande POLYSOLIDE : une polyligne devient un mur d'epaisseur donnee.

    Justification : gauche, centre ou droite, comme dans la boite de dialogue
    d'AutoCAD.
    """
    from .solid import union_all
    pts = [Vec3.of(p) for p in points]
    if len(pts) < 2:
        raise ValueError("POLYSOLIDE : au moins deux points")
    if width <= 0 or height <= 0:
        raise ValueError("POLYSOLIDE : largeur et hauteur doivent etre positives")
    offsets = {"gauche": 0.0, "centre": -0.5, "droite": -1.0}
    if justify not in offsets:
        raise ValueError("POLYSOLIDE : justification inconnue %r" % justify)
    shift = offsets[justify]
    segments = list(zip(pts, pts[1:]))
    if closed and len(pts) > 2:
        segments.append((pts[-1], pts[0]))
    pieces: List[Solid] = []
    for a, b in segments:
        direction = b - a
        length = direction.norm()
        if length < TOL:
            continue
        d = direction.unit()
        normal = Vec3(-d.y, d.x, 0.0)
        if normal.norm() < TOL:
            normal = X_AXIS
        normal = normal.unit()
        base = a + normal * (width * shift) + Vec3(0, 0, elevation)
        outline = [base, base + d * length, base + d * length + normal * width,
                   base + normal * width]
        pieces.append(extrude_outline(outline, height, material, name))
    if not pieces:
        raise ValueError("POLYSOLIDE : trajectoire de longueur nulle")
    result = union_all(pieces, name)
    result.material = material
    return result.apply_appearance()


def extrude_outline(outline: Sequence, height: float, material: str = "default",
                    name: str = "prisme") -> Solid:
    """Prisme droit sur un contour ferme : brique de base de nombreux outils."""
    pts = [Vec3.of(p) for p in outline]
    if len(pts) < 3 or abs(height) < TOL:
        raise ValueError("prisme : contour ou hauteur invalide")
    profile = Profile(pts).oriented(Z_AXIS if height > 0 else -Z_AXIS)
    base = profile.outline
    top = [p + Vec3(0, 0, height) for p in base]
    polygons = [Polygon(list(reversed(base)), material=material),
                Polygon(list(top), material=material)]
    for i in range(len(base)):
        j = (i + 1) % len(base)
        polygons.append(_quad(base[i], base[j], top[j], top[i], material))
    return _build(polygons, name, material)


# ---------------------------------------------------------------------------
# Primitives de maillage (menu Maillage : MAILLEBOITE, MAILLESPHERE, ...)
# ---------------------------------------------------------------------------
def mesh_box(length: float = 1000.0, width: float = 1000.0,
             height: float = 1000.0, origin=ORIGIN, divisions: int = 2,
             material: str = "default") -> Solid:
    """Commande MAILLEBOITE : boite subdivisee, base des maillages lissables."""
    from .mesh_tools import subdivide
    return subdivide(box(length, width, height, origin, material=material,
                         name="maille_boite"), max(0, divisions - 1))


def mesh_sphere(radius: float = 500.0, center=ORIGIN, divisions: int = 16,
                material: str = "default") -> Solid:
    """Commande MAILLESPHERE."""
    return sphere(radius, center, divisions, divisions // 2, material,
                  "maille_sphere")


def mesh_cylinder(radius: float = 500.0, height: float = 1000.0, origin=ORIGIN,
                  divisions: int = 16, material: str = "default") -> Solid:
    """Commande MAILLECYLINDRE."""
    return cylinder(radius, height, origin, divisions, None, Z_AXIS, material,
                    "maille_cylindre")


def mesh_cone(radius: float = 500.0, height: float = 1000.0, origin=ORIGIN,
              divisions: int = 16, material: str = "default") -> Solid:
    """Commande MAILLECONE."""
    return cone(radius, height, origin, divisions, 0.0, Z_AXIS, material,
                "maille_cone")


def mesh_torus(radius: float = 500.0, tube_radius: float = 100.0, center=ORIGIN,
               divisions: int = 24, material: str = "default") -> Solid:
    """Commande MAILLETORE."""
    return torus(radius, tube_radius, center, divisions, divisions // 2,
                 material, "maille_tore")


def mesh_pyramid(radius: float = 500.0, height: float = 1000.0, sides: int = 4,
                 origin=ORIGIN, material: str = "default") -> Solid:
    """Commande MAILLEPYRAMIDE."""
    return pyramid(radius, height, sides, origin, 0.0, True, material,
                   "maille_pyramide")


def mesh_wedge(length: float = 1000.0, width: float = 1000.0,
               height: float = 1000.0, origin=ORIGIN,
               material: str = "default") -> Solid:
    """Commande MAILLEBISEAU."""
    return wedge(length, width, height, origin, material, "maille_biseau")


PRIMITIVES = {
    "boite": box, "biseau": wedge, "cylindre": cylinder, "cone": cone,
    "sphere": sphere, "tore": torus, "pyramide": pyramid,
    "polysolide": polysolid, "maille_boite": mesh_box,
    "maille_sphere": mesh_sphere, "maille_cylindre": mesh_cylinder,
    "maille_cone": mesh_cone, "maille_tore": mesh_torus,
    "maille_pyramide": mesh_pyramid, "maille_biseau": mesh_wedge,
}
