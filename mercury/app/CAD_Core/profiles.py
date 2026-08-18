"""Contours 2D et courbes 3D : la matiere premiere des outils volumiques.

Un `Profile` est un contour ferme, eventuellement perce, pose dans un plan
de l'espace. C'est ce que consomment EXTRUSION, REVOLUTION, BALAYAGE et
LISSAGE. Une `Curve` est une polyligne 3D ouverte ou fermee : trajectoire
de balayage, helice, arete extraite.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .math3d import (EPS, Mat4, ORIGIN, Plane, TOL, Vec3, X_AXIS, XY_PLANE,
                     Y_AXIS, Z_AXIS, polygon_normal)

DEFAULT_SEGMENTS = 48


def arc_points(center, radius: float, start_angle: float, end_angle: float,
               segments: int = DEFAULT_SEGMENTS, plane: Optional[Plane] = None
               ) -> List[Vec3]:
    """Discretise un arc. Angles en radians, sens trigonometrique."""
    plane = plane or XY_PLANE
    u, v = plane.basis()
    center = Vec3.of(center)
    span = end_angle - start_angle
    count = max(2, int(math.ceil(abs(span) / (2 * math.pi) * segments)) + 1)
    points: List[Vec3] = []
    for i in range(count):
        angle = start_angle + span * i / float(count - 1)
        points.append(center + u * (radius * math.cos(angle))
                      + v * (radius * math.sin(angle)))
    return points


def bulge_arc(start: Vec3, end: Vec3, bulge: float,
              segments: int = 16) -> List[Vec3]:
    """Arc defini par un bulge DXF (tangente du quart de l'angle au centre)."""
    start, end = Vec3.of(start), Vec3.of(end)
    if abs(bulge) < 1e-12:
        return [start, end]
    chord = end - start
    length = chord.norm()
    if length < TOL:
        return [start, end]
    theta = 4.0 * math.atan(bulge)
    radius = length / (2.0 * math.sin(abs(theta) / 2.0))
    normal = Vec3(-chord.y, chord.x, 0.0).unit()
    middle = (start + end) * 0.5
    sagitta = radius - math.sqrt(max(0.0, radius * radius - (length / 2.0) ** 2))
    center = middle + normal * ((radius - sagitta) * (1 if bulge > 0 else -1))
    a0 = math.atan2(start.y - center.y, start.x - center.x)
    a1 = math.atan2(end.y - center.y, end.x - center.x)
    if bulge > 0 and a1 < a0:
        a1 += 2 * math.pi
    if bulge < 0 and a1 > a0:
        a1 -= 2 * math.pi
    return arc_points(center, radius, a0, a1, max(8, segments))


def bezier_points(control: Sequence, segments: int = 32) -> List[Vec3]:
    """Courbe de Bezier de degre quelconque (algorithme de De Casteljau)."""
    pts = [Vec3.of(p) for p in control]
    if len(pts) < 2:
        return list(pts)
    out: List[Vec3] = []
    for i in range(segments + 1):
        t = i / float(segments)
        current = list(pts)
        while len(current) > 1:
            current = [current[k].lerp(current[k + 1], t)
                       for k in range(len(current) - 1)]
        out.append(current[0])
    return out


def spline_points(control: Sequence, segments_per_span: int = 12,
                  closed: bool = False) -> List[Vec3]:
    """Spline de Catmull-Rom : la SPLINE d'AutoCAD passe par ses points."""
    pts = [Vec3.of(p) for p in control]
    if len(pts) < 3:
        return list(pts)
    if closed:
        extended = [pts[-1]] + pts + [pts[0], pts[1]]
    else:
        extended = [pts[0]] + pts + [pts[-1]]
    out: List[Vec3] = []
    for i in range(len(extended) - 3):
        p0, p1, p2, p3 = extended[i:i + 4]
        for s in range(segments_per_span):
            t = s / float(segments_per_span)
            t2, t3 = t * t, t * t * t
            out.append((p1 * 2.0 + (p2 - p0) * t
                        + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * t2
                        + (p1 * 3.0 - p0 - p2 * 3.0 + p3) * t3) * 0.5)
    if not closed:
        out.append(pts[-1])
    return out


@dataclass
class Curve:
    """Polyligne 3D, support des balayages et des aretes extraites."""

    points: List[Vec3] = field(default_factory=list)
    closed: bool = False
    name: str = "courbe"
    layer: str = "0"

    def __post_init__(self) -> None:
        self.points = [Vec3.of(p) for p in self.points]

    @property
    def length(self) -> float:
        total = 0.0
        for i in range(len(self.points) - 1):
            total += self.points[i].distance_to(self.points[i + 1])
        if self.closed and len(self.points) > 2:
            total += self.points[-1].distance_to(self.points[0])
        return total

    @property
    def start(self) -> Vec3:
        return self.points[0] if self.points else ORIGIN

    @property
    def end(self) -> Vec3:
        return self.points[-1] if self.points else ORIGIN

    def resampled(self, count: int) -> "Curve":
        """Reechantillonne a pas constant : indispensable avant un balayage."""
        pts = list(self.points) + ([self.points[0]] if self.closed
                                   and len(self.points) > 2 else [])
        if len(pts) < 2 or count < 2:
            return Curve(list(self.points), self.closed, self.name, self.layer)
        cumulated = [0.0]
        for i in range(1, len(pts)):
            cumulated.append(cumulated[-1] + pts[i - 1].distance_to(pts[i]))
        total = cumulated[-1]
        if total < TOL:
            return Curve(list(self.points), self.closed, self.name, self.layer)
        out: List[Vec3] = []
        index = 0
        for i in range(count):
            target = total * i / float(count - 1)
            while index < len(cumulated) - 2 and cumulated[index + 1] < target:
                index += 1
            span = cumulated[index + 1] - cumulated[index]
            t = 0.0 if span < TOL else (target - cumulated[index]) / span
            out.append(pts[index].lerp(pts[index + 1], t))
        return Curve(out, False, self.name, self.layer)

    def tangents(self) -> List[Vec3]:
        """Tangente unitaire en chaque point."""
        n = len(self.points)
        if n < 2:
            return [Z_AXIS]
        out: List[Vec3] = []
        for i in range(n):
            if i == 0:
                t = self.points[1] - self.points[0]
            elif i == n - 1:
                t = self.points[-1] - self.points[-2]
            else:
                t = self.points[i + 1] - self.points[i - 1]
            if t.norm() < TOL:
                t = Z_AXIS
            out.append(t.unit())
        return out

    def transformed(self, matrix: Mat4) -> "Curve":
        return Curve([matrix.apply(p) for p in self.points], self.closed,
                     self.name, self.layer)

    def reversed_curve(self) -> "Curve":
        return Curve(list(reversed(self.points)), self.closed, self.name,
                     self.layer)

    def to_dict(self) -> Dict[str, object]:
        return {"nom": self.name, "points": len(self.points),
                "ferme": self.closed, "longueur_mm": round(self.length, 3)}

    @staticmethod
    def line(a, b) -> "Curve":
        return Curve([Vec3.of(a), Vec3.of(b)], False, "ligne")

    @staticmethod
    def polyline(points, closed: bool = False) -> "Curve":
        return Curve([Vec3.of(p) for p in points], closed, "polyligne")

    @staticmethod
    def arc(center, radius: float, start_angle: float, end_angle: float,
            plane: Optional[Plane] = None, segments: int = DEFAULT_SEGMENTS
            ) -> "Curve":
        return Curve(arc_points(center, radius, start_angle, end_angle,
                                segments, plane), False, "arc")

    @staticmethod
    def circle(center, radius: float, plane: Optional[Plane] = None,
               segments: int = DEFAULT_SEGMENTS) -> "Curve":
        points = arc_points(center, radius, 0.0, 2 * math.pi, segments, plane)
        return Curve(points[:-1], True, "cercle")

    @staticmethod
    def spline(control, segments_per_span: int = 12,
               closed: bool = False) -> "Curve":
        return Curve(spline_points(control, segments_per_span, closed), closed,
                     "spline")

    @staticmethod
    def helix(center=ORIGIN, base_radius: float = 100.0,
              top_radius: Optional[float] = None, height: float = 200.0,
              turns: float = 3.0, clockwise: bool = False,
              segments_per_turn: int = 36) -> "Curve":
        """Commande HELICE : ressort, rampe, filetage, escalier helicoidal."""
        center = Vec3.of(center)
        top_radius = base_radius if top_radius is None else top_radius
        steps = max(4, int(round(abs(turns) * segments_per_turn)))
        sign = -1.0 if clockwise else 1.0
        points: List[Vec3] = []
        for i in range(steps + 1):
            t = i / float(steps)
            angle = sign * 2 * math.pi * turns * t
            radius = base_radius + (top_radius - base_radius) * t
            points.append(Vec3(center.x + radius * math.cos(angle),
                               center.y + radius * math.sin(angle),
                               center.z + height * t))
        return Curve(points, False, "helice")


@dataclass
class Profile:
    """Contour ferme dans un plan, avec ses eventuelles ouvertures."""

    outline: List[Vec3] = field(default_factory=list)
    holes: List[List[Vec3]] = field(default_factory=list)
    name: str = "profil"
    layer: str = "0"

    def __post_init__(self) -> None:
        self.outline = [Vec3.of(p) for p in self.outline]
        self.holes = [[Vec3.of(p) for p in hole] for hole in self.holes]
        if len(self.outline) >= 2 and \
                self.outline[0].distance_to(self.outline[-1]) < TOL:
            self.outline.pop()
        for hole in self.holes:
            if len(hole) >= 2 and hole[0].distance_to(hole[-1]) < TOL:
                hole.pop()

    @property
    def plane(self) -> Plane:
        if len(self.outline) < 3:
            return XY_PLANE
        try:
            return Plane.from_point_normal(self.outline[0], self.normal)
        except ValueError:
            return XY_PLANE

    @property
    def normal(self) -> Vec3:
        normal = polygon_normal(self.outline)
        return normal if normal.norm() > EPS else Z_AXIS

    @property
    def area(self) -> float:
        """Aire nette, ouvertures deduites."""
        from .math3d import polygon_area_3d
        total = polygon_area_3d(self.outline)
        for hole in self.holes:
            total -= polygon_area_3d(hole)
        return max(0.0, total)

    @property
    def perimeter(self) -> float:
        def ring_length(ring: Sequence[Vec3]) -> float:
            return sum(ring[i].distance_to(ring[(i + 1) % len(ring)])
                       for i in range(len(ring))) if len(ring) > 1 else 0.0
        return ring_length(self.outline) + sum(ring_length(h) for h in self.holes)

    @property
    def centroid(self) -> Vec3:
        if not self.outline:
            return ORIGIN
        total = Vec3()
        for p in self.outline:
            total = total + p
        return total / float(len(self.outline))

    def oriented(self, normal: Optional[Vec3] = None) -> "Profile":
        """Retourne le contour pour que sa normale suive la reference."""
        reference = Vec3.of(normal) if normal is not None else self.normal
        outline = list(self.outline)
        if polygon_normal(outline).dot(reference) < 0:
            outline.reverse()
        holes = []
        for hole in self.holes:
            ring = list(hole)
            if polygon_normal(ring).dot(reference) > 0:
                ring.reverse()
            holes.append(ring)
        return Profile(outline, holes, self.name, self.layer)

    def transformed(self, matrix: Mat4) -> "Profile":
        return Profile([matrix.apply(p) for p in self.outline],
                       [[matrix.apply(p) for p in hole] for hole in self.holes],
                       self.name, self.layer)

    def translated(self, vector) -> "Profile":
        return self.transformed(Mat4.translation(vector))

    def with_hole(self, hole) -> "Profile":
        return Profile(list(self.outline), self.holes + [[Vec3.of(p) for p in hole]],
                       self.name, self.layer)

    def rings(self) -> List[List[Vec3]]:
        return [self.outline] + self.holes

    def triangulate(self) -> List[Tuple[Vec3, Vec3, Vec3]]:
        """Triangule le contour perce en fusionnant les ouvertures (pont)."""
        from .solid import _ear_clip
        if not self.holes:
            return [tuple(t) for t in _ear_clip(self.outline)]
        merged = _merge_holes(self.outline, self.holes, self.normal)
        return [tuple(t) for t in _ear_clip(merged)]

    def to_curve(self) -> Curve:
        return Curve(list(self.outline), True, self.name, self.layer)

    def to_dict(self) -> Dict[str, object]:
        return {"nom": self.name, "sommets": len(self.outline),
                "ouvertures": len(self.holes), "aire_mm2": round(self.area, 3),
                "perimetre_mm": round(self.perimeter, 3)}

    # -- fabriques ---------------------------------------------------------
    @staticmethod
    def rectangle(width: float, depth: float, origin=ORIGIN,
                  plane: Optional[Plane] = None, centered: bool = False
                  ) -> "Profile":
        plane = plane or XY_PLANE
        u, v = plane.basis()
        base = Vec3.of(origin)
        if centered:
            base = base - u * (width / 2.0) - v * (depth / 2.0)
        return Profile([base, base + u * width, base + u * width + v * depth,
                        base + v * depth], name="rectangle")

    @staticmethod
    def circle(radius: float, center=ORIGIN, plane: Optional[Plane] = None,
               segments: int = DEFAULT_SEGMENTS) -> "Profile":
        points = arc_points(center, radius, 0.0, 2 * math.pi, segments, plane)
        return Profile(points[:-1], name="cercle")

    @staticmethod
    def ellipse(radius_x: float, radius_y: float, center=ORIGIN,
                plane: Optional[Plane] = None, segments: int = DEFAULT_SEGMENTS
                ) -> "Profile":
        plane = plane or XY_PLANE
        u, v = plane.basis()
        center = Vec3.of(center)
        points = []
        for i in range(segments):
            angle = 2 * math.pi * i / float(segments)
            points.append(center + u * (radius_x * math.cos(angle))
                          + v * (radius_y * math.sin(angle)))
        return Profile(points, name="ellipse")

    @staticmethod
    def regular_polygon(sides: int, radius: float, center=ORIGIN,
                        plane: Optional[Plane] = None,
                        inscribed: bool = True) -> "Profile":
        """Commande POLYGONE : de 3 a 1024 cotes, inscrit ou circonscrit."""
        if sides < 3:
            raise ValueError("un polygone exige au moins 3 cotes")
        plane = plane or XY_PLANE
        u, v = plane.basis()
        center = Vec3.of(center)
        r = radius if inscribed else radius / math.cos(math.pi / sides)
        points = []
        for i in range(sides):
            angle = 2 * math.pi * i / float(sides) + math.pi / 2.0
            points.append(center + u * (r * math.cos(angle))
                          + v * (r * math.sin(angle)))
        return Profile(points, name="polygone%d" % sides)

    @staticmethod
    def polyline(points, holes: Optional[Sequence] = None,
                 name: str = "contour") -> "Profile":
        return Profile([Vec3.of(p) for p in points],
                       [[Vec3.of(p) for p in hole] for hole in (holes or [])],
                       name=name)

    @staticmethod
    def from_2d(points, elevation: float = 0.0, holes=None) -> "Profile":
        """Contour donne en coordonnees planes (x, y), pose a une altitude."""
        def lift(seq):
            out = []
            for p in seq:
                values = list(p)
                out.append(Vec3(float(values[0]), float(values[1]),
                                float(values[2]) if len(values) > 2 else elevation))
            return out
        return Profile(lift(points), [lift(h) for h in (holes or [])])

    @staticmethod
    def rounded_rectangle(width: float, depth: float, radius: float,
                          origin=ORIGIN, segments: int = 8) -> "Profile":
        """Rectangle a angles arrondis : RECTANG avec option Raccord."""
        radius = max(0.0, min(radius, min(width, depth) / 2.0))
        o = Vec3.of(origin)
        if radius < TOL:
            return Profile.rectangle(width, depth, o)
        corners = [(o + Vec3(width - radius, radius, 0.0), -math.pi / 2, 0.0),
                   (o + Vec3(width - radius, depth - radius, 0.0), 0.0, math.pi / 2),
                   (o + Vec3(radius, depth - radius, 0.0), math.pi / 2, math.pi),
                   (o + Vec3(radius, radius, 0.0), math.pi, 3 * math.pi / 2)]
        points: List[Vec3] = []
        for center, a0, a1 in corners:
            points.extend(arc_points(center, radius, a0, a1, segments * 4))
        return Profile(points, name="rectangle_arrondi")


def _merge_holes(outline: Sequence[Vec3], holes: Sequence[Sequence[Vec3]],
                 normal: Vec3) -> List[Vec3]:
    """Relie chaque ouverture au contour par un pont : contour simple equivalent."""
    merged = list(outline)
    remaining = [list(h) for h in holes if len(h) >= 3]
    for hole in remaining:
        if polygon_normal(hole).dot(normal) > 0:
            hole.reverse()
        best = None
        for i, outer in enumerate(merged):
            for j, inner in enumerate(hole):
                distance = outer.distance_to(inner)
                if best is None or distance < best[0]:
                    best = (distance, i, j)
        if best is None:
            continue
        _, i, j = best
        bridge = hole[j:] + hole[:j] + [hole[j]]
        merged = merged[:i + 1] + bridge + merged[i:]
    return merged
