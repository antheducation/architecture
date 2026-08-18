"""Solides de type B-rep facettise et operations booleennes (CSG).

Le noyau manipule des solides fermes decrits par des polygones plans. Les
operations booleennes UNION, SOUSTRACTION et INTERSECTION reposent sur un
arbre BSP : c'est la methode retenue par la plupart des modeleurs
facettises parce qu'elle est exacte sur les cas plans et robuste sur les
maillages fermes, sans dependance externe.

Unite : le millimetre, comme le reste du projet.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .math3d import (BBox3, EPS, Mat4, ORIGIN, Plane, TOL, Vec3,
                     polygon_area_3d, polygon_normal)

COPLANAR, FRONT, BACK, SPANNING = 0, 1, 2, 3
SPLIT_EPS = 1e-6


@dataclass
class Polygon:
    """Face plane orientee, definie par ses sommets en sens trigonometrique."""

    vertices: List[Vec3]
    material: str = "default"
    layer: str = "0"
    color: int = 256                      # 256 = DUCALQUE, comme en DXF
    _plane: Optional[Plane] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.vertices = [Vec3.of(v) for v in self.vertices]
        self._plane = None

    @property
    def plane(self) -> Plane:
        """Plan porteur, calcule une fois : le BSP l'interroge sans arret."""
        if self._plane is None:
            normal = polygon_normal(self.vertices)
            if normal.norm() < EPS:
                normal = Vec3(0.0, 0.0, 1.0)
            self._plane = Plane(normal, normal.dot(self.vertices[0]))
        return self._plane

    @property
    def normal(self) -> Vec3:
        return self.plane.normal

    @property
    def area(self) -> float:
        return polygon_area_3d(self.vertices)

    @property
    def centroid(self) -> Vec3:
        total = Vec3()
        for v in self.vertices:
            total = total + v
        return total / float(len(self.vertices))

    def flipped(self) -> "Polygon":
        return replace(self, vertices=list(reversed(self.vertices)))

    def transformed(self, matrix: Mat4) -> "Polygon":
        points = [matrix.apply(v) for v in self.vertices]
        if matrix.is_mirroring():
            points.reverse()
        return replace(self, vertices=points)

    def is_degenerate(self, tol: float = 1e-9) -> bool:
        return len(self.vertices) < 3 or self.area < tol

    def triangulate(self) -> List[Tuple[Vec3, Vec3, Vec3]]:
        """Decoupe en triangles par oreilles : gere les contours concaves."""
        return [tuple(t) for t in _ear_clip(self.vertices)]

    def to_dict(self) -> Dict[str, object]:
        return {"sommets": [list(v) for v in self.vertices],
                "materiau": self.material, "calque": self.layer}


def _ear_clip(points: Sequence[Vec3]) -> List[List[Vec3]]:
    """Triangulation par oreilles d'un polygone plan quelconque."""
    pts = [Vec3.of(p) for p in points]
    if len(pts) < 3:
        return []
    if len(pts) == 3:
        return [list(pts)]
    normal = polygon_normal(pts)
    if normal.norm() < EPS:
        return []
    u = normal.any_perpendicular()
    v = normal.cross(u).unit()
    flat = [(p.dot(u), p.dot(v)) for p in pts]

    def area2(poly):
        s = 0.0
        for i in range(len(poly)):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % len(poly)]
            s += x0 * y1 - x1 * y0
        return s / 2.0

    index = list(range(len(pts)))
    if area2(flat) < 0:
        index.reverse()

    def cross2(o, a, b):
        return ((flat[a][0] - flat[o][0]) * (flat[b][1] - flat[o][1])
                - (flat[a][1] - flat[o][1]) * (flat[b][0] - flat[o][0]))

    def inside(a, b, c, p) -> bool:
        # Un sommet confondu avec un coin du triangle ne le bloque pas : les
        # ponts creuses pour raccorder une ouverture dupliquent des sommets.
        for corner in (a, b, c):
            if (abs(flat[p][0] - flat[corner][0]) < 1e-9
                    and abs(flat[p][1] - flat[corner][1]) < 1e-9):
                return False
        d1 = cross2(a, b, p)
        d2 = cross2(b, c, p)
        d3 = cross2(c, a, p)
        return (d1 >= -1e-12 and d2 >= -1e-12 and d3 >= -1e-12)

    triangles: List[List[Vec3]] = []
    guard = 0
    while len(index) > 3 and guard < 4 * len(pts) + 16:
        guard += 1
        clipped = False
        for i in range(len(index)):
            a = index[(i - 1) % len(index)]
            b = index[i]
            c = index[(i + 1) % len(index)]
            if cross2(a, b, c) <= 1e-12:
                continue
            if any(inside(a, b, c, index[k]) for k in range(len(index))
                   if index[k] not in (a, b, c)):
                continue
            triangles.append([pts[a], pts[b], pts[c]])
            index.pop(i)
            clipped = True
            guard = 0
            break
        if not clipped:                      # contour degenere : eventail
            break
    if len(index) == 3:
        triangles.append([pts[index[0]], pts[index[1]], pts[index[2]]])
    elif len(index) > 3:
        for i in range(1, len(index) - 1):
            triangles.append([pts[index[0]], pts[index[i]], pts[index[i + 1]]])
    return triangles


def split_polygon(polygon: Polygon, plane: Plane,
                  coplanar_front: List[Polygon], coplanar_back: List[Polygon],
                  front: List[Polygon], back: List[Polygon]) -> None:
    """Repartit un polygone de part et d'autre d'un plan (algorithme BSP)."""
    types: List[int] = []
    polygon_type = 0
    nx, ny, nz, offset = (plane.normal.x, plane.normal.y, plane.normal.z,
                          plane.offset)
    for vertex in polygon.vertices:
        distance = nx * vertex.x + ny * vertex.y + nz * vertex.z - offset
        kind = (BACK if distance < -SPLIT_EPS
                else FRONT if distance > SPLIT_EPS else COPLANAR)
        polygon_type |= kind
        types.append(kind)

    if polygon_type == COPLANAR:
        target = (coplanar_front if plane.normal.dot(polygon.normal) > 0
                  else coplanar_back)
        target.append(polygon)
    elif polygon_type == FRONT:
        front.append(polygon)
    elif polygon_type == BACK:
        back.append(polygon)
    else:
        front_points: List[Vec3] = []
        back_points: List[Vec3] = []
        count = len(polygon.vertices)
        for i in range(count):
            j = (i + 1) % count
            ti, tj = types[i], types[j]
            vi, vj = polygon.vertices[i], polygon.vertices[j]
            if ti != BACK:
                front_points.append(vi)
            if ti != FRONT:
                back_points.append(vi)
            if (ti | tj) == SPANNING:
                di = plane.signed_distance(vi)
                dj = plane.signed_distance(vj)
                t = di / (di - dj)
                cut = vi.lerp(vj, t)
                front_points.append(cut)
                back_points.append(cut)
        if len(front_points) >= 3:
            piece = replace(polygon, vertices=front_points)
            if not piece.is_degenerate():
                front.append(piece)
        if len(back_points) >= 3:
            piece = replace(polygon, vertices=back_points)
            if not piece.is_degenerate():
                back.append(piece)


class BSPNode:
    """Noeud d'arbre BSP servant de support aux operations booleennes.

    Deux choix rendent l'arbre utilisable sur des maillages reels : le plan
    de separation est choisi parmi plusieurs candidats pour equilibrer
    l'arbre, et tous les parcours sont iteratifs. Un arbre construit
    naivement sur une sphere degenere en liste chainee et fait exploser la
    pile bien avant la fin du calcul.
    """

    __slots__ = ("plane", "front", "back", "polygons")

    CANDIDATES = 5
    MAX_EXPANSIONS = 200000

    def __init__(self, polygons: Optional[List[Polygon]] = None) -> None:
        self.plane: Optional[Plane] = None
        self.front: Optional["BSPNode"] = None
        self.back: Optional["BSPNode"] = None
        self.polygons: List[Polygon] = []
        if polygons:
            self.build(polygons)

    # -- parcours iteratifs -------------------------------------------------
    def _nodes(self) -> List["BSPNode"]:
        stack = [self]
        seen: List["BSPNode"] = []
        while stack:
            node = stack.pop()
            seen.append(node)
            if node.front is not None:
                stack.append(node.front)
            if node.back is not None:
                stack.append(node.back)
        return seen

    def invert(self) -> None:
        for node in self._nodes():
            node.polygons = [p.flipped() for p in node.polygons]
            if node.plane is not None:
                node.plane = node.plane.flipped()
            node.front, node.back = node.back, node.front

    def clip_polygons(self, polygons: List[Polygon]) -> List[Polygon]:
        result: List[Polygon] = []
        work: List[Tuple["BSPNode", List[Polygon]]] = [(self, list(polygons))]
        while work:
            node, items = work.pop()
            if not items:
                continue
            if node.plane is None:
                result.extend(items)
                continue
            front: List[Polygon] = []
            back: List[Polygon] = []
            for polygon in items:
                split_polygon(polygon, node.plane, front, back, front, back)
            if node.front is not None:
                if front:
                    work.append((node.front, front))
            else:
                result.extend(front)
            if node.back is not None and back:
                work.append((node.back, back))
        return result

    def clip_to(self, other: "BSPNode") -> None:
        for node in self._nodes():
            node.polygons = other.clip_polygons(node.polygons)

    def all_polygons(self) -> List[Polygon]:
        out: List[Polygon] = []
        for node in self._nodes():
            out.extend(node.polygons)
        return out

    # -- construction -------------------------------------------------------
    @staticmethod
    def _pick_index(polygons: List[Polygon]) -> int:
        """Face dont le plan equilibre le mieux l'arbre et coupe le moins."""
        count = len(polygons)
        if count <= 4:
            return 0
        step = max(1, count // BSPNode.CANDIDATES)
        best_index, best_score = 0, None
        for index in range(0, count, step):
            plane = polygons[index].plane
            nx, ny, nz = plane.normal.x, plane.normal.y, plane.normal.z
            offset = plane.offset
            front = back = spanning = 0
            for polygon in polygons:
                side = 0
                for vertex in polygon.vertices:
                    distance = (nx * vertex.x + ny * vertex.y + nz * vertex.z
                                - offset)
                    if distance > SPLIT_EPS:
                        side |= FRONT
                    elif distance < -SPLIT_EPS:
                        side |= BACK
                    if side == SPANNING:
                        break
                if side == SPANNING:
                    spanning += 1
                elif side == FRONT:
                    front += 1
                elif side == BACK:
                    back += 1
            score = abs(front - back) + 8 * spanning
            if best_score is None or score < best_score:
                best_score, best_index = score, index
        return best_index

    def build(self, polygons: List[Polygon]) -> None:
        """Construit l'arbre par une boucle explicite.

        La face qui fournit le plan est retiree du lot avant la repartition :
        chaque niveau consomme donc au moins une face. Sans cette garantie,
        une facette en sliver dont la normale est instable se redecoupe
        indefiniment en elle-meme et la construction ne se termine jamais.
        """
        work: List[Tuple["BSPNode", List[Polygon]]] = [
            (self, [p for p in polygons if not p.is_degenerate()])]
        expansions = 0
        while work:
            expansions += 1
            if expansions > BSPNode.MAX_EXPANSIONS:
                raise ValueError(
                    "arbre BSP hors limites (%d noeuds) : geometrie trop "
                    "degradee pour une operation booleenne fiable"
                    % expansions)
            node, items = work.pop()
            if not items:
                continue
            if node.plane is None:
                seed = items.pop(BSPNode._pick_index(items))
                node.plane = seed.plane
                node.polygons.append(seed)
            front: List[Polygon] = []
            back: List[Polygon] = []
            for polygon in items:
                split_polygon(polygon, node.plane, node.polygons, node.polygons,
                              front, back)
            if front:
                if node.front is None:
                    node.front = BSPNode()
                work.append((node.front, front))
            if back:
                if node.back is None:
                    node.back = BSPNode()
                work.append((node.back, back))


@dataclass
class Solid:
    """Solide facettise : un ensemble de polygones fermant un volume."""

    polygons: List[Polygon] = field(default_factory=list)
    name: str = "solide"
    layer: str = "0"
    material: str = "default"
    color: int = 256
    metadata: Dict[str, object] = field(default_factory=dict)

    # -- construction ------------------------------------------------------
    @staticmethod
    def from_polygons(polygons: Iterable, **kwargs) -> "Solid":
        items: List[Polygon] = []
        for polygon in polygons:
            if isinstance(polygon, Polygon):
                items.append(polygon)
            else:
                items.append(Polygon(list(polygon)))
        solid = Solid(items, **kwargs)
        solid.apply_appearance()
        return solid

    @staticmethod
    def from_triangles(triangles: Iterable, **kwargs) -> "Solid":
        return Solid.from_polygons([Polygon(list(t)) for t in triangles], **kwargs)

    def apply_appearance(self) -> "Solid":
        """Propage calque, materiau et couleur du solide vers ses faces."""
        for polygon in self.polygons:
            if polygon.material == "default":
                polygon.material = self.material
            if polygon.layer == "0":
                polygon.layer = self.layer
            if polygon.color == 256:
                polygon.color = self.color
        return self

    def copy(self, name: Optional[str] = None) -> "Solid":
        return Solid([replace(p, vertices=list(p.vertices)) for p in self.polygons],
                     name or self.name, self.layer, self.material, self.color,
                     dict(self.metadata))

    # -- transformations ---------------------------------------------------
    def transformed(self, matrix: Mat4, name: Optional[str] = None) -> "Solid":
        return Solid([p.transformed(matrix) for p in self.polygons],
                     name or self.name, self.layer, self.material, self.color,
                     dict(self.metadata))

    def translated(self, vector) -> "Solid":
        return self.transformed(Mat4.translation(vector))

    def rotated(self, axis, angle: float, base=ORIGIN) -> "Solid":
        return self.transformed(Mat4.rotation(axis, angle, base))

    def scaled(self, factor, base=ORIGIN) -> "Solid":
        return self.transformed(Mat4.scaling(factor, base))

    def mirrored(self, plane: Plane) -> "Solid":
        return self.transformed(Mat4.mirror(plane))

    def inverted(self) -> "Solid":
        """Retourne toutes les faces : le dedans devient le dehors."""
        return Solid([p.flipped() for p in self.polygons], self.name, self.layer,
                     self.material, self.color, dict(self.metadata))

    # -- operations booleennes --------------------------------------------
    def union(self, other: "Solid", name: Optional[str] = None) -> "Solid":
        """Commande UNION."""
        if not self.polygons:
            return other.copy(name)
        if not other.polygons:
            return self.copy(name)
        a, b = BSPNode(self._clone_polygons()), BSPNode(other._clone_polygons())
        a.clip_to(b)
        b.clip_to(a)
        b.invert()
        b.clip_to(a)
        b.invert()
        a.build(b.all_polygons())
        return self._result(a.all_polygons(), name or "%s_union" % self.name)

    def subtract(self, other: "Solid", name: Optional[str] = None) -> "Solid":
        """Commande SOUSTRACTION."""
        if not self.polygons or not other.polygons:
            return self.copy(name)
        a, b = BSPNode(self._clone_polygons()), BSPNode(other._clone_polygons())
        a.invert()
        a.clip_to(b)
        b.clip_to(a)
        b.invert()
        b.clip_to(a)
        b.invert()
        a.build(b.all_polygons())
        a.invert()
        return self._result(a.all_polygons(), name or "%s_moins" % self.name)

    def intersect(self, other: "Solid", name: Optional[str] = None) -> "Solid":
        """Commande INTERSECTION."""
        if not self.polygons or not other.polygons:
            return self._result([], name or "%s_inter" % self.name)
        a, b = BSPNode(self._clone_polygons()), BSPNode(other._clone_polygons())
        a.invert()
        b.clip_to(a)
        b.invert()
        a.clip_to(b)
        b.clip_to(a)
        a.build(b.all_polygons())
        a.invert()
        return self._result(a.all_polygons(), name or "%s_inter" % self.name)

    def _clone_polygons(self) -> List[Polygon]:
        return [replace(p, vertices=list(p.vertices)) for p in self.polygons]

    def _result(self, polygons: List[Polygon], name: str) -> "Solid":
        clean = [p for p in polygons if not p.is_degenerate(1e-7)]
        raw = Solid(clean, name, self.layer, self.material, self.color,
                    dict(self.metadata))
        # Le BSP laisse des jonctions en T : on les resout tout de suite pour
        # que le resultat reste exportable en STL, 3MF ou STEP.
        return raw.heal()

    # -- reparation --------------------------------------------------------
    def heal(self, tol: float = 1e-4) -> "Solid":
        """Repare le maillage : sommets fusionnes et jonctions en T resolues.

        Une operation booleenne BSP decoupe un polygone sans decouper son
        voisin : il reste des sommets poses au milieu d'une arete (jonction
        en T). Le solide est geometriquement juste mais n'est plus manifold,
        ce qui gene les exports STL, 3MF ou STEP. Cette passe insere les
        sommets manquants et supprime les faces degenerees.
        """
        if not self.polygons:
            return self.copy()
        snapped: List[Polygon] = []
        digits = max(0, int(round(-math.log10(tol))))
        for polygon in self.polygons:
            points: List[Vec3] = []
            for vertex in polygon.vertices:
                rounded = Vec3(round(vertex.x, digits), round(vertex.y, digits),
                               round(vertex.z, digits))
                if not points or points[-1].distance_to(rounded) > tol:
                    points.append(rounded)
            if len(points) >= 3 and points[0].distance_to(points[-1]) <= tol:
                points.pop()
            if len(points) >= 3:
                snapped.append(replace(polygon, vertices=points))

        box = BBox3.of(v for p in snapped for v in p.vertices)
        cell = max(tol * 10.0, box.diagonal / 64.0, 1e-3)
        grid: Dict[Tuple[int, int, int], List[Vec3]] = {}

        def cell_of(point: Vec3) -> Tuple[int, int, int]:
            return (int(math.floor(point.x / cell)),
                    int(math.floor(point.y / cell)),
                    int(math.floor(point.z / cell)))

        for polygon in snapped:
            for vertex in polygon.vertices:
                bucket = grid.setdefault(cell_of(vertex), [])
                if all(vertex.distance_to(v) > tol for v in bucket):
                    bucket.append(vertex)

        def candidates(a: Vec3, b: Vec3) -> List[Vec3]:
            """Sommets proches du segment [a, b].

            La grille est parcourue en marchant le long du segment plutot
            qu'en balayant sa boite englobante : le cout reste proportionnel
            a la longueur de l'arete, meme sur un modele de plusieurs metres.
            """
            length = (b - a).norm()
            steps = int(length / cell) + 2
            visited = set()
            out: List[Vec3] = []
            for s in range(steps + 1):
                sample = a.lerp(b, min(1.0, s / float(steps)))
                cx, cy, cz = cell_of(sample)
                for i in (-1, 0, 1):
                    for j in (-1, 0, 1):
                        for k in (-1, 0, 1):
                            key = (cx + i, cy + j, cz + k)
                            if key in visited:
                                continue
                            visited.add(key)
                            out.extend(grid.get(key, ()))
            return out

        healed: List[Polygon] = []
        for polygon in snapped:
            points: List[Vec3] = []
            count = len(polygon.vertices)
            for i in range(count):
                a = polygon.vertices[i]
                b = polygon.vertices[(i + 1) % count]
                points.append(a)
                edge = b - a
                length = edge.norm()
                if length < tol:
                    continue
                direction = edge / length
                inserted: List[Tuple[float, Vec3]] = []
                for vertex in candidates(a, b):
                    delta = vertex - a
                    t = delta.dot(direction)
                    if t <= tol or t >= length - tol:
                        continue
                    if (delta - direction * t).norm() > tol:
                        continue
                    inserted.append((t, vertex))
                inserted.sort(key=lambda item: item[0])
                previous = 0.0
                for t, vertex in inserted:
                    if t - previous > tol:
                        points.append(vertex)
                        previous = t
            candidate = replace(polygon, vertices=points)
            if not candidate.is_degenerate(tol * tol):
                healed.append(candidate)
        return Solid(healed, self.name, self.layer, self.material, self.color,
                     dict(self.metadata))

    # -- proprietes physiques ---------------------------------------------
    @property
    def bbox(self) -> BBox3:
        return BBox3.of(v for p in self.polygons for v in p.vertices)

    @property
    def area(self) -> float:
        """Aire totale des faces, en mm2."""
        return sum(p.area for p in self.polygons)

    @property
    def signed_volume(self) -> float:
        """Volume signe : negatif si les faces sont orientees vers l'interieur.

        C'est le controle qui empeche une operation booleenne de renvoyer le
        complementaire du resultat attendu ; toute primitive et tout import
        doit produire un volume signe positif.
        """
        total = 0.0
        for polygon in self.polygons:
            for a, b, c in polygon.triangulate():
                total += a.dot(b.cross(c)) / 6.0
        return total

    @property
    def volume(self) -> float:
        """Volume absolu, en mm3."""
        return abs(self.signed_volume)

    def outward(self) -> "Solid":
        """Garantit des faces tournees vers l'exterieur."""
        return self.inverted() if self.signed_volume < 0 else self

    @property
    def centroid(self) -> Vec3:
        """Centre de gravite du volume, exact pour un solide ferme."""
        volume = 0.0
        accumulator = Vec3()
        for polygon in self.polygons:
            for a, b, c in polygon.triangulate():
                dv = a.dot(b.cross(c)) / 6.0
                volume += dv
                accumulator = accumulator + (a + b + c) * (dv / 4.0)
        if abs(volume) < 1e-12:
            box = self.bbox
            return box.center if box.valid else ORIGIN
        return accumulator / volume

    def mass_properties(self, density_kg_m3: float = 2400.0) -> Dict[str, object]:
        """Commande PROPMECA : volume, aire, masse, inertie, boite."""
        volume_mm3 = self.volume
        volume_m3 = volume_mm3 * 1e-9
        centroid = self.centroid
        box = self.bbox
        ixx = iyy = izz = 0.0
        for polygon in self.polygons:
            for a, b, c in polygon.triangulate():
                dv = a.dot(b.cross(c)) / 6.0
                g = (a + b + c) / 3.0 - centroid
                ixx += dv * (g.y * g.y + g.z * g.z)
                iyy += dv * (g.x * g.x + g.z * g.z)
                izz += dv * (g.x * g.x + g.y * g.y)
        rho = density_kg_m3
        return {
            "volume_mm3": round(volume_mm3, 3),
            "volume_m3": round(volume_m3, 9),
            "aire_mm2": round(self.area, 3),
            "aire_m2": round(self.area * 1e-6, 6),
            "masse_kg": round(volume_m3 * rho, 4),
            "masse_volumique_kg_m3": rho,
            "centre_gravite": [round(v, 4) for v in centroid],
            "inertie_kg_m2": [round(abs(i) * 1e-12 * rho, 9)
                              for i in (ixx, iyy, izz)],
            "boite": box.to_dict(),
            "faces": len(self.polygons),
            "triangles": self.triangle_count,
        }

    @property
    def triangle_count(self) -> int:
        return sum(max(0, len(p.vertices) - 2) for p in self.polygons)

    # -- controle qualite --------------------------------------------------
    def check(self, tol: float = 1e-4) -> Dict[str, object]:
        """Commande VERIFSOLIDE : etancheite, orientation, faces degenerees."""
        edges: Dict[Tuple[Tuple[float, ...], Tuple[float, ...]], int] = {}
        degenerate = 0
        for polygon in self.polygons:
            if polygon.is_degenerate(tol):
                degenerate += 1
                continue
            count = len(polygon.vertices)
            for i in range(count):
                a = polygon.vertices[i].rounded(4)
                b = polygon.vertices[(i + 1) % count].rounded(4)
                key = (a, b) if a <= b else (b, a)
                edges[key] = edges.get(key, 0) + 1
        open_edges = [k for k, v in edges.items() if v != 2]
        volume = self.volume
        return {
            "faces": len(self.polygons),
            "faces_degenerees": degenerate,
            "aretes": len(edges),
            "aretes_libres": len(open_edges),
            "ferme": not open_edges and bool(self.polygons),
            "volume_mm3": round(volume, 3),
            "valide": (not open_edges and degenerate == 0 and volume > tol
                       and bool(self.polygons)),
        }

    def edges(self) -> List[Tuple[Vec3, Vec3]]:
        """Commande XARETES : aretes uniques du solide."""
        seen = set()
        out: List[Tuple[Vec3, Vec3]] = []
        for polygon in self.polygons:
            count = len(polygon.vertices)
            for i in range(count):
                a, b = polygon.vertices[i], polygon.vertices[(i + 1) % count]
                ka, kb = a.rounded(4), b.rounded(4)
                key = (ka, kb) if ka <= kb else (kb, ka)
                if key in seen:
                    continue
                seen.add(key)
                out.append((a, b))
        return out

    def vertices(self) -> List[Vec3]:
        """Sommets uniques du solide, ordre stable."""
        seen: Dict[Tuple[float, ...], Vec3] = {}
        for polygon in self.polygons:
            for vertex in polygon.vertices:
                seen.setdefault(vertex.rounded(4), vertex)
        return list(seen.values())

    def separate(self) -> List["Solid"]:
        """Commande SEPARER : eclate un solide en ses volumes disjoints."""
        parent: Dict[int, int] = {i: i for i in range(len(self.polygons))}

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def merge(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[rj] = ri

        owner: Dict[Tuple[float, ...], int] = {}
        for index, polygon in enumerate(self.polygons):
            for vertex in polygon.vertices:
                key = vertex.rounded(3)
                if key in owner:
                    merge(owner[key], index)
                else:
                    owner[key] = index
        groups: Dict[int, List[Polygon]] = {}
        for index, polygon in enumerate(self.polygons):
            groups.setdefault(find(index), []).append(polygon)
        if len(groups) <= 1:
            return [self.copy()]
        return [Solid(items, "%s_%d" % (self.name, i + 1), self.layer,
                      self.material, self.color, dict(self.metadata))
                for i, items in enumerate(groups.values())]

    # -- conversions -------------------------------------------------------
    def to_mesh(self) -> Tuple[List[Tuple[float, float, float]], List[Tuple[int, ...]]]:
        """Sommets fusionnes et faces indexees, format d'export universel."""
        index: Dict[Tuple[float, ...], int] = {}
        vertices: List[Tuple[float, float, float]] = []
        faces: List[Tuple[int, ...]] = []
        for polygon in self.polygons:
            face: List[int] = []
            for vertex in polygon.vertices:
                key = vertex.rounded(5)
                if key not in index:
                    index[key] = len(vertices)
                    vertices.append((vertex.x, vertex.y, vertex.z))
                if not face or face[-1] != index[key]:
                    face.append(index[key])
            if len(face) >= 3 and face[0] != face[-1]:
                faces.append(tuple(face))
            elif len(face) > 3:
                faces.append(tuple(face[:-1]))
        return vertices, faces

    def to_triangles(self) -> List[Tuple[Vec3, Vec3, Vec3]]:
        out: List[Tuple[Vec3, Vec3, Vec3]] = []
        for polygon in self.polygons:
            out.extend(polygon.triangulate())
        return out

    def to_dict(self) -> Dict[str, object]:
        return {"nom": self.name, "calque": self.layer, "materiau": self.material,
                "faces": len(self.polygons), "triangles": self.triangle_count,
                "volume_mm3": round(self.volume, 3),
                "aire_mm2": round(self.area, 3),
                "boite": self.bbox.to_dict()}

    def __repr__(self) -> str:
        return "Solid(%s, faces=%d, volume=%.1f mm3)" % (
            self.name, len(self.polygons), self.volume)


def union_all(solids: Sequence[Solid], name: str = "union") -> Solid:
    """UNION appliquee a une liste : reduction en arbre pour limiter le cout."""
    items = [s for s in solids if s and s.polygons]
    if not items:
        return Solid([], name)
    while len(items) > 1:
        merged: List[Solid] = []
        for i in range(0, len(items) - 1, 2):
            merged.append(items[i].union(items[i + 1]))
        if len(items) % 2:
            merged.append(items[-1])
        items = merged
    result = items[0].copy(name)
    return result


def subtract_all(base: Solid, tools: Sequence[Solid],
                 name: Optional[str] = None) -> Solid:
    """SOUSTRACTION d'une liste d'outils sur un solide de base."""
    result = base.copy(name or base.name)
    for tool in tools:
        if tool and tool.polygons:
            result = result.subtract(tool, result.name)
    return result


def intersect_all(solids: Sequence[Solid], name: str = "intersection") -> Solid:
    items = [s for s in solids if s and s.polygons]
    if not items:
        return Solid([], name)
    result = items[0].copy(name)
    for other in items[1:]:
        result = result.intersect(other, name)
    return result


def interfere(solids: Sequence[Solid]) -> Dict[str, object]:
    """Commande INTERFERENCE : detecte et mesure les collisions deux a deux."""
    items = list(solids)
    collisions: List[Dict[str, object]] = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if not items[i].bbox.intersects(items[j].bbox):
                continue
            common = items[i].intersect(items[j], "interference")
            volume = common.volume
            if volume > 1e-6:
                collisions.append({
                    "a": items[i].name, "b": items[j].name,
                    "volume_mm3": round(volume, 3),
                    "centre": [round(v, 3) for v in common.centroid],
                    "solide": common,
                })
    return {"collisions": len(collisions), "details": collisions}
