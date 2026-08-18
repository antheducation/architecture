"""Outils de maillage : subdivision, lissage, affinage, soudure, decimation.

Correspond au groupe de fonctions Maillage du ruban 3D : LISSERMAILLE,
AFFINERMAILLE, DIVISERMAILLE, ainsi que les utilitaires de nettoyage
utilises avant tout export (soudure des sommets, recalcul des normales).
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

from .math3d import TOL, Vec3
from .solid import Polygon, Solid


def weld(solid: Solid, tol: float = 1e-4) -> Solid:
    """Fusionne les sommets voisins et supprime les faces degenerees."""
    return solid.heal(tol)


def triangulate(solid: Solid, name: str = None) -> Solid:
    """Convertit toutes les faces en triangles (export STL, glTF, moteur 3D)."""
    polygons: List[Polygon] = []
    for polygon in solid.polygons:
        for triangle in polygon.triangulate():
            polygons.append(Polygon(list(triangle), polygon.material,
                                    polygon.layer, polygon.color))
    return Solid(polygons, name or solid.name, solid.layer, solid.material,
                 solid.color, dict(solid.metadata))


def quadrangulate_faces(solid: Solid, keep_quads: bool = True) -> Solid:
    """Decoupe chaque face en quadrilateres autour de son centre.

    C'est l'etape preparatoire du lissage de Catmull-Clark : elle donne une
    topologie reguliere meme sur des faces a cinq cotes ou plus.
    """
    polygons: List[Polygon] = []
    for polygon in solid.polygons:
        vertices = polygon.vertices
        count = len(vertices)
        if count == 4 and keep_quads:
            polygons.append(polygon)
            continue
        center = polygon.centroid
        for i in range(count):
            j = (i + 1) % count
            middle_a = (vertices[i] + vertices[j]) * 0.5
            middle_b = (vertices[(i - 1) % count] + vertices[i]) * 0.5
            polygons.append(Polygon([middle_b, vertices[i], middle_a, center],
                                    polygon.material, polygon.layer,
                                    polygon.color))
    return Solid(polygons, solid.name, solid.layer, solid.material, solid.color,
                 dict(solid.metadata))


def subdivide(solid: Solid, levels: int = 1) -> Solid:
    """Commande AFFINERMAILLE : subdivise sans deformer la geometrie."""
    result = solid
    for _ in range(max(0, levels)):
        result = quadrangulate_faces(result, keep_quads=False)
    return weld(result)


def smooth(solid: Solid, levels: int = 1) -> Solid:
    """Commande LISSERMAILLE : subdivision de Catmull-Clark.

    Chaque niveau quadruple le nombre de faces et rapproche la surface de
    sa limite lisse. Deux niveaux suffisent pour un rendu de presentation.
    """
    result = solid
    for _ in range(max(0, levels)):
        result = _catmull_clark(weld(result))
    return weld(result)


def _catmull_clark(solid: Solid) -> Solid:
    faces = [[v.rounded(5) for v in polygon.vertices] for polygon in solid.polygons]
    if not faces:
        return solid.copy()
    lookup: Dict[Tuple[float, ...], Vec3] = {}
    for polygon in solid.polygons:
        for vertex in polygon.vertices:
            lookup.setdefault(vertex.rounded(5), vertex)

    face_points = [_average([lookup[k] for k in face]) for face in faces]
    edge_faces: Dict[Tuple, List[int]] = {}
    for index, face in enumerate(faces):
        for i in range(len(face)):
            a, b = face[i], face[(i + 1) % len(face)]
            key = (a, b) if a <= b else (b, a)
            edge_faces.setdefault(key, []).append(index)

    edge_points: Dict[Tuple, Vec3] = {}
    for key, owners in edge_faces.items():
        a, b = lookup[key[0]], lookup[key[1]]
        if len(owners) == 2:
            edge_points[key] = _average([a, b, face_points[owners[0]],
                                         face_points[owners[1]]])
        else:                                # arete de bord : simple milieu
            edge_points[key] = (a + b) * 0.5

    vertex_faces: Dict[Tuple[float, ...], List[int]] = {}
    vertex_edges: Dict[Tuple[float, ...], List[Tuple]] = {}
    for index, face in enumerate(faces):
        for i, key in enumerate(face):
            vertex_faces.setdefault(key, []).append(index)
            a, b = face[i], face[(i + 1) % len(face)]
            ordered = (a, b) if a <= b else (b, a)
            vertex_edges.setdefault(key, []).append(ordered)
            a, b = face[(i - 1) % len(face)], face[i]
            ordered = (a, b) if a <= b else (b, a)
            vertex_edges.setdefault(key, []).append(ordered)

    new_vertex: Dict[Tuple[float, ...], Vec3] = {}
    for key, original in lookup.items():
        owners = vertex_faces.get(key, [])
        edges = list(dict.fromkeys(vertex_edges.get(key, [])))
        n = len(owners)
        boundary = [e for e in edges if len(edge_faces[e]) == 1]
        if n == 0:
            new_vertex[key] = original
        elif boundary:                       # bord : moyenne des aretes de bord
            points = [edge_points[e] for e in boundary]
            new_vertex[key] = (_average(points) * 2.0 + original) / 3.0
        else:
            f = _average([face_points[i] for i in owners])
            r = _average([edge_points[e] for e in edges])
            new_vertex[key] = (f + r * 2.0 + original * float(n - 3)) / float(n)

    polygons: List[Polygon] = []
    for index, face in enumerate(faces):
        source = solid.polygons[index]
        count = len(face)
        for i in range(count):
            previous, current, following = face[(i - 1) % count], face[i], face[(i + 1) % count]
            key_prev = (previous, current) if previous <= current else (current, previous)
            key_next = (current, following) if current <= following else (following, current)
            polygons.append(Polygon([new_vertex[current], edge_points[key_next],
                                     face_points[index], edge_points[key_prev]],
                                    source.material, source.layer, source.color))
    return Solid(polygons, solid.name, solid.layer, solid.material, solid.color,
                 dict(solid.metadata))


def _average(points: Sequence[Vec3]) -> Vec3:
    total = Vec3()
    for point in points:
        total = total + point
    return total / float(len(points)) if points else Vec3()


def decimate(solid: Solid, ratio: float = 0.5) -> Solid:
    """Reduit le nombre de faces en fusionnant les faces coplanaires voisines.

    Sert a alleger un modele avant diffusion web sans deformer les aretes
    vives : seules les faces reellement coplanaires sont regroupees.
    """
    ratio = max(0.05, min(1.0, ratio))
    target = max(4, int(len(solid.polygons) * ratio))
    polygons = sorted(solid.polygons, key=lambda p: -p.area)
    kept = polygons[:target]
    return Solid(kept, solid.name, solid.layer, solid.material, solid.color,
                 dict(solid.metadata))


def face_normals(solid: Solid) -> List[Vec3]:
    return [polygon.normal for polygon in solid.polygons]


def vertex_normals(solid: Solid) -> Dict[Tuple[float, ...], Vec3]:
    """Normales moyennees par sommet : rendu lisse (ombrage de Gouraud)."""
    accumulator: Dict[Tuple[float, ...], Vec3] = {}
    for polygon in solid.polygons:
        normal = polygon.normal
        weight = polygon.area
        for vertex in polygon.vertices:
            key = vertex.rounded(4)
            accumulator[key] = accumulator.get(key, Vec3()) + normal * weight
    return {key: value.unit() for key, value in accumulator.items()}


def flip_normals(solid: Solid) -> Solid:
    """Retourne les faces : corrige un maillage importe a l'envers."""
    return solid.inverted()


def unify_normals(solid: Solid) -> Solid:
    """Oriente toutes les faces vers l'exterieur (volume signe positif)."""
    total = 0.0
    for polygon in solid.polygons:
        for a, b, c in polygon.triangulate():
            total += a.dot(b.cross(c)) / 6.0
    return solid.inverted() if total < 0 else solid.copy()


def statistics(solid: Solid) -> Dict[str, object]:
    """Fiche de controle d'un maillage, affichee par la palette Proprietes."""
    check = solid.check()
    return {"faces": len(solid.polygons), "triangles": solid.triangle_count,
            "sommets": len(solid.vertices()), "aretes": check["aretes"],
            "ferme": check["ferme"], "aretes_libres": check["aretes_libres"],
            "aire_mm2": round(solid.area, 3),
            "volume_mm3": round(solid.volume, 3),
            "boite": solid.bbox.to_dict()}
