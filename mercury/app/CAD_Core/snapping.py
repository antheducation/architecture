"""Accrochages : ACCROBJ, RESOL, GRILLE, ORTHO, reperage polaire.

Le module rend le point reellement accroche et le mode qui a gagne, ce qui
permet a l'interface d'afficher le marqueur correspondant, exactement comme
la barre d'etat d'AutoCAD.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .math3d import TOL, Vec3
from .profiles import Curve, Profile
from .solid import Solid

# Bits de la variable systeme OSMODE.
OSNAP_MODES = {
    "extremite": 1, "milieu": 2, "centre": 4, "noeud": 8, "quadrant": 16,
    "intersection": 32, "insertion": 64, "perpendiculaire": 128,
    "tangente": 256, "proche": 512, "parallele": 2048,
}


@dataclass
class SnapResult:
    """Point accroche, mode gagnant et distance au curseur."""

    point: Vec3
    mode: str
    distance: float
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"point": [round(v, 4) for v in self.point], "mode": self.mode,
                "distance": round(self.distance, 4), "objet": self.source}


class SnapEngine:
    """Moteur d'accrochage sur une collection d'objets."""

    def __init__(self, aperture: float = 50.0, modes: int = 4133) -> None:
        self.aperture = aperture
        self.modes = modes                 # OSMODE
        self.ortho = False
        self.polar_angle = 45.0
        self.grid_spacing = 100.0
        self.grid_snap = False

    def enabled(self, mode: str) -> bool:
        return bool(self.modes & OSNAP_MODES.get(mode, 0))

    # -- points caracteristiques -------------------------------------------
    @staticmethod
    def candidates(geometry, modes: int) -> List[Tuple[Vec3, str]]:
        """Points remarquables d'un objet, filtres par les modes actifs."""
        out: List[Tuple[Vec3, str]] = []

        def push(point: Vec3, mode: str) -> None:
            if modes & OSNAP_MODES[mode]:
                out.append((point, mode))

        if isinstance(geometry, Solid):
            for vertex in geometry.vertices():
                push(vertex, "extremite")
            for a, b in geometry.edges():
                push((a + b) * 0.5, "milieu")
            for polygon in geometry.polygons:
                push(polygon.centroid, "centre")
            push(geometry.centroid, "insertion")
        elif isinstance(geometry, Curve):
            points = geometry.points
            for point in points:
                push(point, "noeud")
            if points:
                push(points[0], "extremite")
                push(points[-1], "extremite")
            for i in range(len(points) - 1):
                push((points[i] + points[i + 1]) * 0.5, "milieu")
            if geometry.closed and len(points) > 2:
                center = Vec3()
                for point in points:
                    center = center + point
                center = center / float(len(points))
                push(center, "centre")
                for index in (0, len(points) // 4, len(points) // 2,
                              3 * len(points) // 4):
                    if index < len(points):
                        push(points[index], "quadrant")
        elif isinstance(geometry, Profile):
            for ring in geometry.rings():
                for point in ring:
                    push(point, "extremite")
                for i in range(len(ring)):
                    push((ring[i] + ring[(i + 1) % len(ring)]) * 0.5, "milieu")
            push(geometry.centroid, "centre")
        return out

    def nearest_on_edges(self, geometry, cursor: Vec3
                         ) -> Optional[Tuple[Vec3, str]]:
        """Point le plus proche sur une arete : modes Proche et Perpendiculaire."""
        best: Optional[Tuple[float, Vec3]] = None
        segments: List[Tuple[Vec3, Vec3]] = []
        if isinstance(geometry, Solid):
            segments = geometry.edges()
        elif isinstance(geometry, Curve):
            points = geometry.points
            segments = [(points[i], points[i + 1])
                        for i in range(len(points) - 1)]
            if geometry.closed and len(points) > 2:
                segments.append((points[-1], points[0]))
        elif isinstance(geometry, Profile):
            for ring in geometry.rings():
                segments += [(ring[i], ring[(i + 1) % len(ring)])
                             for i in range(len(ring))]
        for a, b in segments:
            edge = b - a
            length = edge.norm()
            if length < TOL:
                continue
            t = max(0.0, min(1.0, (cursor - a).dot(edge) / (length * length)))
            point = a.lerp(b, t)
            distance = point.distance_to(cursor)
            if best is None or distance < best[0]:
                best = (distance, point)
        if best is None:
            return None
        return best[1], "proche"

    # -- accrochage --------------------------------------------------------
    def snap(self, cursor, entities: Sequence, last_point=None
             ) -> Optional[SnapResult]:
        """Renvoie le meilleur accrochage pour la position du curseur."""
        cursor = Vec3.of(cursor)
        if self.ortho and last_point is not None:
            cursor = self._orthogonal(Vec3.of(last_point), cursor)
        best: Optional[SnapResult] = None
        priority = {"extremite": 0, "intersection": 1, "milieu": 2, "centre": 3,
                    "quadrant": 4, "noeud": 5, "insertion": 6,
                    "perpendiculaire": 7, "tangente": 8, "proche": 9}
        for item in entities:
            geometry = getattr(item, "geometry", item)
            source = getattr(item, "handle", "")
            for point, mode in self.candidates(geometry, self.modes):
                distance = point.distance_to(cursor)
                if distance > self.aperture:
                    continue
                candidate = SnapResult(point, mode, distance, source)
                if best is None or (priority[mode], distance) < \
                        (priority[best.mode], best.distance):
                    best = candidate
            if self.enabled("proche"):
                near = self.nearest_on_edges(geometry, cursor)
                if near is not None and near[0].distance_to(cursor) <= self.aperture:
                    candidate = SnapResult(near[0], "proche",
                                           near[0].distance_to(cursor), source)
                    if best is None or (priority["proche"], candidate.distance) < \
                            (priority[best.mode], best.distance):
                        best = candidate
        if best is None and self.grid_snap:
            snapped = self.snap_to_grid(cursor)
            return SnapResult(snapped, "resolution",
                              snapped.distance_to(cursor))
        return best

    def snap_to_grid(self, point) -> Vec3:
        """Commande RESOL : accrochage a la grille."""
        step = max(TOL, self.grid_spacing)
        point = Vec3.of(point)
        return Vec3(round(point.x / step) * step, round(point.y / step) * step,
                    round(point.z / step) * step)

    def _orthogonal(self, base: Vec3, cursor: Vec3) -> Vec3:
        """Mode ORTHO : contraint le deplacement a un axe."""
        delta = cursor - base
        axes = [(abs(delta.x), Vec3(delta.x, 0, 0)),
                (abs(delta.y), Vec3(0, delta.y, 0)),
                (abs(delta.z), Vec3(0, 0, delta.z))]
        axes.sort(key=lambda item: -item[0])
        return base + axes[0][1]

    def polar_track(self, base, cursor) -> Vec3:
        """Reperage polaire : bloque la direction sur un multiple d'angle."""
        base, cursor = Vec3.of(base), Vec3.of(cursor)
        delta = cursor - base
        planar = math.hypot(delta.x, delta.y)
        if planar < TOL:
            return cursor
        step = math.radians(max(1.0, self.polar_angle))
        angle = round(math.atan2(delta.y, delta.x) / step) * step
        return Vec3(base.x + planar * math.cos(angle),
                    base.y + planar * math.sin(angle), cursor.z)

    def intersections(self, entities: Sequence, cursor, radius: Optional[float] = None
                      ) -> List[Vec3]:
        """Mode Intersection : croisements d'aretes proches du curseur."""
        cursor = Vec3.of(cursor)
        radius = radius or self.aperture
        segments: List[Tuple[Vec3, Vec3]] = []
        for item in entities:
            geometry = getattr(item, "geometry", item)
            if isinstance(geometry, Solid):
                segments += geometry.edges()
            elif isinstance(geometry, Curve):
                points = geometry.points
                segments += [(points[i], points[i + 1])
                             for i in range(len(points) - 1)]
        found: List[Vec3] = []
        for i in range(len(segments)):
            for j in range(i + 1, len(segments)):
                point = _segment_intersection(segments[i], segments[j])
                if point is not None and point.distance_to(cursor) <= radius:
                    if all(point.distance_to(other) > 1e-6 for other in found):
                        found.append(point)
        return found

    def to_dict(self) -> Dict[str, Any]:
        return {"osmode": self.modes, "ouverture": self.aperture,
                "ortho": self.ortho, "polaire_deg": self.polar_angle,
                "grille_mm": self.grid_spacing, "resol": self.grid_snap,
                "modes_actifs": [name for name, bit in OSNAP_MODES.items()
                                 if self.modes & bit]}


def _segment_intersection(first: Tuple[Vec3, Vec3], second: Tuple[Vec3, Vec3],
                          tol: float = 1e-4) -> Optional[Vec3]:
    """Point commun a deux segments de l'espace, s'il existe."""
    p, q = first[0], second[0]
    u, v = first[1] - first[0], second[1] - second[0]
    w = p - q
    a, b, c = u.dot(u), u.dot(v), v.dot(v)
    d, e = u.dot(w), v.dot(w)
    denominator = a * c - b * b
    if abs(denominator) < 1e-12:
        return None
    s = (b * e - c * d) / denominator
    t = (a * e - b * d) / denominator
    if not (-tol <= s <= 1 + tol and -tol <= t <= 1 + tol):
        return None
    point_a = p + u * s
    point_b = q + v * t
    if point_a.distance_to(point_b) > tol:
        return None
    return (point_a + point_b) * 0.5
