"""Deplacements et reseaux : le groupe Modification du ruban.

DEPLACER3D, ROTATION3D, ECHELLE, ALIGNER3D, MIROIR3D, RESEAU (rectangulaire,
polaire, sur trajectoire), COPIER, DECALER. Les fonctions acceptent aussi
bien un solide qu'une liste de solides et renvoient toujours de nouveaux
objets : l'original n'est jamais modifie, ce qui rend l'annulation triviale.
"""
from __future__ import annotations

import math
from typing import Iterable, List, Optional, Sequence, Union

from .math3d import Mat4, ORIGIN, Plane, TOL, Vec3, X_AXIS, Y_AXIS, Z_AXIS
from .profiles import Curve
from .solid import Solid

Geometry = Union[Solid, Curve]


def _apply(item: Geometry, matrix: Mat4, name: Optional[str] = None) -> Geometry:
    if isinstance(item, Solid):
        return item.transformed(matrix, name)
    return item.transformed(matrix)


def transform(items, matrix: Mat4) -> List[Geometry]:
    """Applique une matrice a un objet ou a une selection."""
    return [_apply(item, matrix) for item in _as_list(items)]


def _as_list(items) -> List[Geometry]:
    if isinstance(items, (Solid, Curve)):
        return [items]
    return list(items)


def move(items, vector) -> List[Geometry]:
    """Commande DEPLACER / DEPLACER3D."""
    return transform(items, Mat4.translation(vector))


def copy_items(items, vector=ORIGIN, copies: int = 1) -> List[Geometry]:
    """Commande COPIER : n copies decalees du meme vecteur."""
    if copies < 1:
        raise ValueError("COPIER : au moins une copie")
    step = Vec3.of(vector)
    out: List[Geometry] = []
    for index in range(1, copies + 1):
        out.extend(transform(items, Mat4.translation(step * index)))
    return out


def rotate3d(items, axis=Z_AXIS, angle_deg: float = 90.0, base=ORIGIN
             ) -> List[Geometry]:
    """Commande ROTATION3D : rotation autour d'un axe quelconque."""
    return transform(items, Mat4.rotation(axis, math.radians(angle_deg), base))


def rotate_between_points(items, point_a, point_b, angle_deg: float
                          ) -> List[Geometry]:
    """ROTATION3D par deux points definissant l'axe."""
    a, b = Vec3.of(point_a), Vec3.of(point_b)
    axis = b - a
    if axis.norm() < TOL:
        raise ValueError("ROTATION3D : les deux points sont confondus")
    return transform(items, Mat4.rotation(axis, math.radians(angle_deg), a))


def scale3d(items, factor, base=ORIGIN) -> List[Geometry]:
    """Commande ECHELLE : facteur unique ou facteurs par axe."""
    if isinstance(factor, (int, float)) and factor <= 0:
        raise ValueError("ECHELLE : le facteur doit etre positif")
    return transform(items, Mat4.scaling(factor, base))


def mirror3d(items, plane: Plane, keep_source: bool = True) -> List[Geometry]:
    """Commande MIROIR3D : symetrie par rapport a un plan."""
    mirrored = transform(items, Mat4.mirror(plane))
    return (_as_list(items) + mirrored) if keep_source else mirrored


def align3d(items, source_points: Sequence, target_points: Sequence
            ) -> List[Geometry]:
    """Commande ALIGNER3D : un, deux ou trois couples de points."""
    return transform(items, Mat4.align(source_points, target_points))


def array_rectangular(items, columns: int = 3, rows: int = 2, levels: int = 1,
                      column_spacing: float = 1000.0,
                      row_spacing: float = 1000.0,
                      level_spacing: float = 1000.0,
                      axes=(X_AXIS, Y_AXIS, Z_AXIS)) -> List[Geometry]:
    """Commande RESEAU rectangulaire, en trois dimensions (RESEAU3D)."""
    if min(columns, rows, levels) < 1:
        raise ValueError("RESEAU : au moins une occurrence par direction")
    ax, ay, az = (Vec3.of(a).unit() for a in axes)
    out: List[Geometry] = []
    for level in range(levels):
        for row in range(rows):
            for column in range(columns):
                offset = (ax * (column * column_spacing)
                          + ay * (row * row_spacing)
                          + az * (level * level_spacing))
                out.extend(transform(items, Mat4.translation(offset)))
    return out


def array_polar(items, center=ORIGIN, axis=Z_AXIS, count: int = 6,
                total_angle_deg: float = 360.0, rotate_items: bool = True
                ) -> List[Geometry]:
    """Commande RESEAUPOLAIRE : repartition autour d'un axe."""
    if count < 1:
        raise ValueError("RESEAUPOLAIRE : au moins une occurrence")
    center = Vec3.of(center)
    full = abs(abs(total_angle_deg) - 360.0) < 1e-6
    divisor = count if full else max(1, count - 1)
    out: List[Geometry] = []
    for index in range(count):
        angle = math.radians(total_angle_deg) * index / float(divisor)
        rotation = Mat4.rotation(axis, angle, center)
        if rotate_items:
            out.extend(transform(items, rotation))
        else:
            source = _as_list(items)
            for item in source:
                pivot = item.centroid if isinstance(item, Solid) else item.start
                moved = rotation.apply(pivot)
                out.append(_apply(item, Mat4.translation(moved - pivot)))
    return out


def array_path(items, path: Curve, count: int = 6, align: bool = True,
               measure: bool = False, spacing: Optional[float] = None
               ) -> List[Geometry]:
    """Commande RESEAUCHEMIN : occurrences reparties le long d'une courbe.

    `measure` place les occurrences a intervalle fixe (`spacing`) au lieu de
    les repartir sur toute la longueur.
    """
    if count < 1:
        raise ValueError("RESEAUCHEMIN : au moins une occurrence")
    length = path.length
    if length < TOL:
        raise ValueError("RESEAUCHEMIN : trajectoire de longueur nulle")
    if measure:
        if not spacing or spacing <= 0:
            raise ValueError("RESEAUCHEMIN : pas de mesure invalide")
        count = max(1, int(length // spacing) + 1)
    samples = path.resampled(max(2, count if count > 1 else 2))
    points = samples.points[:count] if count > 1 else [path.start]
    tangents = samples.tangents()
    source = _as_list(items)
    origin = Vec3()
    for item in source:
        origin = origin + (item.centroid if isinstance(item, Solid) else item.start)
    origin = origin / float(len(source)) if source else ORIGIN

    out: List[Geometry] = []
    reference = tangents[0]
    for index, point in enumerate(points):
        matrix = Mat4.translation(point - origin)
        if align:
            tangent = tangents[min(index, len(tangents) - 1)]
            axis = reference.cross(tangent)
            if axis.norm() > 1e-9:
                matrix = Mat4.translation(point - origin) * \
                    Mat4.rotation(axis, reference.angle_to(tangent), origin)
        out.extend(transform(source, matrix))
    return out


def array_along_helix(items, center=ORIGIN, radius: float = 1000.0,
                      height: float = 3000.0, turns: float = 2.0,
                      count: int = 12) -> List[Geometry]:
    """Reseau sur helice : escalier helicoidal, rampe, convoyeur."""
    return array_path(items, Curve.helix(center, radius, radius, height, turns),
                      count, align=True)


def explode_positions(items) -> List[List[float]]:
    """Centres des objets d'une selection : utile a l'affichage des poignees."""
    out: List[List[float]] = []
    for item in _as_list(items):
        pivot = item.centroid if isinstance(item, Solid) else item.start
        out.append([round(v, 3) for v in pivot])
    return out


def bounding_box(items):
    """Boite englobante d'une selection complete."""
    from .math3d import BBox3
    box = BBox3()
    for item in _as_list(items):
        if isinstance(item, Solid):
            for polygon in item.polygons:
                for vertex in polygon.vertices:
                    box.add(vertex)
        else:
            for point in item.points:
                box.add(point)
    return box


def align_to_face(item: Solid, face_index: int, target_point,
                  target_normal) -> Solid:
    """Pose un solide sur une face : le poser-coller du ruban 3D."""
    if not 0 <= face_index < len(item.polygons):
        raise ValueError("face inconnue : %d" % face_index)
    face = item.polygons[face_index]
    source_normal = face.normal
    target_normal = Vec3.of(target_normal).unit()
    axis = source_normal.cross(-target_normal)
    if axis.norm() < 1e-9:
        rotation = Mat4.identity() if source_normal.dot(target_normal) < 0 \
            else Mat4.rotation(source_normal.any_perpendicular(), math.pi,
                               face.centroid)
    else:
        rotation = Mat4.rotation(axis, source_normal.angle_to(-target_normal),
                                 face.centroid)
    placed = item.transformed(rotation)
    moved = placed.polygons[face_index].centroid
    return placed.transformed(Mat4.translation(Vec3.of(target_point) - moved))
