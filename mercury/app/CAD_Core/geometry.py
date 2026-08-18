"""Primitives geometriques 2D. Unite : le millimetre.

Aucune dependance : le noyau doit rester portable (serveur, worker, edge).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

EPS = 1e-9


@dataclass(frozen=True)
class Vec2:
    """Point ou vecteur du plan."""

    x: float
    y: float

    def __add__(self, o: "Vec2") -> "Vec2":
        return Vec2(self.x + o.x, self.y + o.y)

    def __sub__(self, o: "Vec2") -> "Vec2":
        return Vec2(self.x - o.x, self.y - o.y)

    def __mul__(self, k: float) -> "Vec2":
        return Vec2(self.x * k, self.y * k)

    def dot(self, o: "Vec2") -> float:
        return self.x * o.x + self.y * o.y

    def cross(self, o: "Vec2") -> float:
        return self.x * o.y - self.y * o.x

    def norm(self) -> float:
        return math.hypot(self.x, self.y)

    def unit(self) -> "Vec2":
        n = self.norm()
        if n < EPS:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / n, self.y / n)

    def perp(self) -> "Vec2":
        return Vec2(-self.y, self.x)

    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass(frozen=True)
class Segment:
    """Segment oriente, brique de tout trace 2D."""

    a: Vec2
    b: Vec2

    @property
    def vec(self) -> Vec2:
        return self.b - self.a

    @property
    def length(self) -> float:
        return self.vec.norm()

    @property
    def direction(self) -> Vec2:
        return self.vec.unit()

    @property
    def midpoint(self) -> Vec2:
        return Vec2((self.a.x + self.b.x) / 2.0, (self.a.y + self.b.y) / 2.0)

    def point_at(self, t: float) -> Vec2:
        return Vec2(self.a.x + self.vec.x * t, self.a.y + self.vec.y * t)

    def distance_to(self, p: Vec2) -> float:
        v = self.vec
        d2 = v.dot(v)
        if d2 < EPS:
            return (p - self.a).norm()
        t = max(0.0, min(1.0, (p - self.a).dot(v) / d2))
        return (p - self.point_at(t)).norm()


def segment_intersection(s1: Segment, s2: Segment, tol: float = 1e-7):
    """Intersection de deux segments, ou None s'ils ne se croisent pas."""
    d1, d2 = s1.vec, s2.vec
    den = d1.cross(d2)
    if abs(den) < EPS:
        return None
    t = (s2.a - s1.a).cross(d2) / den
    u = (s2.a - s1.a).cross(d1) / den
    if -tol <= t <= 1 + tol and -tol <= u <= 1 + tol:
        return s1.point_at(t), t, u
    return None


def polygon_area(points: Sequence[Vec2]) -> float:
    """Aire signee ; positive si le contour tourne dans le sens direct."""
    if len(points) < 3:
        return 0.0
    total = 0.0
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        total += p.cross(q)
    return total / 2.0


def polygon_perimeter(points: Sequence[Vec2]) -> float:
    if len(points) < 2:
        return 0.0
    return sum((points[(i + 1) % len(points)] - p).norm()
               for i, p in enumerate(points))


def polygon_centroid(points: Sequence[Vec2]) -> Vec2:
    area = polygon_area(points)
    if abs(area) < EPS:
        n = max(1, len(points))
        return Vec2(sum(p.x for p in points) / n, sum(p.y for p in points) / n)
    cx = cy = 0.0
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        c = p.cross(q)
        cx += (p.x + q.x) * c
        cy += (p.y + q.y) * c
    return Vec2(cx / (6 * area), cy / (6 * area))


def point_in_polygon(p: Vec2, polygon: Sequence[Vec2]) -> bool:
    inside = False
    n = len(polygon)
    for i in range(n):
        a, b = polygon[i], polygon[(i + 1) % n]
        if (a.y > p.y) != (b.y > p.y):
            x = (b.x - a.x) * (p.y - a.y) / (b.y - a.y + EPS) + a.x
            if p.x < x:
                inside = not inside
    return inside


def bounding_box(points: Iterable[Vec2]) -> Tuple[float, float, float, float]:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    if not xs:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


def offset_polygon(points: Sequence[Vec2], distance: float) -> List[Vec2]:
    """Decale un contour vers l'interieur (distance negative) ou l'exterieur."""
    n = len(points)
    if n < 3:
        return list(points)
    # La normale perp() d'une arete pointe vers l'interieur pour un contour
    # oriente dans le sens direct. Une distance negative doit donc reduire le
    # contour : d'ou le signe inverse ci-dessous.
    sign = 1.0 if polygon_area(points) > 0 else -1.0
    edges: List[Segment] = []
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        shift = (b - a).unit().perp() * (-distance * sign)
        edges.append(Segment(a + shift, b + shift))
    result: List[Vec2] = []
    for i in range(n):
        e1, e2 = edges[i - 1], edges[i]
        den = e1.vec.cross(e2.vec)
        if abs(den) < EPS:
            result.append(points[i])
            continue
        t = (e2.a - e1.a).cross(e2.vec) / den
        result.append(e1.point_at(t))
    return result
