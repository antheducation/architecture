"""Moteur 2D : murs, ouvertures, extraction des pieces (livrable #16).

L'extraction des pieces repose sur un arrangement planaire : les axes de
murs sont decoupes a leurs intersections, les sommets voisins fusionnes,
les brins pendants elagues, puis les demi-aretes parcourues pour obtenir
les faces minimales. Aucune heuristique de remplissage.
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Set, Tuple

from .geometry import (
    Segment,
    Vec2,
    offset_polygon,
    polygon_area,
    polygon_centroid,
    polygon_perimeter,
    segment_intersection,
)


class Engine2D:
    """Operations 2D de haut niveau utilisees par l'API et les tests."""

    def __init__(self, snap: float = 120.0) -> None:
        if snap <= 0:
            raise ValueError("la tolerance de fusion doit etre strictement positive")
        self.snap = snap

    # -- decoupe -----------------------------------------------------------
    def split_at_intersections(self, segments: Sequence[Segment]) -> List[Segment]:
        cuts: List[List[float]] = [[0.0, 1.0] for _ in segments]
        for i in range(len(segments)):
            for j in range(i + 1, len(segments)):
                hit = segment_intersection(segments[i], segments[j])
                if hit is None:
                    continue
                _, t, u = hit
                if 1e-6 < t < 1 - 1e-6:
                    cuts[i].append(t)
                if 1e-6 < u < 1 - 1e-6:
                    cuts[j].append(u)
        out: List[Segment] = []
        for seg, ts in zip(segments, cuts):
            ordered = sorted(set(round(t, 9) for t in ts))
            for t0, t1 in zip(ordered, ordered[1:]):
                a, b = seg.point_at(t0), seg.point_at(t1)
                if (b - a).norm() > 1.0:
                    out.append(Segment(a, b))
        return out

    # -- graphe planaire ---------------------------------------------------
    def _build_graph(self, segments: Sequence[Segment]):
        nodes: List[Vec2] = []
        index: Dict[Tuple[int, int], int] = {}

        def node_id(p: Vec2) -> int:
            key = (int(round(p.x / self.snap)), int(round(p.y / self.snap)))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    found = index.get((key[0] + dx, key[1] + dy))
                    if found is not None and (nodes[found] - p).norm() <= self.snap:
                        return found
            nodes.append(p)
            index[key] = len(nodes) - 1
            return len(nodes) - 1

        edges: Set[Tuple[int, int]] = set()
        for seg in segments:
            a, b = node_id(seg.a), node_id(seg.b)
            if a != b:
                edges.add((min(a, b), max(a, b)))
        return nodes, edges

    @staticmethod
    def _prune(edges: Set[Tuple[int, int]], rounds: int = 60) -> Set[Tuple[int, int]]:
        for _ in range(rounds):
            degree: Dict[int, int] = {}
            for a, b in edges:
                degree[a] = degree.get(a, 0) + 1
                degree[b] = degree.get(b, 0) + 1
            dangling = {n for n, d in degree.items() if d <= 1}
            if not dangling:
                break
            edges = {e for e in edges if e[0] not in dangling and e[1] not in dangling}
        return edges

    def detect_rooms(self, walls: Sequence["object"],
                     min_area_m2: float = 1.5) -> List[List[Vec2]]:
        """Renvoie les contours fermes formes par les axes de murs."""
        axes = [Segment(Vec2(*w.start), Vec2(*w.end)) for w in walls]
        pieces = self.split_at_intersections(axes)
        nodes, edges = self._build_graph(pieces)
        edges = self._prune(edges)

        adjacency: Dict[int, List[int]] = {}
        for a, b in edges:
            adjacency.setdefault(a, []).append(b)
            adjacency.setdefault(b, []).append(a)
        for node, neighbours in adjacency.items():
            neighbours.sort(key=lambda m: (nodes[m] - nodes[node]).perp().dot(
                Vec2(1, 0)) * 0 + _angle(nodes[node], nodes[m]))

        visited: Set[Tuple[int, int]] = set()
        faces: List[List[Vec2]] = []
        for start, neighbours in adjacency.items():
            for first in neighbours:
                if (start, first) in visited:
                    continue
                cycle: List[int] = []
                u, v = start, first
                for _ in range(4096):
                    visited.add((u, v))
                    cycle.append(u)
                    ring = adjacency[v]
                    position = ring.index(u)
                    w = ring[(position - 1) % len(ring)]
                    u, v = v, w
                    if (u, v) == (start, first):
                        break
                    if (u, v) in visited:
                        cycle = []
                        break
                if len(cycle) < 3:
                    continue
                polygon = [nodes[i] for i in cycle]
                if polygon_area(polygon) > min_area_m2 * 1e6:
                    faces.append(polygon)

        unique: List[List[Vec2]] = []
        seen: Set[Tuple[int, int]] = set()
        for face in sorted(faces, key=polygon_area):
            c = polygon_centroid(face)
            key = (int(c.x / 250), int(c.y / 250))
            if key in seen:
                continue
            seen.add(key)
            unique.append(face)
        return unique

    # -- mesures -----------------------------------------------------------
    @staticmethod
    def room_metrics(polygon: Sequence[Vec2], wall_thickness: float = 100.0):
        """Surface utile, perimetre et centre, epaisseur des murs deduite."""
        inner = offset_polygon(polygon, -wall_thickness / 2.0)
        if abs(polygon_area(inner)) < 1e5:
            inner = list(polygon)
        centroid = polygon_centroid(inner)
        return {
            "outline": [p.as_tuple() for p in inner],
            "area_m2": round(abs(polygon_area(inner)) / 1e6, 2),
            "perimeter_m": round(polygon_perimeter(inner) / 1000.0, 2),
            "centroid": centroid.as_tuple(),
        }


def _angle(origin: Vec2, other: Vec2) -> float:
    import math
    return math.atan2(other.y - origin.y, other.x - origin.x)
