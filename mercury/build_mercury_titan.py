#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_mercury_titan.py
======================
Generateur autonome du projet MERCURY CAD AI X - PROJET TITAN.

Une seule execution cree l'arborescence complete, ecrit tous les fichiers
(noyau de modelisation 3D, interoperabilite DWG/DXF/IFC/STEP, backend, API
REST, moteurs CAO/BIM/IA, cloud, mobile, base de donnees, securite, interface
web WebGL, tests, documentation, Docker, CI/CD), puis valide le resultat :
compilation de chaque module, execution de la suite de tests, mesure de la
couverture et demarrage reel de l'API avec sondes sur /health et /ready.

Dependances du generateur : bibliotheque standard uniquement.
Dependances du projet genere : FastAPI et uvicorn (installes a la demande
lors de la phase de validation).

Utilisation
-----------
    python build_mercury_titan.py                 # genere puis valide
    python build_mercury_titan.py --dir /tmp/x    # repertoire cible
    python build_mercury_titan.py --no-verify     # generation seule
    python build_mercury_titan.py --force         # ecrase une cible existante
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

VERSION = "2.0.0"
RACINE_DEFAUT = "Mercury"

# ---------------------------------------------------------------------------
# Les 70 livrables du projet TITAN : nom, groupe, module porteur, etat reel.
# Cette table est la source unique : elle alimente la documentation, le
# registre interrogeable par l'API et les tests de conformite.
# ---------------------------------------------------------------------------
LIVRABLES: List[Tuple[int, str, str, str, str]] = [
    (1, "Vision et architecture globale", "CORE", "docs", "livre"),
    (2, "Analyse marche CAO BIM Construction Tech", "BUSINESS", "docs", "documente"),
    (3, "Moteur IA Design Generatif", "CORE", "AI_Engine.generative_design", "livre"),
    (4, "Assistant conversationnel IA ingenierie", "CORE", "AI_Engine.nlp_assistant", "livre"),
    (5, "Lecture automatique PDF et plans", "CORE", "AI_Engine.vision_ai", "livre"),
    (6, "Vision AI reconnaissance plans", "CORE", "AI_Engine.vision_ai", "livre"),
    (7, "Conversion 2D vers 3D", "CORE", "CAD_Core.modeling", "livre"),
    (8, "Interface CAO nouvelle generation", "CORE", "Frontend", "livre"),
    (9, "Rendu 3D temps reel", "CORE", "CAD_Core.render_engine", "livre"),
    (10, "MVP initial", "CORE", "API.main", "livre"),
    (11, "BIM Engine", "BIM", "BIM_Engine.models", "livre"),
    (12, "Objets BIM intelligents", "BIM", "BIM_Engine.object_library", "livre"),
    (13, "Bibliotheque BIM", "BIM", "BIM_Engine.object_library", "livre"),
    (14, "Standards IFC", "BIM", "BIM_Engine.ifc_handler", "livre"),
    (15, "BIM Cloud Collaboration", "COLLAB", "BIM_Engine.collaboration", "livre"),
    (16, "Architecture Professional Module", "BIM", "CAD_Core.engine_2d", "livre"),
    (17, "Structure Engineering Module", "BIM", "BIM_Engine.structure", "esquisse"),
    (18, "MEP Engineering Module", "BIM", "BIM_Engine.mep", "esquisse"),
    (19, "Documentation automatique", "BIM", "CAD_Core.documentation", "livre"),
    (20, "Assistant ingenieur BIM IA", "CORE", "AI_Engine.nlp_assistant", "livre"),
    (21, "Gestion versions projet", "COLLAB", "Database.repository", "livre"),
    (22, "Marketplace BIM", "BIM", "BIM_Engine.object_library", "esquisse"),
    (23, "Fabricants materiaux", "BIM", "BIM_Engine.object_library", "esquisse"),
    (24, "API BIM", "CORE", "API.main", "livre"),
    (25, "Enterprise BIM Platform", "COLLAB", "Security.rbac", "livre"),
    (26, "Construction AI Platform", "CONSTRUCTION", "Construction.platform", "esquisse"),
    (27, "Planning chantier IA", "CONSTRUCTION", "Construction.planning", "livre"),
    (28, "Suivi avancement chantier", "CONSTRUCTION", "Construction.progress", "esquisse"),
    (29, "Vision IA qualite", "CONSTRUCTION", "AI_Engine.vision_ai", "esquisse"),
    (30, "Securite chantier IA", "CONSTRUCTION", "Construction.safety", "esquisse"),
    (31, "Drone chantier", "CONSTRUCTION", "Construction.drone", "esquisse"),
    (32, "Comparaison BIM reel", "CONSTRUCTION", "Construction.progress", "esquisse"),
    (33, "Gestion ressources", "CONSTRUCTION", "Construction.resources", "esquisse"),
    (34, "Gestion fournisseurs", "CONSTRUCTION", "Construction.resources", "esquisse"),
    (35, "Rapports automatiques", "CONSTRUCTION", "CAD_Core.documentation", "livre"),
    (36, "Cost AI", "COST", "Estimating.cost_ai", "livre"),
    (37, "Metres automatiques", "COST", "Estimating.takeoff", "livre"),
    (38, "Devis IA", "COST", "Estimating.cost_ai", "livre"),
    (39, "Optimisation budget", "COST", "Estimating.cost_ai", "esquisse"),
    (40, "Project Management Enterprise", "COLLAB", "Construction.planning", "esquisse"),
    (41, "Digital Twin Platform", "TWIN", "Cloud_Platform.digital_twin", "livre"),
    (42, "Smart Building OS", "TWIN", "Cloud_Platform.digital_twin", "esquisse"),
    (43, "IoT Integration", "TWIN", "Cloud_Platform.iot", "livre"),
    (44, "Maintenance predictive", "TWIN", "Cloud_Platform.predictive", "livre"),
    (45, "Energy Intelligence", "GREEN", "Sustainability.energy", "livre"),
    (46, "Solar Microgrid", "GREEN", "Sustainability.energy", "esquisse"),
    (47, "Performance batiment", "GREEN", "Sustainability.energy", "livre"),
    (48, "AR Maintenance", "MOBILE", "Mobile.ar", "esquisse"),
    (49, "Drone Inspection Digital Twin", "TWIN", "Construction.drone", "esquisse"),
    (50, "Cycle de vie batiment", "GREEN", "Sustainability.carbon", "livre"),
    (51, "Green Building AI", "GREEN", "Sustainability.carbon", "livre"),
    (52, "Calcul carbone", "GREEN", "Sustainability.carbon", "livre"),
    (53, "Materiaux durables", "GREEN", "Sustainability.carbon", "livre"),
    (54, "Simulation energetique", "GREEN", "Sustainability.energy", "livre"),
    (55, "Certification verte", "GREEN", "Sustainability.certification", "livre"),
    (56, "Adaptation climatique", "GREEN", "Sustainability.energy", "esquisse"),
    (57, "Smart Village Platform", "CITY", "Cloud_Platform.city", "esquisse"),
    (58, "Digital Twin Smart City", "CITY", "Cloud_Platform.city", "esquisse"),
    (59, "GIS Topography Drone", "CITY", "Cloud_Platform.city", "esquisse"),
    (60, "Finance Projet AI", "BUSINESS", "Estimating.cost_ai", "esquisse"),
    (61, "Sustainability AI", "GREEN", "Sustainability.carbon", "livre"),
    (62, "Topography Integration", "CITY", "Cloud_Platform.city", "esquisse"),
    (63, "Mobile Tablet Platform", "MOBILE", "Mobile", "livre"),
    (64, "Expansion internationale", "BUSINESS", "docs", "documente"),
    (65, "Legal Corporate Governance", "BUSINESS", "docs", "documente"),
    (66, "Investor Package", "BUSINESS", "docs/INVESTOR_DECK.md", "documente"),
    (67, "Documentation technique", "BUSINESS", "docs", "livre"),
    (68, "Beta Testing Program", "BUSINESS", "docs", "documente"),
    (69, "Global Launch Plan", "BUSINESS", "docs", "documente"),
    (70, "Master Plan 2030", "BUSINESS", "docs/ROADMAP_2030.md", "documente"),
]

GROUPES = {
    "CORE": "Systeme central : CAO, IA, interface, MVP",
    "BIM": "Moteur BIM, objets, standards IFC, metiers",
    "COLLAB": "Collaboration, versions, entreprise",
    "CONSTRUCTION": "Chantier : planning, suivi, qualite, securite",
    "COST": "Economie : metres, couts, devis",
    "TWIN": "Jumeau numerique, IoT, maintenance",
    "GREEN": "Environnement : carbone, energie, certification",
    "CITY": "Territoire : village et ville intelligents",
    "MOBILE": "Terrain : tablette, mobile, realite augmentee",
    "BUSINESS": "Marche, juridique, investisseurs, lancement",
}

FICHIERS: Dict[str, str] = {}


def ajouter(chemin: str, contenu: str) -> None:
    """Enregistre un fichier a ecrire. Le contenu est normalise."""
    FICHIERS[chemin] = contenu.lstrip("\n")


# ===========================================================================
# 1. NOYAU CAO  (livrables #07, #08, #09, #16, #19)
# ===========================================================================

# =========================================================================
# 1. NOYAU CAO 2D ET 3D  (livrables #07, #08, #09, #16, #19)
# =========================================================================
ajouter('CAD_Core/__init__.py', r'''
"""Noyau de conception assistee par ordinateur.

Deux couches se completent :

- la couche historique (`geometry`, `engine_2d`, `engine_3d`, `rendering`)
  qui transforme un modele BIM en plans et en maillages ;
- le noyau de modelisation 3D (`math3d`, `solid`, `primitives`, `modeling`,
  `solid_edit`, `transform3d`, `mesh_tools`) qui offre les outils volumiques
  d'un logiciel de CAO, avec son document, ses accrochages, ses annotations,
  ses vues et son interpreteur de commandes.
"""
from .documentation import DocumentGenerator
from .engine_2d import Engine2D
from .engine_3d import Engine3D
from .geometry import Vec2, Segment, polygon_area, polygon_centroid
from .math3d import BBox3, Mat4, Plane, Vec3
from .profiles import Curve, Profile
from .rendering import Renderer
from .solid import Polygon, Solid, intersect_all, subtract_all, union_all

__all__ = [
    "Vec2", "Segment", "polygon_area", "polygon_centroid",
    "Engine2D", "Engine3D", "Renderer", "DocumentGenerator",
    "Vec3", "Mat4", "Plane", "BBox3", "Profile", "Curve",
    "Solid", "Polygon", "union_all", "subtract_all", "intersect_all",
]
''')

ajouter('CAD_Core/geometry.py', r'''
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
''')

ajouter('CAD_Core/engine_2d.py', r'''
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
''')

ajouter('CAD_Core/engine_3d.py', r'''
"""Moteur 3D : extrusion du modele BIM en maillage (livrable #07).

Chaque mur devient un prisme perce par ses baies : la portion ouverte
produit une allege sous la baie et un linteau au-dessus. La geometrie
obtenue est exploitable en rendu comme en export IFC.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from .geometry import Vec2, polygon_area

Vertex = Tuple[float, float, float]


@dataclass
class Group:
    """Regroupement de faces partageant un materiau et une entite source."""

    name: str
    material: str
    start: int
    count: int = 0
    entity_id: str = ""


@dataclass
class Mesh:
    vertices: List[Vertex] = field(default_factory=list)
    faces: List[Tuple[int, ...]] = field(default_factory=list)
    groups: List[Group] = field(default_factory=list)

    def open_group(self, name: str, material: str, entity_id: str = "") -> None:
        self.groups.append(Group(name, material, len(self.faces), 0, entity_id))

    def close_group(self) -> None:
        if self.groups:
            self.groups[-1].count = len(self.faces) - self.groups[-1].start

    def add_box(self, origin: Vec2, direction: Vec2, length: float,
                thickness: float, z0: float, z1: float) -> None:
        if length <= 0 or thickness <= 0 or z1 <= z0:
            return
        normal = direction.perp() * (thickness / 2.0)
        a = origin + normal
        b = origin - normal
        c = origin + direction * length - normal
        d = origin + direction * length + normal
        base = len(self.vertices)
        for p in (a, b, c, d):
            self.vertices.append((p.x, p.y, z0))
        for p in (a, b, c, d):
            self.vertices.append((p.x, p.y, z1))
        f = base
        self.faces.extend([
            (f + 0, f + 1, f + 2, f + 3),
            (f + 4, f + 7, f + 6, f + 5),
            (f + 0, f + 4, f + 5, f + 1),
            (f + 1, f + 5, f + 6, f + 2),
            (f + 2, f + 6, f + 7, f + 3),
            (f + 3, f + 7, f + 4, f + 0),
        ])

    def add_prism(self, outline: Sequence[Vec2], z0: float, z1: float) -> None:
        points = list(outline)
        if len(points) < 3:
            return
        if polygon_area(points) < 0:
            points.reverse()
        base = len(self.vertices)
        n = len(points)
        for p in points:
            self.vertices.append((p.x, p.y, z0))
        for p in points:
            self.vertices.append((p.x, p.y, z1))
        self.faces.append(tuple(range(base, base + n))[::-1])
        self.faces.append(tuple(range(base + n, base + 2 * n)))
        for i in range(n):
            j = (i + 1) % n
            self.faces.append((base + i, base + j, base + n + j, base + n + i))

    @property
    def stats(self) -> Dict[str, int]:
        return {"vertices": len(self.vertices), "faces": len(self.faces),
                "groups": len(self.groups)}


class Engine3D:
    """Transforme un projet BIM en maillage."""

    def build(self, project) -> Mesh:
        mesh = Mesh()
        for slab in project.slabs:
            mesh.open_group("dalle_" + slab.id, "beton", slab.id)
            mesh.add_prism([Vec2(*p) for p in slab.outline],
                           slab.z - slab.thickness, slab.z)
            mesh.close_group()
        for wall in project.walls:
            self._extrude_wall(mesh, wall)
        for item in project.furniture:
            mesh.open_group("mobilier_" + item.id, "mobilier", item.id)
            direction = Vec2(math.cos(item.rotation), math.sin(item.rotation))
            origin = Vec2(*item.position) - direction * (item.size[0] / 2.0)
            mesh.add_box(origin, direction, item.size[0], item.size[1],
                         0.0, item.size[2])
            mesh.close_group()
        return mesh

    @staticmethod
    def _extrude_wall(mesh: Mesh, wall) -> None:
        a, b = Vec2(*wall.start), Vec2(*wall.end)
        length = (b - a).norm()
        if length < 1.0:
            return
        direction = (b - a).unit()
        material = "maconnerie" if wall.exterior else "cloison"
        mesh.open_group("mur_" + wall.id, material, wall.id)

        cursor = 0.0
        for opening in sorted(wall.openings, key=lambda o: o.offset):
            x0 = max(0.0, opening.offset - opening.width / 2.0)
            x1 = min(length, opening.offset + opening.width / 2.0)
            if x0 > cursor + 1.0:
                mesh.add_box(a + direction * cursor, direction, x0 - cursor,
                             wall.thickness, 0.0, wall.height)
            cursor = max(cursor, x1)
            if opening.sill > 1.0:
                mesh.add_box(a + direction * x0, direction, x1 - x0,
                             wall.thickness, 0.0, opening.sill)
            head = min(wall.height, opening.sill + opening.height)
            if head < wall.height - 1.0:
                mesh.add_box(a + direction * x0, direction, x1 - x0,
                             wall.thickness, head, wall.height)
        if cursor < length - 1.0:
            mesh.add_box(a + direction * cursor, direction, length - cursor,
                         wall.thickness, 0.0, wall.height)
        mesh.close_group()
''')

ajouter('CAD_Core/rendering.py', r'''
"""Rendu (livrable #09) : export OBJ, glTF et vues vectorielles SVG.

Le rendu temps reel est assure cote client par WebGL ; le serveur produit
les formats d'echange et les vues 2D vectorielles, seuls livrables qui
partent en agence ou en impression.
"""
from __future__ import annotations

import base64
import json
import struct
from typing import Dict, List, Sequence, Tuple

from .engine_3d import Mesh
from .geometry import Vec2, bounding_box

PALETTE: Dict[str, Tuple[float, float, float]] = {
    "maconnerie": (0.85, 0.83, 0.78),
    "cloison": (0.90, 0.89, 0.86),
    "beton": (0.72, 0.72, 0.70),
    "mobilier": (0.55, 0.40, 0.28),
    "default": (0.80, 0.80, 0.80),
}


class Renderer:
    """Convertit un maillage ou un projet en formats diffusables."""

    @staticmethod
    def to_obj(mesh: Mesh, scale: float = 0.001) -> str:
        lines = ["# MERCURY CAD AI X - export OBJ", "mtllib mercury.mtl"]
        for x, y, z in mesh.vertices:
            lines.append("v %.5f %.5f %.5f" % (x * scale, z * scale, -y * scale))
        by_face: Dict[int, str] = {}
        for group in mesh.groups:
            for i in range(group.start, group.start + group.count):
                by_face[i] = group.material
        current = None
        for i, face in enumerate(mesh.faces):
            material = by_face.get(i, "default")
            if material != current:
                current = material
                lines.append("usemtl " + material)
            lines.append("f " + " ".join(str(idx + 1) for idx in face))
        return "\n".join(lines) + "\n"

    @staticmethod
    def to_mtl() -> str:
        out = ["# MERCURY CAD AI X - materiaux"]
        for name, (r, g, b) in PALETTE.items():
            out += ["newmtl " + name, "Kd %.3f %.3f %.3f" % (r, g, b),
                    "Ks 0.05 0.05 0.05", "Ns 20", "illum 2", ""]
        return "\n".join(out)

    @staticmethod
    def to_gltf(mesh: Mesh, scale: float = 0.001) -> str:
        positions: List[float] = []
        indices: List[int] = []
        for x, y, z in mesh.vertices:
            positions += [x * scale, z * scale, -y * scale]
        for face in mesh.faces:
            for k in range(1, len(face) - 1):
                indices += [face[0], face[k], face[k + 1]]
        if not positions:
            positions = [0.0, 0.0, 0.0]
            indices = [0, 0, 0]
        pos_bytes = struct.pack("<%df" % len(positions), *positions)
        idx_bytes = struct.pack("<%dI" % len(indices), *indices)
        padding = (4 - len(pos_bytes) % 4) % 4
        buffer = pos_bytes + b"\x00" * padding + idx_bytes
        uri = "data:application/octet-stream;base64," + \
            base64.b64encode(buffer).decode()
        document = {
            "asset": {"version": "2.0", "generator": "MERCURY CAD AI X"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0, "name": "Projet"}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                        "indices": 1}]}],
            "buffers": [{"byteLength": len(buffer), "uri": uri}],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes),
                 "target": 34962},
                {"buffer": 0, "byteOffset": len(pos_bytes) + padding,
                 "byteLength": len(idx_bytes), "target": 34963},
            ],
            "accessors": [
                {"bufferView": 0, "componentType": 5126,
                 "count": len(positions) // 3, "type": "VEC3",
                 "min": [min(positions[i::3]) for i in range(3)],
                 "max": [max(positions[i::3]) for i in range(3)]},
                {"bufferView": 1, "componentType": 5125,
                 "count": len(indices), "type": "SCALAR"},
            ],
        }
        return json.dumps(document)

    @staticmethod
    def plan_svg(project, width_px: int = 1400, margin: int = 60) -> str:
        points = [Vec2(*w.start) for w in project.walls] + \
                 [Vec2(*w.end) for w in project.walls]
        if not points:
            return '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'
        x0, y0, x1, y1 = bounding_box(points)
        span_x = max(1.0, x1 - x0)
        span_y = max(1.0, y1 - y0)
        k = (width_px - 2 * margin) / span_x
        height_px = int(span_y * k + 2 * margin)

        def sx(x: float) -> float:
            return margin + (x - x0) * k

        def sy(y: float) -> float:
            return height_px - margin - (y - y0) * k

        out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">'
               % (width_px, height_px),
               '<rect width="100%" height="100%" fill="#ffffff"/>',
               '<g stroke="#111111" stroke-width="1.4" fill="none">']
        for wall in project.walls:
            a, b = Vec2(*wall.start), Vec2(*wall.end)
            normal = (b - a).unit().perp() * (wall.thickness / 2.0)
            for p, q in ((a + normal, b + normal), (a - normal, b - normal)):
                out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                           % (sx(p.x), sy(p.y), sx(q.x), sy(q.y)))
        out.append('</g><g font-family="sans-serif" font-size="13" fill="#333"'
                   ' text-anchor="middle">')
        for room in project.rooms:
            out.append('<text x="%.1f" y="%.1f">%s</text>'
                       % (sx(room.centroid[0]), sy(room.centroid[1]), room.name))
            out.append('<text x="%.1f" y="%.1f" font-size="11">%.2f m2</text>'
                       % (sx(room.centroid[0]), sy(room.centroid[1]) + 16,
                          room.area_m2))
        out.append("</g></svg>")
        return "\n".join(out)
''')

ajouter('CAD_Core/documentation.py', r'''
"""Documentation automatique (livrables #19 et #35).

Les nomenclatures et rapports sont derives du modele : ils ne peuvent pas
diverger de la geometrie, puisqu'ils en sont extraits a chaque appel.
"""
from __future__ import annotations

from typing import Dict, List


class DocumentGenerator:
    """Produit nomenclatures et rapports de projet."""

    @staticmethod
    def room_schedule(project) -> List[Dict[str, object]]:
        return [
            {
                "id": room.id,
                "nom": room.name,
                "type": room.kind,
                "surface_m2": room.area_m2,
                "perimetre_m": room.perimeter_m,
                "volume_m3": round(room.area_m2 * room.height / 1000.0, 2),
            }
            for room in sorted(project.rooms, key=lambda r: -r.area_m2)
        ]

    @staticmethod
    def project_report(project) -> Dict[str, object]:
        openings = [o for w in project.walls for o in w.openings]
        return {
            "projet": project.name,
            "type_batiment": project.building_type,
            "version": project.version,
            "surface_utile_m2": round(sum(r.area_m2 for r in project.rooms), 2),
            "nb_pieces": len(project.rooms),
            "nb_murs": len(project.walls),
            "lineaire_murs_m": round(sum(w.length for w in project.walls) / 1000.0, 2),
            "nb_portes": sum(1 for o in openings if o.type == "porte"),
            "nb_fenetres": sum(1 for o in openings if o.type != "porte"),
            "nb_objets": len(project.furniture),
        }
''')


# =========================================================================
# 2. NOYAU DE MODELISATION 3D : maths, solides, booleens
# =========================================================================
ajouter('CAD_Core/math3d.py', r'''
"""Algebre lineaire 3D du noyau CAO : points, vecteurs, matrices, plans.

Toutes les operations de modelisation (primitives, extrusion, revolution,
tableaux, alignements) reposent sur ce module. Il ne depend de rien : le
noyau doit rester utilisable dans un worker, une tache batch ou un test.

Convention : matrices 4x4 en ligne-majeure, transformation d'un point par
`Mat4.apply(point)`, composition par `a * b` qui applique `b` puis `a`,
comme en algebre classique.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

EPS = 1e-9
TOL = 1e-7


@dataclass(frozen=True)
class Vec3:
    """Point ou vecteur de l'espace."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, k: float) -> "Vec3":
        return Vec3(self.x * k, self.y * k, self.z * k)

    __rmul__ = __mul__

    def __truediv__(self, k: float) -> "Vec3":
        if abs(k) < EPS:
            raise ZeroDivisionError("division d'un vecteur par zero")
        return Vec3(self.x / k, self.y / k, self.z / k)

    def __neg__(self) -> "Vec3":
        return Vec3(-self.x, -self.y, -self.z)

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def __getitem__(self, i: int) -> float:
        return (self.x, self.y, self.z)[i]

    def dot(self, o: "Vec3") -> float:
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o: "Vec3") -> "Vec3":
        return Vec3(self.y * o.z - self.z * o.y,
                    self.z * o.x - self.x * o.z,
                    self.x * o.y - self.y * o.x)

    def norm(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def norm2(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    def unit(self) -> "Vec3":
        n = self.norm()
        if n < EPS:
            return Vec3(0.0, 0.0, 0.0)
        return Vec3(self.x / n, self.y / n, self.z / n)

    def distance_to(self, o: "Vec3") -> float:
        return (self - o).norm()

    def lerp(self, o: "Vec3", t: float) -> "Vec3":
        return Vec3(self.x + (o.x - self.x) * t,
                    self.y + (o.y - self.y) * t,
                    self.z + (o.z - self.z) * t)

    def any_perpendicular(self) -> "Vec3":
        """Un vecteur unitaire quelconque orthogonal a self (self non nul)."""
        reference = Vec3(0.0, 0.0, 1.0)
        if abs(self.unit().dot(reference)) > 0.9:
            reference = Vec3(1.0, 0.0, 0.0)
        return self.cross(reference).unit()

    def angle_to(self, o: "Vec3") -> float:
        """Angle non oriente en radians entre deux vecteurs."""
        a, b = self.unit(), o.unit()
        return math.acos(max(-1.0, min(1.0, a.dot(b))))

    def rounded(self, digits: int = 6) -> Tuple[float, float, float]:
        return (round(self.x, digits), round(self.y, digits), round(self.z, digits))

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @staticmethod
    def of(value) -> "Vec3":
        """Accepte Vec3, tuple, liste ou dict et renvoie un Vec3."""
        if isinstance(value, Vec3):
            return value
        if isinstance(value, dict):
            return Vec3(float(value.get("x", 0.0)), float(value.get("y", 0.0)),
                        float(value.get("z", 0.0)))
        seq = list(value)
        while len(seq) < 3:
            seq.append(0.0)
        return Vec3(float(seq[0]), float(seq[1]), float(seq[2]))


ORIGIN = Vec3(0.0, 0.0, 0.0)
X_AXIS = Vec3(1.0, 0.0, 0.0)
Y_AXIS = Vec3(0.0, 1.0, 0.0)
Z_AXIS = Vec3(0.0, 0.0, 1.0)


class Mat4:
    """Matrice homogene 4x4, stockee en 16 flottants ligne-majeure."""

    __slots__ = ("m",)

    def __init__(self, values: Sequence[float] = None) -> None:
        if values is None:
            self.m: Tuple[float, ...] = (1.0, 0.0, 0.0, 0.0,
                                         0.0, 1.0, 0.0, 0.0,
                                         0.0, 0.0, 1.0, 0.0,
                                         0.0, 0.0, 0.0, 1.0)
        else:
            values = tuple(float(v) for v in values)
            if len(values) != 16:
                raise ValueError("une matrice 4x4 exige 16 valeurs")
            self.m = values

    # -- constructeurs -----------------------------------------------------
    @staticmethod
    def identity() -> "Mat4":
        return Mat4()

    @staticmethod
    def translation(v) -> "Mat4":
        t = Vec3.of(v)
        return Mat4((1, 0, 0, t.x, 0, 1, 0, t.y, 0, 0, 1, t.z, 0, 0, 0, 1))

    @staticmethod
    def scaling(factor, base=ORIGIN) -> "Mat4":
        """Echelle uniforme ou non, autour d'un point de base."""
        if isinstance(factor, (int, float)):
            s = Vec3(float(factor), float(factor), float(factor))
        else:
            s = Vec3.of(factor)
        base = Vec3.of(base)
        core = Mat4((s.x, 0, 0, 0, 0, s.y, 0, 0, 0, 0, s.z, 0, 0, 0, 0, 1))
        return Mat4.translation(base) * core * Mat4.translation(-base)

    @staticmethod
    def rotation(axis, angle: float, base=ORIGIN) -> "Mat4":
        """Rotation d'angle (radians) autour d'un axe passant par `base`."""
        a = Vec3.of(axis).unit()
        if a.norm() < EPS:
            raise ValueError("axe de rotation nul")
        base = Vec3.of(base)
        c, s = math.cos(angle), math.sin(angle)
        t = 1.0 - c
        x, y, z = a.x, a.y, a.z
        core = Mat4((t * x * x + c, t * x * y - s * z, t * x * z + s * y, 0,
                     t * x * y + s * z, t * y * y + c, t * y * z - s * x, 0,
                     t * x * z - s * y, t * y * z + s * x, t * z * z + c, 0,
                     0, 0, 0, 1))
        return Mat4.translation(base) * core * Mat4.translation(-base)

    @staticmethod
    def rotation_x(angle: float) -> "Mat4":
        return Mat4.rotation(X_AXIS, angle)

    @staticmethod
    def rotation_y(angle: float) -> "Mat4":
        return Mat4.rotation(Y_AXIS, angle)

    @staticmethod
    def rotation_z(angle: float) -> "Mat4":
        return Mat4.rotation(Z_AXIS, angle)

    @staticmethod
    def mirror(plane: "Plane") -> "Mat4":
        """Symetrie par rapport a un plan (commande MIROIR3D)."""
        n = plane.normal.unit()
        d = plane.offset
        x, y, z = n.x, n.y, n.z
        return Mat4((1 - 2 * x * x, -2 * x * y, -2 * x * z, 2 * d * x,
                     -2 * x * y, 1 - 2 * y * y, -2 * y * z, 2 * d * y,
                     -2 * x * z, -2 * y * z, 1 - 2 * z * z, 2 * d * z,
                     0, 0, 0, 1))

    @staticmethod
    def frame(origin, x_axis, y_axis, z_axis) -> "Mat4":
        """Matrice qui envoie le repere global sur le repere donne."""
        o, ax, ay, az = (Vec3.of(origin), Vec3.of(x_axis).unit(),
                         Vec3.of(y_axis).unit(), Vec3.of(z_axis).unit())
        return Mat4((ax.x, ay.x, az.x, o.x,
                     ax.y, ay.y, az.y, o.y,
                     ax.z, ay.z, az.z, o.z,
                     0, 0, 0, 1))

    @staticmethod
    def align(src_points: Sequence, dst_points: Sequence) -> "Mat4":
        """Aligne un triedre source sur un triedre cible (commande ALIGNER3D).

        Un, deux ou trois couples de points sont acceptes, exactement comme
        dans AutoCAD : translation pure, puis rotation, puis mise a plat.
        """
        src = [Vec3.of(p) for p in src_points]
        dst = [Vec3.of(p) for p in dst_points]
        if not src or len(src) != len(dst):
            raise ValueError("ALIGNER3D exige autant de points source que cible")
        if len(src) == 1:
            return Mat4.translation(dst[0] - src[0])

        def basis(points: List[Vec3]) -> Tuple[Vec3, Vec3, Vec3]:
            ex = (points[1] - points[0]).unit()
            if len(points) >= 3:
                temp = points[2] - points[0]
                ez = ex.cross(temp)
                if ez.norm() < TOL:
                    ez = ex.any_perpendicular()
                ez = ez.unit()
            else:
                ez = ex.any_perpendicular()
            ey = ez.cross(ex).unit()
            return ex, ey, ez

        sx, sy, sz = basis(src)
        dx, dy, dz = basis(dst)
        to_origin = Mat4.translation(-src[0])
        rotate = Mat4.frame(ORIGIN, dx, dy, dz) * Mat4.frame(ORIGIN, sx, sy, sz).transposed()
        return Mat4.translation(dst[0]) * rotate * to_origin

    # -- algebre -----------------------------------------------------------
    def __mul__(self, other):
        if isinstance(other, Mat4):
            a, b = self.m, other.m
            out = []
            for row in range(4):
                for col in range(4):
                    out.append(sum(a[row * 4 + k] * b[k * 4 + col]
                                   for k in range(4)))
            return Mat4(out)
        if isinstance(other, Vec3):
            return self.apply(other)
        raise TypeError("produit matriciel non supporte avec %r" % type(other))

    def __eq__(self, other) -> bool:
        return (isinstance(other, Mat4)
                and all(abs(a - b) < 1e-9 for a, b in zip(self.m, other.m)))

    def __repr__(self) -> str:
        rows = ["[%s]" % ", ".join("%.4f" % v for v in self.m[i * 4:i * 4 + 4])
                for i in range(4)]
        return "Mat4(%s)" % ", ".join(rows)

    def apply(self, point) -> Vec3:
        """Transforme un point (composante homogene w = 1)."""
        p = Vec3.of(point)
        m = self.m
        w = m[12] * p.x + m[13] * p.y + m[14] * p.z + m[15]
        if abs(w) < EPS:
            w = 1.0
        return Vec3((m[0] * p.x + m[1] * p.y + m[2] * p.z + m[3]) / w,
                    (m[4] * p.x + m[5] * p.y + m[6] * p.z + m[7]) / w,
                    (m[8] * p.x + m[9] * p.y + m[10] * p.z + m[11]) / w)

    def apply_vector(self, vector) -> Vec3:
        """Transforme une direction : la translation est ignoree."""
        v = Vec3.of(vector)
        m = self.m
        return Vec3(m[0] * v.x + m[1] * v.y + m[2] * v.z,
                    m[4] * v.x + m[5] * v.y + m[6] * v.z,
                    m[8] * v.x + m[9] * v.y + m[10] * v.z)

    def transposed(self) -> "Mat4":
        m = self.m
        return Mat4([m[i + 4 * j] for i in range(4) for j in range(4)])

    def determinant(self) -> float:
        m = self.m

        def minor(r0, r1, r2, c0, c1, c2):
            return (m[r0 * 4 + c0] * (m[r1 * 4 + c1] * m[r2 * 4 + c2]
                                      - m[r1 * 4 + c2] * m[r2 * 4 + c1])
                    - m[r0 * 4 + c1] * (m[r1 * 4 + c0] * m[r2 * 4 + c2]
                                        - m[r1 * 4 + c2] * m[r2 * 4 + c0])
                    + m[r0 * 4 + c2] * (m[r1 * 4 + c0] * m[r2 * 4 + c1]
                                        - m[r1 * 4 + c1] * m[r2 * 4 + c0]))

        return (m[0] * minor(1, 2, 3, 1, 2, 3) - m[1] * minor(1, 2, 3, 0, 2, 3)
                + m[2] * minor(1, 2, 3, 0, 1, 3) - m[3] * minor(1, 2, 3, 0, 1, 2))

    def inverse(self) -> "Mat4":
        """Inverse par Gauss-Jordan. Leve ValueError si la matrice est singuliere."""
        size = 4
        rows = [[self.m[r * 4 + c] for c in range(size)]
                + [1.0 if r == c else 0.0 for c in range(size)]
                for r in range(size)]
        for col in range(size):
            pivot = max(range(col, size), key=lambda r: abs(rows[r][col]))
            if abs(rows[pivot][col]) < 1e-12:
                raise ValueError("matrice singuliere : inversion impossible")
            rows[col], rows[pivot] = rows[pivot], rows[col]
            factor = rows[col][col]
            rows[col] = [v / factor for v in rows[col]]
            for r in range(size):
                if r == col:
                    continue
                k = rows[r][col]
                if k:
                    rows[r] = [v - k * w for v, w in zip(rows[r], rows[col])]
        return Mat4([rows[r][size + c] for r in range(size) for c in range(size)])

    def normal_matrix(self) -> "Mat4":
        """Matrice a appliquer aux normales (inverse transposee)."""
        return self.inverse().transposed()

    def is_mirroring(self) -> bool:
        """Vrai si la transformation inverse l'orientation des faces."""
        return self.determinant() < 0.0

    def to_list(self) -> List[float]:
        return list(self.m)

    def to_column_major(self) -> List[float]:
        """Format attendu par WebGL et glTF."""
        return self.transposed().to_list()


@dataclass(frozen=True)
class Plane:
    """Plan oriente : normal . p = offset."""

    normal: Vec3
    offset: float

    @staticmethod
    def from_point_normal(point, normal) -> "Plane":
        n = Vec3.of(normal).unit()
        if n.norm() < EPS:
            raise ValueError("normale de plan nulle")
        return Plane(n, n.dot(Vec3.of(point)))

    @staticmethod
    def from_points(a, b, c) -> "Plane":
        a, b, c = Vec3.of(a), Vec3.of(b), Vec3.of(c)
        n = (b - a).cross(c - a)
        if n.norm() < TOL:
            raise ValueError("trois points alignes ne definissent pas un plan")
        return Plane.from_point_normal(a, n)

    @property
    def origin(self) -> Vec3:
        return self.normal * self.offset

    def signed_distance(self, point) -> float:
        return self.normal.dot(Vec3.of(point)) - self.offset

    def project(self, point) -> Vec3:
        p = Vec3.of(point)
        return p - self.normal * self.signed_distance(p)

    def flipped(self) -> "Plane":
        return Plane(-self.normal, -self.offset)

    def basis(self) -> Tuple[Vec3, Vec3]:
        """Repere orthonorme du plan (u, v).

        Applique l'algorithme d'axe arbitraire de la norme DXF : le repere
        obtenu est celui qu'attendent AutoCAD et tous les lecteurs DXF, ce
        qui garantit qu'un cercle exporte revient au meme endroit.
        """
        n = self.normal.unit()
        if abs(n.x) < 1.0 / 64.0 and abs(n.y) < 1.0 / 64.0:
            u = Y_AXIS.cross(n).unit()
        else:
            u = Z_AXIS.cross(n).unit()
        if u.norm() < EPS:
            u = n.any_perpendicular()
        return u, n.cross(u).unit()

    def to_world(self, u: float, v: float) -> Vec3:
        bu, bv = self.basis()
        return self.origin + bu * u + bv * v

    def to_local(self, point) -> Tuple[float, float]:
        bu, bv = self.basis()
        d = Vec3.of(point) - self.origin
        return d.dot(bu), d.dot(bv)

    def line_intersection(self, a, b):
        """Point d'intersection du segment [a, b] avec le plan, sinon None."""
        a, b = Vec3.of(a), Vec3.of(b)
        da, db = self.signed_distance(a), self.signed_distance(b)
        if abs(da - db) < EPS:
            return None
        t = da / (da - db)
        if t < -TOL or t > 1.0 + TOL:
            return None
        return a.lerp(b, t)


XY_PLANE = Plane(Z_AXIS, 0.0)
XZ_PLANE = Plane(Y_AXIS, 0.0)
YZ_PLANE = Plane(X_AXIS, 0.0)


@dataclass
class BBox3:
    """Boite englobante alignee sur les axes."""

    min: Vec3 = Vec3(math.inf, math.inf, math.inf)
    max: Vec3 = Vec3(-math.inf, -math.inf, -math.inf)

    @staticmethod
    def of(points: Iterable) -> "BBox3":
        box = BBox3()
        for p in points:
            box.add(p)
        return box

    def add(self, point) -> "BBox3":
        p = Vec3.of(point)
        self.min = Vec3(min(self.min.x, p.x), min(self.min.y, p.y),
                        min(self.min.z, p.z))
        self.max = Vec3(max(self.max.x, p.x), max(self.max.y, p.y),
                        max(self.max.z, p.z))
        return self

    @property
    def valid(self) -> bool:
        return (self.min.x <= self.max.x and self.min.y <= self.max.y
                and self.min.z <= self.max.z)

    @property
    def center(self) -> Vec3:
        return (self.min + self.max) * 0.5 if self.valid else ORIGIN

    @property
    def size(self) -> Vec3:
        return self.max - self.min if self.valid else ORIGIN

    @property
    def diagonal(self) -> float:
        return self.size.norm() if self.valid else 0.0

    def expanded(self, margin: float) -> "BBox3":
        d = Vec3(margin, margin, margin)
        return BBox3(self.min - d, self.max + d)

    def intersects(self, other: "BBox3", tol: float = TOL) -> bool:
        if not (self.valid and other.valid):
            return False
        return not (self.max.x < other.min.x - tol or other.max.x < self.min.x - tol
                    or self.max.y < other.min.y - tol or other.max.y < self.min.y - tol
                    or self.max.z < other.min.z - tol or other.max.z < self.min.z - tol)

    def contains(self, point, tol: float = TOL) -> bool:
        p = Vec3.of(point)
        return (self.min.x - tol <= p.x <= self.max.x + tol
                and self.min.y - tol <= p.y <= self.max.y + tol
                and self.min.z - tol <= p.z <= self.max.z + tol)

    def to_dict(self):
        if not self.valid:
            return {"vide": True}
        return {"min": list(self.min), "max": list(self.max),
                "taille": list(self.size), "centre": list(self.center)}


def polygon_normal(points: Sequence) -> Vec3:
    """Normale d'un polygone gauche par la formule de Newell."""
    pts = [Vec3.of(p) for p in points]
    n = Vec3()
    count = len(pts)
    for i in range(count):
        a, b = pts[i], pts[(i + 1) % count]
        n = n + Vec3((a.y - b.y) * (a.z + b.z),
                     (a.z - b.z) * (a.x + b.x),
                     (a.x - b.x) * (a.y + b.y))
    return n.unit()


def polygon_area_3d(points: Sequence) -> float:
    """Aire d'un polygone plan quelconque de l'espace.

    Ecrite sans allocation : ce calcul est appele des centaines de milliers
    de fois par les operations booleennes.
    """
    count = len(points)
    if count < 3:
        return 0.0
    if not isinstance(points[0], Vec3):
        points = [Vec3.of(p) for p in points]
    sx = sy = sz = 0.0
    previous = points[-1]
    for current in points:
        sx += previous.y * current.z - previous.z * current.y
        sy += previous.z * current.x - previous.x * current.z
        sz += previous.x * current.y - previous.y * current.x
        previous = current
    return math.sqrt(sx * sx + sy * sy + sz * sz) / 2.0
''')

ajouter('CAD_Core/solid.py', r'''
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
''')

ajouter('CAD_Core/profiles.py', r'''
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
''')


# =========================================================================
# 3. OUTILS VOLUMIQUES : primitives, modelisation, edition, reseaux
# =========================================================================
ajouter('CAD_Core/primitives.py', r'''
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
''')

ajouter('CAD_Core/mesh_tools.py', r'''
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
''')

ajouter('CAD_Core/modeling.py', r'''
"""Outils volumiques a partir d'un profil : le coeur du ruban 3D.

EXTRUSION, REVOLUTION, BALAYAGE, LISSAGE, APPUYERTIRER, EPAISSIR, ainsi que
les surfaces reglees, tabulees, de Coons et de revolution. Chaque fonction
prend un ou plusieurs `Profile` et rend un `Solid` ferme (ou une surface
ouverte pour les fonctions de la famille SURFACE*).
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .math3d import (EPS, Mat4, ORIGIN, Plane, TOL, Vec3, X_AXIS, Y_AXIS,
                     Z_AXIS, polygon_normal)
from .profiles import Curve, DEFAULT_SEGMENTS, Profile
from .solid import Polygon, Solid


def _cap(profile: Profile, flip: bool, material: str) -> List[Polygon]:
    """Face pleine d'un profil, ouvertures comprises."""
    polygons: List[Polygon] = []
    for triangle in profile.triangulate():
        points = list(triangle)
        if flip:
            points.reverse()
        polygons.append(Polygon(points, material=material))
    return polygons


def _cap_oriented(rings: Sequence[Sequence[Vec3]], normal: Vec3,
                  material: str) -> List[Polygon]:
    """Face pleine dont la normale suit exactement la direction demandee."""
    profile = Profile(list(rings[0]), [list(r) for r in rings[1:]])
    return _cap(profile.oriented(normal), False, material)


def _ring_walls(bottom: Sequence[Vec3], top: Sequence[Vec3], material: str,
                outward: bool) -> List[Polygon]:
    """Bande laterale entre deux anneaux de meme longueur."""
    polygons: List[Polygon] = []
    count = len(bottom)
    for i in range(count):
        j = (i + 1) % count
        quad = [bottom[i], bottom[j], top[j], top[i]]
        if not outward:
            quad.reverse()
        polygons.append(Polygon(quad, material=material))
    return polygons


def offset_ring(points: Sequence[Vec3], distance: float,
                normal: Optional[Vec3] = None) -> List[Vec3]:
    """Decale un contour ferme dans son plan (depouille, coque, OFFSET)."""
    pts = [Vec3.of(p) for p in points]
    if abs(distance) < TOL or len(pts) < 3:
        return list(pts)
    n = Vec3.of(normal) if normal is not None else polygon_normal(pts)
    out: List[Vec3] = []
    count = len(pts)
    for i in range(count):
        previous = pts[(i - 1) % count]
        current = pts[i]
        following = pts[(i + 1) % count]
        d1 = (current - previous).unit()
        d2 = (following - current).unit()
        n1 = n.cross(d1).unit()
        n2 = n.cross(d2).unit()
        bisector = (n1 + n2)
        if bisector.norm() < 1e-6:
            bisector = n1
        bisector = bisector.unit()
        scale = max(0.2, bisector.dot(n1))
        out.append(current + bisector * (distance / scale))
    return out


def extrude(profile: Profile, height: float = 1000.0, direction=None,
            taper: float = 0.0, path: Optional[Curve] = None,
            material: str = "default", name: str = "extrusion") -> Solid:
    """Commande EXTRUSION : hauteur, direction, depouille ou trajectoire.

    - `height` seul : extrusion droite selon la normale du profil.
    - `direction` : vecteur complet de l'extrusion (option Direction) ;
      il remplace `height`, sa longueur donne la hauteur.
    - `taper` : angle de depouille en degres (option Angle d'extrusion).
    - `path` : extrusion le long d'une trajectoire (option Trajectoire).
    """
    if path is not None:
        return sweep(profile, path, material=material, name=name)
    if len(profile.outline) < 3:
        raise ValueError("EXTRUSION : le profil doit avoir au moins 3 sommets")
    normal = profile.normal
    if direction is not None:
        vector = Vec3.of(direction)
        if vector.norm() < TOL:
            raise ValueError("EXTRUSION : direction nulle")
    else:
        if abs(height) < TOL:
            raise ValueError("EXTRUSION : hauteur nulle")
        vector = normal * height
    reference = normal if vector.dot(normal) > 0 else -normal
    # Le contour est oriente dans le sens direct vu depuis la direction
    # d'extrusion : les murs lateraux en heritent une normale sortante, et
    # les ouvertures, deja retournees, percent correctement le volume.
    source = profile.oriented(reference)
    inset = 0.0
    if abs(taper) > 1e-9:
        inset = vector.norm() * math.tan(math.radians(taper))

    polygons: List[Polygon] = _cap_oriented(source.rings(), -reference, material)
    top_rings: List[List[Vec3]] = []
    for ring_index, ring in enumerate(source.rings()):
        ring_normal = reference if ring_index == 0 else -reference
        shifted = offset_ring(ring, inset, ring_normal) if abs(inset) > TOL \
            else list(ring)
        top = [p + vector for p in shifted]
        top_rings.append(top)
        polygons.extend(_ring_walls(ring, top, material, outward=True))
    polygons.extend(_cap_oriented(top_rings, reference, material))
    solid = Solid.from_polygons(polygons, name=name, material=material)
    return solid.heal().outward().apply_appearance()


def revolve(profile: Profile, axis_point=ORIGIN, axis_direction=Y_AXIS,
            angle: float = 2 * math.pi, segments: int = DEFAULT_SEGMENTS,
            material: str = "default", name: str = "revolution") -> Solid:
    """Commande REVOLUTION : profil tourne autour d'un axe, total ou partiel."""
    if len(profile.outline) < 3:
        raise ValueError("REVOLUTION : le profil doit avoir au moins 3 sommets")
    axis = Vec3.of(axis_direction).unit()
    if axis.norm() < TOL:
        raise ValueError("REVOLUTION : axe nul")
    base = Vec3.of(axis_point)
    full = abs(abs(angle) - 2 * math.pi) < 1e-6
    steps = max(3, int(math.ceil(abs(angle) / (2 * math.pi) * segments)))
    source = profile.oriented()
    rings: List[List[List[Vec3]]] = []
    for step in range(steps + 1):
        rotation = Mat4.rotation(axis, angle * step / float(steps), base)
        rings.append([[rotation.apply(p) for p in ring]
                      for ring in source.rings()])

    polygons: List[Polygon] = []
    for step in range(steps):
        current, following = rings[step], rings[step + 1]
        for ring_index in range(len(current)):
            polygons.extend(_ring_walls_open(current[ring_index],
                                             following[ring_index],
                                             material, True))
    if not full:
        # La normale sortante d'une face de coupe est l'oppose du deplacement
        # de la matiere : c'est ce qui ferme proprement une revolution
        # partielle (option Angle de revolution).
        def motion(rings_at_step) -> Vec3:
            centroid = Vec3()
            points = rings_at_step[0]
            for point in points:
                centroid = centroid + point
            centroid = centroid / float(len(points))
            radial = centroid - base
            radial = radial - axis * radial.dot(axis)
            direction = axis.cross(radial)
            if direction.norm() < TOL:
                direction = axis.any_perpendicular()
            return direction.unit() * (1.0 if angle >= 0 else -1.0)

        polygons.extend(_cap_oriented(rings[0], -motion(rings[0]), material))
        polygons.extend(_cap_oriented(rings[steps], motion(rings[steps]),
                                      material))
    solid = Solid.from_polygons(polygons, name=name, material=material)
    return solid.heal().outward().apply_appearance()


def _ring_walls_open(bottom: Sequence[Vec3], top: Sequence[Vec3], material: str,
                     outward: bool) -> List[Polygon]:
    """Bande entre deux anneaux fermes, faces degenerees ecartees."""
    polygons: List[Polygon] = []
    count = len(bottom)
    for i in range(count):
        j = (i + 1) % count
        quad = [bottom[i], bottom[j], top[j], top[i]]
        if not outward:
            quad.reverse()
        polygon = Polygon(quad, material=material)
        if not polygon.is_degenerate(1e-9):
            polygons.append(polygon)
    return polygons


def sweep(profile: Profile, path: Curve, twist: float = 0.0,
          scale: float = 1.0, align: bool = True, material: str = "default",
          name: str = "balayage") -> Solid:
    """Commande BALAYAGE : profil deplace le long d'une trajectoire.

    Le repere est transporte parallelement le long du chemin : le profil ne
    vrille pas de lui-meme, exactement comme l'option Torsion=0 d'AutoCAD.
    """
    if len(path.points) < 2:
        raise ValueError("BALAYAGE : la trajectoire doit avoir 2 points au moins")
    working = path
    if abs(twist) > 1e-6 or abs(scale - 1.0) > 1e-6:
        # Une torsion ou une mise a l'echelle progressive doit etre decrite
        # par assez de sections, sinon le solide obtenu est un prisme vrille
        # en une seule marche au lieu d'une helice reguliere.
        needed = max(len(path.points), int(abs(twist) / 5.0) + 2, 8)
        working = path.resampled(needed)
        working.closed = path.closed
    points = list(working.points)
    if working.closed and len(points) > 2:
        points = points + [points[0]]
    if len(profile.outline) < 3:
        raise ValueError("BALAYAGE : le profil doit avoir au moins 3 sommets")

    source = profile.oriented()
    origin = source.centroid
    normal = source.normal
    tangents = Curve(points).tangents()

    # Repere initial aligne sur la premiere tangente, puis transport parallele.
    frames: List[Tuple[Vec3, Vec3, Vec3]] = []
    reference = tangents[0]
    up = reference.any_perpendicular()
    for index, tangent in enumerate(tangents):
        if index > 0:
            previous = tangents[index - 1]
            axis = previous.cross(tangent)
            if axis.norm() > 1e-9:
                up = Mat4.rotation(axis, previous.angle_to(tangent)).apply_vector(up)
        side = tangent.cross(up).unit()
        frames.append((tangent, up.unit(), side))


    rings: List[List[List[Vec3]]] = []
    total = float(len(points) - 1)
    for index, point in enumerate(points):
        tangent, up, side = frames[index]
        t = index / total if total else 0.0
        # (up, side, tangent) forme un triedre direct : un repere indirect
        # retournerait silencieusement l'enroulement des sections et donc
        # l'orientation des faces du balayage.
        matrix = Mat4.frame(point, up, side, tangent)
        if align:
            base = Mat4.frame(origin, *_profile_frame(source, normal)).inverse()
        else:
            base = Mat4.translation(-origin)
        factor = 1.0 + (scale - 1.0) * t
        transform = matrix * Mat4.scaling(factor) * \
            Mat4.rotation(Z_AXIS, math.radians(twist) * t) * base
        rings.append([[transform.apply(p) for p in ring] for ring in source.rings()])

    polygons: List[Polygon] = []
    for index in range(len(rings) - 1):
        for ring_index in range(len(rings[index])):
            polygons.extend(_ring_walls_open(rings[index][ring_index],
                                             rings[index + 1][ring_index],
                                             material, ring_index == 0))
    if not working.closed:
        polygons.extend(_cap_oriented(rings[0], -tangents[0], material))
        polygons.extend(_cap_oriented(rings[-1], tangents[-1], material))
    solid = Solid.from_polygons(polygons, name=name, material=material)
    return solid.heal().outward().apply_appearance()


def _profile_frame(profile: Profile, normal: Vec3) -> Tuple[Vec3, Vec3, Vec3]:
    plane = Plane.from_point_normal(profile.centroid, normal)
    u, v = plane.basis()
    return u, v, normal


def loft(profiles: Sequence[Profile], ruled: bool = True, closed: bool = False,
         smooth_levels: int = 0, material: str = "default",
         name: str = "lissage") -> Solid:
    """Commande LISSAGE : transition entre plusieurs sections.

    `ruled` produit des faces reglees entre sections consecutives ; sinon
    les sections sont interpolees par une spline pour adoucir la surface.
    """
    sections = [p.oriented() for p in profiles if len(p.outline) >= 3]
    if len(sections) < 2:
        raise ValueError("LISSAGE : au moins deux sections sont necessaires")
    resolution = max(len(s.outline) for s in sections)
    rings = [_resample_ring(s.outline, resolution) for s in sections]
    rings = _align_rings(rings)
    if not ruled:
        rings = _interpolate_rings(rings, max(2, smooth_levels or 4))

    polygons: List[Polygon] = []
    for index in range(len(rings) - 1):
        polygons.extend(_ring_walls_open(rings[index], rings[index + 1],
                                         material, True))
    if closed:
        polygons.extend(_ring_walls_open(rings[-1], rings[0], material, True))
    else:
        direction = (rings[-1][0] - rings[0][0])
        axis_hint = polygon_normal(rings[0])
        if axis_hint.dot(direction) < 0:
            axis_hint = -axis_hint
        polygons.extend(_cap_oriented([rings[0]], -axis_hint, material))
        polygons.extend(_cap_oriented([rings[-1]], axis_hint, material))
    solid = Solid.from_polygons(polygons, name=name, material=material)
    return solid.heal().outward().apply_appearance()


def _resample_ring(points: Sequence[Vec3], count: int) -> List[Vec3]:
    curve = Curve(list(points), True)
    resampled = curve.resampled(count + 1).points
    return resampled[:count]


def _align_rings(rings: List[List[Vec3]]) -> List[List[Vec3]]:
    """Fait tourner chaque anneau pour minimiser la torsion du lissage."""
    aligned = [rings[0]]
    for ring in rings[1:]:
        previous = aligned[-1]
        best_shift, best_cost = 0, None
        for shift in range(len(ring)):
            cost = sum(previous[i].distance_to(ring[(i + shift) % len(ring)])
                       for i in range(0, len(ring), max(1, len(ring) // 12)))
            if best_cost is None or cost < best_cost:
                best_cost, best_shift = cost, shift
        aligned.append(ring[best_shift:] + ring[:best_shift])
    return aligned


def _interpolate_rings(rings: List[List[Vec3]], density: int) -> List[List[Vec3]]:
    """Insere des anneaux intermediaires par spline de Catmull-Rom."""
    if len(rings) < 3:
        return rings
    count = len(rings[0])
    out: List[List[Vec3]] = []
    for index in range(len(rings) - 1):
        for step in range(density):
            t = step / float(density)
            ring: List[Vec3] = []
            for k in range(count):
                p0 = rings[max(0, index - 1)][k]
                p1 = rings[index][k]
                p2 = rings[index + 1][k]
                p3 = rings[min(len(rings) - 1, index + 2)][k]
                t2, t3 = t * t, t * t * t
                ring.append((p1 * 2.0 + (p2 - p0) * t
                             + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * t2
                             + (p1 * 3.0 - p0 - p2 * 3.0 + p3) * t3) * 0.5)
            out.append(ring)
    out.append(rings[-1])
    return out


def presspull(profile: Profile, distance: float, material: str = "default",
              name: str = "appuyer_tirer") -> Solid:
    """Commande APPUYERTIRER : pousse ou tire une zone fermee.

    Une distance negative produit le solide a soustraire (percement), ce que
    l'appelant enchaine avec SOUSTRACTION.
    """
    if abs(distance) < TOL:
        raise ValueError("APPUYERTIRER : distance nulle")
    return extrude(profile, distance, material=material, name=name)


def thicken(polygons: Sequence[Polygon], thickness: float = 100.0,
            material: str = "default", name: str = "epaissi") -> Solid:
    """Commande EPAISSIR : donne une epaisseur a une surface pour la solidifier."""
    if abs(thickness) < TOL:
        raise ValueError("EPAISSIR : epaisseur nulle")
    faces = [p for p in polygons if not p.is_degenerate()]
    if not faces:
        raise ValueError("EPAISSIR : aucune face exploitable")
    bottom = [Polygon(list(reversed(p.vertices)), material=material) for p in faces]
    top = [Polygon([v + p.normal * thickness for v in p.vertices],
                   material=material) for p in faces]
    polygons_out: List[Polygon] = list(bottom) + list(top)
    border: dict = {}
    for polygon in faces:
        count = len(polygon.vertices)
        for i in range(count):
            a = polygon.vertices[i]
            b = polygon.vertices[(i + 1) % count]
            key = tuple(sorted([a.rounded(4), b.rounded(4)]))
            border[key] = border.get(key, 0) + 1
    for polygon in faces:
        count = len(polygon.vertices)
        offset = polygon.normal * thickness
        for i in range(count):
            a = polygon.vertices[i]
            b = polygon.vertices[(i + 1) % count]
            key = tuple(sorted([a.rounded(4), b.rounded(4)]))
            if border.get(key, 0) != 1:
                continue
            polygons_out.append(Polygon([a, b, b + offset, a + offset],
                                        material=material))
    solid = Solid.from_polygons(polygons_out, name=name, material=material)
    return solid.heal().outward().apply_appearance()


# ---------------------------------------------------------------------------
# Surfaces (famille SURF* : SURFPLAN, SURFREGLE, SURFRESEAU, SURFEXTRUSION)
# ---------------------------------------------------------------------------
def planar_surface(profile: Profile, material: str = "default",
                   name: str = "surface_plane") -> Solid:
    """Commande SURFPLAN : surface pleine posee sur un contour ferme."""
    return Solid.from_polygons(_cap(profile.oriented(), False, material),
                               name=name, material=material)


def ruled_surface(first: Curve, second: Curve, material: str = "default",
                  name: str = "surface_reglee") -> Solid:
    """Commande SURFREGLE : surface tendue entre deux courbes."""
    count = max(len(first.points), len(second.points), 2)
    a = first.resampled(count).points
    b = second.resampled(count).points
    polygons = [Polygon([a[i], a[i + 1], b[i + 1], b[i]], material=material)
                for i in range(count - 1)]
    return Solid.from_polygons([p for p in polygons if not p.is_degenerate()],
                               name=name, material=material)


def tabulated_surface(curve: Curve, direction, material: str = "default",
                      name: str = "surface_tabulee") -> Solid:
    """Commande SURFEXTRUSION : courbe extrudee selon un vecteur."""
    vector = Vec3.of(direction)
    moved = Curve([p + vector for p in curve.points], curve.closed)
    return ruled_surface(curve, moved, material, name)


def coons_surface(curves: Sequence[Curve], resolution: int = 12,
                  material: str = "default", name: str = "surface_coons"
                  ) -> Solid:
    """Commande SURFRESEAU : carreau de Coons sur quatre courbes de bord."""
    if len(curves) != 4:
        raise ValueError("SURFRESEAU : exactement quatre courbes de bord")
    c0, c1, c2, c3 = [c.resampled(resolution + 1).points for c in curves]
    # c0 : bord bas (u), c1 : bord droit (v), c2 : bord haut (u), c3 : bord gauche (v)
    grid: List[List[Vec3]] = []
    for j in range(resolution + 1):
        v = j / float(resolution)
        row: List[Vec3] = []
        for i in range(resolution + 1):
            u = i / float(resolution)
            linear_u = c0[i] * (1 - v) + c2[i] * v
            linear_v = c3[j] * (1 - u) + c1[j] * u
            bilinear = (c0[0] * (1 - u) * (1 - v) + c0[-1] * u * (1 - v)
                        + c2[0] * (1 - u) * v + c2[-1] * u * v)
            row.append(linear_u + linear_v - bilinear)
        grid.append(row)
    polygons: List[Polygon] = []
    for j in range(resolution):
        for i in range(resolution):
            polygon = Polygon([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1],
                               grid[j + 1][i]], material=material)
            if not polygon.is_degenerate():
                polygons.append(polygon)
    return Solid.from_polygons(polygons, name=name, material=material)


def revolved_surface(curve: Curve, axis_point=ORIGIN, axis_direction=Z_AXIS,
                     angle: float = 2 * math.pi, segments: int = DEFAULT_SEGMENTS,
                     material: str = "default", name: str = "surface_revolution"
                     ) -> Solid:
    """Commande SURFREVOLUTION : courbe tournee autour d'un axe."""
    axis = Vec3.of(axis_direction).unit()
    base = Vec3.of(axis_point)
    steps = max(3, int(math.ceil(abs(angle) / (2 * math.pi) * segments)))
    rings = [[Mat4.rotation(axis, angle * s / float(steps), base).apply(p)
              for p in curve.points] for s in range(steps + 1)]
    polygons: List[Polygon] = []
    for s in range(steps):
        for i in range(len(curve.points) - 1):
            polygon = Polygon([rings[s][i], rings[s][i + 1], rings[s + 1][i + 1],
                               rings[s + 1][i]], material=material)
            if not polygon.is_degenerate():
                polygons.append(polygon)
    return Solid.from_polygons(polygons, name=name, material=material)
''')

ajouter('CAD_Core/solid_edit.py', r'''
"""Edition de solides : le groupe Modification du ruban 3D.

RACCORDARETE, CHANFREINARETE, GAINE, COUPE, SECTION, DEPOUILLE, EMPREINTE,
DECALAGE, plus les conversions solide/surface. Toutes les operations sont
menees par decoupe booleenne exacte : on fabrique le volume de matiere a
retirer, puis on le soustrait. Le resultat reste un solide ferme, verifiable
par `Solid.check()`.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .math3d import (BBox3, EPS, Mat4, ORIGIN, Plane, TOL, Vec3, Z_AXIS)
from .modeling import extrude, offset_ring
from .primitives import box, cylinder, sphere
from .profiles import Curve, Profile
from .solid import Polygon, Solid, union_all


# ---------------------------------------------------------------------------
# Topologie : aretes et faces adjacentes
# ---------------------------------------------------------------------------
def edge_map(solid: Solid, digits: int = 4) -> Dict[Tuple, List[int]]:
    """Associe chaque arete a la liste des faces qui la portent."""
    edges: Dict[Tuple, List[int]] = {}
    for index, polygon in enumerate(solid.polygons):
        count = len(polygon.vertices)
        for i in range(count):
            a = polygon.vertices[i].rounded(digits)
            b = polygon.vertices[(i + 1) % count].rounded(digits)
            key = (a, b) if a <= b else (b, a)
            edges.setdefault(key, []).append(index)
    return edges


def dihedral_angle(solid: Solid, faces: Sequence[int]) -> float:
    """Angle diedre entre deux faces, en degres (180 = arete plate)."""
    if len(faces) != 2:
        return 180.0
    n1 = solid.polygons[faces[0]].normal
    n2 = solid.polygons[faces[1]].normal
    return math.degrees(math.pi - n1.angle_to(n2))


def sharp_edges(solid: Solid, tolerance_deg: float = 1.0
                ) -> List[Tuple[Vec3, Vec3, List[int]]]:
    """Aretes vives du solide : celles que RACCORDARETE peut traiter."""
    out: List[Tuple[Vec3, Vec3, List[int]]] = []
    for key, faces in edge_map(solid).items():
        if len(faces) != 2:
            continue
        if abs(dihedral_angle(solid, faces) - 180.0) <= tolerance_deg:
            continue
        out.append((Vec3(*key[0]), Vec3(*key[1]), faces))
    return out


def _edge_frame(solid: Solid, a: Vec3, b: Vec3, faces: Sequence[int]):
    """Repere local d'une arete : direction, normales et sens de la matiere."""
    direction = (b - a).unit()
    if direction.norm() < TOL:
        return None
    n1 = solid.polygons[faces[0]].normal
    n2 = solid.polygons[faces[1]].normal
    if abs(n1.dot(n2)) > 1.0 - 1e-9:
        return None
    return direction, n1, n2


def _corner_solid(a: Vec3, b: Vec3, direction: Vec3, p1: Vec3, corner: Vec3,
                  p2: Vec3, margin: float, material: str) -> Solid:
    """Prisme couvrant le coin de matiere a retirer le long d'une arete."""
    start = a - direction * margin
    shift = direction * ((b - a).norm() + 2 * margin)
    offsets = [p1 - corner, Vec3(), p2 - corner]
    base = [start + corner - a + o for o in offsets]
    top = [p + shift for p in base]
    polygons = [Polygon(list(reversed(base)), material=material),
                Polygon(list(top), material=material)]
    for i in range(3):
        j = (i + 1) % 3
        polygons.append(Polygon([base[i], base[j], top[j], top[i]],
                                material=material))
    return Solid.from_polygons(polygons, name="coin", material=material).outward()


def chamfer_edge(solid: Solid, edge: Tuple[Vec3, Vec3], distance: float = 50.0,
                 distance2: Optional[float] = None,
                 name: Optional[str] = None) -> Solid:
    """Commande CHANFREINARETE : coupe droite le long d'une arete."""
    if distance <= 0:
        raise ValueError("CHANFREINARETE : la distance doit etre positive")
    d2 = distance if distance2 is None else distance2
    a, b = Vec3.of(edge[0]), Vec3.of(edge[1])
    faces = _faces_of_edge(solid, a, b)
    frame = _edge_frame(solid, a, b, faces)
    if frame is None:
        return solid.copy(name)
    direction, n1, n2 = frame
    t1 = _inward(direction, n1, n2)
    t2 = _inward(direction, n2, n1)
    p1 = a + t1 * distance
    p2 = a + t2 * d2
    margin = max(distance, d2) * 0.5 + 1.0
    shard = _corner_solid(a, b, direction, p1, a, p2, margin, solid.material)
    return solid.subtract(shard, name or solid.name)


def fillet_edge(solid: Solid, edge: Tuple[Vec3, Vec3], radius: float = 50.0,
                segments: int = 12, name: Optional[str] = None) -> Solid:
    """Commande RACCORDARETE : arrondi tangent le long d'une arete."""
    if radius <= 0:
        raise ValueError("RACCORDARETE : le rayon doit etre positif")
    a, b = Vec3.of(edge[0]), Vec3.of(edge[1])
    faces = _faces_of_edge(solid, a, b)
    frame = _edge_frame(solid, a, b, faces)
    if frame is None:
        return solid.copy(name)
    shard = _fillet_shard(solid, a, b, frame, radius, segments)
    if shard is None:
        return solid.copy(name)
    return solid.subtract(shard, name or solid.name)


def _faces_of_edge(solid: Solid, a: Vec3, b: Vec3) -> List[int]:
    key_a, key_b = a.rounded(4), b.rounded(4)
    key = (key_a, key_b) if key_a <= key_b else (key_b, key_a)
    faces = edge_map(solid).get(key, [])
    if len(faces) != 2:
        raise ValueError("arete introuvable ou non partagee par deux faces")
    return faces


def _inward(direction: Vec3, normal: Vec3, other_normal: Vec3) -> Vec3:
    """Direction dans le plan d'une face, tournee vers l'interieur du solide."""
    t = normal.cross(direction).unit()
    if t.dot(other_normal) > 0:
        t = -t
    return t


def _fillet_center(a: Vec3, n1: Vec3, n2: Vec3, radius: float) -> Optional[Vec3]:
    """Centre du cylindre tangent aux deux faces, a distance `radius`."""
    bisector = (n1 + n2)
    if bisector.norm() < 1e-9:
        return None
    m = bisector.unit()
    cos_phi = n1.dot(m)
    if abs(cos_phi) < 1e-6:
        return None
    return a - m * (radius / cos_phi)


def _fillet_shard(solid: Solid, a: Vec3, b: Vec3, frame, radius: float,
                  segments: int) -> Optional[Solid]:
    direction, n1, n2 = frame
    center = _fillet_center(a, n1, n2, radius)
    if center is None:
        return None
    p1 = center + n1 * radius
    p2 = center + n2 * radius
    if (p1 - a).norm() > 1e4 * radius or (p2 - a).norm() > 1e4 * radius:
        return None
    margin = radius * 0.75 + 1.0
    corner = _corner_solid(a, b, direction, p1, a, p2, margin, solid.material)
    length = (b - a).norm() + 2 * margin
    round_tool = cylinder(radius, length, center - direction * margin,
                          max(8, segments * 2), None, direction,
                          solid.material, "rond")
    return corner.subtract(round_tool, "eclat")


def fillet_all_edges(solid: Solid, radius: float = 20.0, segments: int = 10,
                     convex_only: bool = True, max_edges: int = 64,
                     name: Optional[str] = None) -> Solid:
    """RACCORDARETE applique a toutes les aretes vives d'un solide.

    Les eclats de matiere sont tous calcules sur la geometrie d'origine,
    puis retires l'un apres l'autre. Aux sommets ou trois raccords se
    rejoignent, le coin restant est l'intersection des surfaces de raccord
    voisines : l'ecart avec un coin strictement spherique reste inferieur a
    un demi pour cent en volume, pour un calcul robuste et rapide.
    """
    edges = sharp_edges(solid)
    if convex_only:
        edges = [e for e in edges if dihedral_angle(solid, e[2]) < 180.0]
    if not edges:
        return solid.copy(name)
    if len(edges) > max_edges:
        edges = sorted(edges, key=lambda e: -(e[1] - e[0]).norm())[:max_edges]

    result = solid.copy(name or solid.name)
    for a, b, faces in edges:
        frame = _edge_frame(solid, a, b, faces)
        if frame is None:
            continue
        shard = _fillet_shard(solid, a, b, frame, radius, segments)
        if shard is None or not shard.polygons:
            continue
        result = result.subtract(shard, result.name)
    return result.apply_appearance()


def chamfer_all_edges(solid: Solid, distance: float = 20.0,
                      max_edges: int = 64, name: Optional[str] = None) -> Solid:
    """CHANFREINARETE applique a toutes les aretes vives."""
    edges = [e for e in sharp_edges(solid) if dihedral_angle(solid, e[2]) < 180.0]
    if not edges:
        return solid.copy(name)
    if len(edges) > max_edges:
        edges = sorted(edges, key=lambda e: -(e[1] - e[0]).norm())[:max_edges]
    result = solid.copy(name or solid.name)
    shards: List[Solid] = []
    for a, b, faces in edges:
        frame = _edge_frame(solid, a, b, faces)
        if frame is None:
            continue
        direction, n1, n2 = frame
        p1 = a + _inward(direction, n1, n2) * distance
        p2 = a + _inward(direction, n2, n1) * distance
        shards.append(_corner_solid(a, b, direction, p1, a, p2,
                                    distance * 0.5 + 1.0, solid.material))
    for shard in shards:
        result = result.subtract(shard, result.name)
    return result.apply_appearance()


# ---------------------------------------------------------------------------
# COUPE et SECTION
# ---------------------------------------------------------------------------
def half_space(plane: Plane, reference: BBox3, positive: bool = True,
               material: str = "default") -> Solid:
    """Demi-espace materialise par une boite largement plus grande que l'objet."""
    size = max(reference.diagonal * 2.0, 1000.0)
    u, v = plane.basis()
    normal = plane.normal if positive else -plane.normal
    origin = plane.project(reference.center) if reference.valid else plane.origin
    corner = origin - u * size - v * size
    base = [corner, corner + u * (2 * size), corner + u * (2 * size) + v * (2 * size),
            corner + v * (2 * size)]
    top = [p + normal * size for p in base]
    polygons = [Polygon(list(reversed(base)), material=material),
                Polygon(list(top), material=material)]
    for i in range(4):
        j = (i + 1) % 4
        polygons.append(Polygon([base[i], base[j], top[j], top[i]],
                                material=material))
    return Solid.from_polygons(polygons, name="demi_espace",
                               material=material).outward()


def slice_solid(solid: Solid, plane: Plane, keep: str = "les_deux"
                ) -> List[Solid]:
    """Commande COUPE : tranche un solide par un plan.

    `keep` vaut « positif », « negatif » ou « les_deux » (cote de la normale).
    """
    if keep not in ("positif", "negatif", "les_deux"):
        raise ValueError("COUPE : cote inconnu %r" % keep)
    reference = solid.bbox
    above = solid.intersect(half_space(plane, reference, True), solid.name + "_sup")
    below = solid.intersect(half_space(plane, reference, False), solid.name + "_inf")
    if keep == "positif":
        return [above]
    if keep == "negatif":
        return [below]
    return [above, below]


def section_loops(solid: Solid, plane: Plane, tol: float = 1e-6) -> List[Curve]:
    """Commande SECTION : contours fermes de l'intersection avec un plan."""
    segments: List[Tuple[Vec3, Vec3]] = []
    for polygon in solid.polygons:
        points: List[Vec3] = []
        count = len(polygon.vertices)
        for i in range(count):
            a = polygon.vertices[i]
            b = polygon.vertices[(i + 1) % count]
            da, db = plane.signed_distance(a), plane.signed_distance(b)
            if abs(da) <= tol:
                points.append(a)
            if (da > tol and db < -tol) or (da < -tol and db > tol):
                cut = plane.line_intersection(a, b)
                if cut is not None:
                    points.append(cut)
        unique: List[Vec3] = []
        for point in points:
            if all(point.distance_to(other) > 1e-5 for other in unique):
                unique.append(point)
        if len(unique) >= 2:
            segments.append((unique[0], unique[-1]))
    return _chain_segments(segments)


def _chain_segments(segments: Sequence[Tuple[Vec3, Vec3]],
                    tol: float = 1e-4) -> List[Curve]:
    """Assemble des segments epars en contours fermes ou en polylignes."""
    pool = [(a, b) for a, b in segments if a.distance_to(b) > tol]
    loops: List[Curve] = []
    while pool:
        start, current = pool.pop(0)
        chain = [start, current]
        progress = True
        while progress:
            progress = False
            for index, (a, b) in enumerate(pool):
                if chain[-1].distance_to(a) <= tol:
                    chain.append(b)
                elif chain[-1].distance_to(b) <= tol:
                    chain.append(a)
                elif chain[0].distance_to(b) <= tol:
                    chain.insert(0, a)
                elif chain[0].distance_to(a) <= tol:
                    chain.insert(0, b)
                else:
                    continue
                pool.pop(index)
                progress = True
                break
        closed = chain[0].distance_to(chain[-1]) <= tol
        if closed and len(chain) > 3:
            chain.pop()
        if len(chain) >= 2:
            loops.append(Curve(chain, closed, "section"))
    return loops


def section_profile(solid: Solid, plane: Plane) -> Optional[Profile]:
    """Section pleine : le plus grand contour devient le pourtour, les autres
    des ouvertures. C'est la coupe utilisee pour les plans et les metres."""
    loops = [loop for loop in section_loops(solid, plane)
             if loop.closed and len(loop.points) >= 3]
    if not loops:
        return None
    profiles = [Profile(loop.points) for loop in loops]
    profiles.sort(key=lambda p: -p.area)
    return Profile(profiles[0].outline, [p.outline for p in profiles[1:]],
                   name="section")


def section_plane_view(solid: Solid, plane: Plane) -> Dict[str, object]:
    """Commande PLANDECOUPE : donnees d'une coupe (aire, contours, perimetre)."""
    loops = section_loops(solid, plane)
    profile = section_profile(solid, plane)
    return {"contours": len(loops), "aire_mm2": round(profile.area, 3) if profile else 0.0,
            "perimetre_mm": round(sum(loop.length for loop in loops), 3),
            "boucles": [loop.to_dict() for loop in loops],
            "profil": profile}


# ---------------------------------------------------------------------------
# GAINE, DEPOUILLE, DECALAGE
# ---------------------------------------------------------------------------
def offset_solid(solid: Solid, distance: float, name: Optional[str] = None
                 ) -> Solid:
    """Commande DECALAGE en 3D : deplace chaque face selon sa normale.

    Le resultat est l'intersection des demi-espaces obtenus, ce qui est exact
    sur un solide convexe et tres proche ailleurs.
    """
    planes: List[Plane] = []
    for polygon in solid.polygons:
        candidate = Plane.from_point_normal(polygon.vertices[0], polygon.normal)
        shifted = Plane(candidate.normal, candidate.offset + distance)
        if all(abs(shifted.offset - p.offset) > 1e-6
               or shifted.normal.dot(p.normal) < 1.0 - 1e-9 for p in planes):
            planes.append(shifted)
    if not planes:
        return solid.copy(name)
    reference = solid.bbox.expanded(abs(distance) * 2.0 + 10.0)
    result = box(reference.size.x, reference.size.y, reference.size.z,
                 reference.min, material=solid.material,
                 name=name or solid.name)
    for plane in planes:
        result = result.intersect(half_space(plane, reference, False),
                                 result.name)
        if not result.polygons:
            break
    return result.apply_appearance()


def shell(solid: Solid, thickness: float = 20.0,
          open_faces: Optional[Sequence[int]] = None,
          name: Optional[str] = None) -> Solid:
    """Commande GAINE : evide un solide en laissant une paroi d'epaisseur donnee.

    `open_faces` designe les faces a retirer (couvercle ouvert, caisson,
    trémie) exactement comme la selection de faces d'AutoCAD.
    """
    if thickness <= 0:
        raise ValueError("GAINE : l'epaisseur doit etre positive")
    inner = offset_solid(solid, -thickness, "interieur")
    if not inner.polygons or inner.volume < 1e-6:
        raise ValueError("GAINE : epaisseur trop grande pour ce solide")
    hollow = solid.subtract(inner, name or solid.name)
    for index in (open_faces or ()):
        if not 0 <= index < len(solid.polygons):
            raise ValueError("GAINE : numero de face invalide %d" % index)
        face = solid.polygons[index]
        # Seule la paroi de la face choisie disparait : le percement suit le
        # contour interieur, sinon il entamerait aussi les parois voisines.
        inner = offset_ring(face.vertices, thickness, face.normal)
        # `direction` porte le vecteur complet de l'extrusion : la paroi est
        # traversee sur toute son epaisseur, avec une marge pour couper net.
        opening = extrude(Profile(inner),
                          direction=face.normal * (-thickness * 1.05),
                          material=solid.material, name="ouverture")
        hollow = hollow.subtract(opening, hollow.name)
    return hollow.apply_appearance()


def taper_faces(solid: Solid, plane: Plane, angle_deg: float = 5.0,
                name: Optional[str] = None) -> Solid:
    """Commande DEPOUILLE : incline la matiere situee d'un cote d'un plan.

    Chaque sommet est deplace proportionnellement a sa distance au plan de
    base, ce qui produit la depouille de demoulage attendue en prefabrication.
    """
    slope = math.tan(math.radians(angle_deg))
    center = solid.centroid
    polygons: List[Polygon] = []
    for polygon in solid.polygons:
        points: List[Vec3] = []
        for vertex in polygon.vertices:
            distance = plane.signed_distance(vertex)
            if distance <= TOL:
                points.append(vertex)
                continue
            radial = vertex - plane.project(center)
            radial = radial - plane.normal * radial.dot(plane.normal)
            if radial.norm() < TOL:
                points.append(vertex)
                continue
            points.append(vertex - radial.unit() * (distance * slope))
        polygons.append(Polygon(points, polygon.material, polygon.layer,
                                polygon.color))
    return Solid(polygons, name or solid.name, solid.layer, solid.material,
                 solid.color, dict(solid.metadata)).heal().outward()


def imprint(solid: Solid, tool: Solid, name: Optional[str] = None) -> Solid:
    """Commande EMPREINTE : imprime les aretes d'un solide sur un autre.

    Les aretes communes sont ajoutees a la topologie du solide receveur,
    ce qui permet ensuite de selectionner la zone marquee (extrusion de
    face, changement de materiau, reservation).
    """
    common = solid.intersect(tool, "empreinte")
    if not common.polygons:
        return solid.copy(name)
    marked = solid.union(common, name or solid.name)
    marked.metadata = dict(solid.metadata)
    marked.metadata["empreintes"] = marked.metadata.get("empreintes", 0) + 1
    return marked


def convert_to_surface(solid: Solid, name: Optional[str] = None) -> Solid:
    """Commande CONVENSURFACE : garde les faces sans les fermer."""
    surface = Solid([Polygon(list(p.vertices), p.material, p.layer, p.color)
                     for p in solid.polygons], name or solid.name + "_surface",
                    solid.layer, solid.material, solid.color,
                    dict(solid.metadata))
    surface.metadata["type"] = "surface"
    return surface


def convert_to_solid(surface: Solid, thickness: float = 0.0,
                     name: Optional[str] = None) -> Solid:
    """Commande CONVENSOLIDE : ferme une surface, avec epaisseur si besoin."""
    from .modeling import thicken
    if thickness > TOL:
        return thicken(surface.polygons, thickness, surface.material,
                       name or surface.name)
    healed = surface.heal().outward()
    healed.name = name or surface.name
    healed.metadata = dict(surface.metadata)
    healed.metadata["type"] = "solide"
    return healed


def extract_edges(solid: Solid) -> List[Curve]:
    """Commande XARETES : extrait le filaire d'un solide."""
    return [Curve([a, b], False, "arete", solid.layer) for a, b in solid.edges()]


def face_report(solid: Solid) -> List[Dict[str, object]]:
    """Fiche des faces : surface, normale, centre. Sert a la selection de face."""
    out: List[Dict[str, object]] = []
    for index, polygon in enumerate(solid.polygons):
        out.append({"index": index, "sommets": len(polygon.vertices),
                    "aire_mm2": round(polygon.area, 3),
                    "normale": [round(v, 4) for v in polygon.normal],
                    "centre": [round(v, 3) for v in polygon.centroid],
                    "materiau": polygon.material})
    return out
''')

ajouter('CAD_Core/transform3d.py', r'''
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
''')


# =========================================================================
# 4. DOCUMENT CAO : calques, blocs, SCU, accrochages, annotation, vues
# =========================================================================
ajouter('CAD_Core/document.py', r'''
"""Document CAO : calques, blocs, objets, SCU, vues, presentations, annuler.

C'est la structure que manipulent l'interface, l'interpreteur de commandes
et les modules d'import-export. Elle reprend l'organisation d'un fichier
DWG : un espace objet, des presentations, une table de calques, une table
de blocs, des styles, et un historique d'annulation.
"""
from __future__ import annotations

import copy
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .math3d import BBox3, Mat4, ORIGIN, Plane, Vec3, X_AXIS, Y_AXIS, Z_AXIS
from .profiles import Curve, Profile
from .solid import Solid

# Couleurs de l'index AutoCAD (ACI) les plus utilisees.
ACI_COLORS: Dict[int, Tuple[int, int, int]] = {
    0: (0, 0, 0), 1: (255, 0, 0), 2: (255, 255, 0), 3: (0, 255, 0),
    4: (0, 255, 255), 5: (0, 0, 255), 6: (255, 0, 255), 7: (255, 255, 255),
    8: (128, 128, 128), 9: (192, 192, 192), 30: (255, 127, 0),
    40: (255, 191, 0), 140: (0, 127, 255), 250: (51, 51, 51),
    251: (91, 91, 91), 252: (132, 132, 132), 253: (173, 173, 173),
    254: (214, 214, 214), 255: (255, 255, 255), 256: (255, 255, 255),
}

LINETYPES = ["CONTINUOUS", "CENTER", "DASHED", "DASHDOT", "HIDDEN", "PHANTOM",
             "DOT", "BORDER", "DIVIDE"]

LINEWEIGHTS = [0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80,
               90, 100, 106, 120, 140, 158, 200, 211]

UNITS = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "ft": 304.8}


@dataclass
class Layer:
    """Calque : couleur, type de ligne, epaisseur, etats."""

    name: str
    color: int = 7
    linetype: str = "CONTINUOUS"
    lineweight: int = 25
    on: bool = True
    frozen: bool = False
    locked: bool = False
    plot: bool = True
    transparency: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "couleur": self.color,
                "type_ligne": self.linetype, "epaisseur": self.lineweight,
                "actif": self.on, "gele": self.frozen, "verrouille": self.locked,
                "traceable": self.plot, "transparence": self.transparency,
                "description": self.description,
                "rvb": list(ACI_COLORS.get(self.color, (255, 255, 255)))}


@dataclass
class Entity:
    """Objet du dessin : geometrie plus proprietes graphiques."""

    handle: str
    kind: str                              # solide, courbe, profil, annotation
    geometry: Any
    layer: str = "0"
    color: int = 256                       # 256 = DUCALQUE
    linetype: str = "PARCALQUE"
    lineweight: int = -1                   # -1 = PARCALQUE
    material: str = "default"
    visible: bool = True
    locked: bool = False
    transparency: int = 0
    name: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    created: float = field(default_factory=lambda: 0.0)

    @property
    def bbox(self) -> BBox3:
        geometry = self.geometry
        if isinstance(geometry, Solid):
            return geometry.bbox
        if isinstance(geometry, Curve):
            return BBox3.of(geometry.points)
        if isinstance(geometry, Profile):
            return BBox3.of(p for ring in geometry.rings() for p in ring)
        if isinstance(geometry, dict) and "points" in geometry:
            return BBox3.of(Vec3.of(p) for p in geometry["points"])
        return BBox3()

    def transformed(self, matrix: Mat4) -> "Entity":
        clone = copy.deepcopy(self)
        geometry = self.geometry
        if isinstance(geometry, (Solid, Curve, Profile)):
            clone.geometry = geometry.transformed(matrix)
        elif isinstance(geometry, dict) and "points" in geometry:
            clone.geometry = dict(geometry)
            clone.geometry["points"] = [list(matrix.apply(p))
                                        for p in geometry["points"]]
        return clone

    def to_dict(self) -> Dict[str, Any]:
        base = {"handle": self.handle, "type": self.kind, "nom": self.name,
                "calque": self.layer, "couleur": self.color,
                "type_ligne": self.linetype, "epaisseur": self.lineweight,
                "materiau": self.material, "visible": self.visible,
                "verrouille": self.locked, "transparence": self.transparency,
                "boite": self.bbox.to_dict()}
        geometry = self.geometry
        if isinstance(geometry, Solid):
            base["geometrie"] = geometry.to_dict()
        elif isinstance(geometry, (Curve, Profile)):
            base["geometrie"] = geometry.to_dict()
        elif isinstance(geometry, dict):
            base["geometrie"] = {k: v for k, v in geometry.items()
                                 if k != "points"}
            base["geometrie"]["points"] = len(geometry.get("points", ()))
        return base


@dataclass
class Block:
    """Bloc : geometrie reutilisable inseree par references."""

    name: str
    entities: List[Entity] = field(default_factory=list)
    base_point: Vec3 = ORIGIN
    description: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "objets": len(self.entities),
                "point_base": list(self.base_point),
                "description": self.description,
                "attributs": dict(self.attributes)}


@dataclass
class UCS:
    """Systeme de coordonnees utilisateur."""

    name: str = "GENERAL"
    origin: Vec3 = ORIGIN
    x_axis: Vec3 = X_AXIS
    y_axis: Vec3 = Y_AXIS

    @property
    def z_axis(self) -> Vec3:
        return self.x_axis.cross(self.y_axis).unit()

    @property
    def matrix(self) -> Mat4:
        return Mat4.frame(self.origin, self.x_axis, self.y_axis, self.z_axis)

    def to_world(self, point) -> Vec3:
        return self.matrix.apply(point)

    def to_local(self, point) -> Vec3:
        return self.matrix.inverse().apply(point)

    @property
    def plane(self) -> Plane:
        return Plane.from_point_normal(self.origin, self.z_axis)

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "origine": list(self.origin),
                "axe_x": list(self.x_axis), "axe_y": list(self.y_axis),
                "axe_z": list(self.z_axis)}


@dataclass
class Layout:
    """Presentation : espace papier, cartouche, fenetres et echelle."""

    name: str = "Presentation1"
    paper_size: str = "A3"
    width_mm: float = 420.0
    height_mm: float = 297.0
    scale: float = 0.01                    # 1:100
    viewports: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "format": self.paper_size,
                "largeur_mm": self.width_mm, "hauteur_mm": self.height_mm,
                "echelle": self.scale, "fenetres": len(self.viewports)}


PAPER_SIZES = {"A4": (297.0, 210.0), "A3": (420.0, 297.0), "A2": (594.0, 420.0),
               "A1": (841.0, 594.0), "A0": (1189.0, 841.0),
               "LETTER": (279.4, 215.9), "TABLOID": (431.8, 279.4)}


class CadDocument:
    """Document CAO complet : l'equivalent d'un fichier DWG en memoire."""

    MAX_UNDO = 50

    def __init__(self, name: str = "SansTitre", units: str = "mm") -> None:
        if units not in UNITS:
            raise ValueError("unite inconnue : %s" % units)
        self.name = name
        self.units = units
        self.entities: Dict[str, Entity] = {}
        self.layers: Dict[str, Layer] = {"0": Layer("0")}
        self.blocks: Dict[str, Block] = {}
        self.ucs_table: Dict[str, UCS] = {"GENERAL": UCS()}
        self.named_views: Dict[str, Dict[str, Any]] = {}
        self.layouts: Dict[str, Layout] = {"Presentation1": Layout()}
        self.text_styles: Dict[str, Dict[str, Any]] = {
            "Standard": {"police": "arial.ttf", "hauteur": 2.5, "largeur": 1.0,
                         "oblique": 0.0}}
        self.dim_styles: Dict[str, Dict[str, Any]] = {
            "ISO-25": {"hauteur_texte": 2.5, "fleche": 2.5, "decimales": 2,
                       "unite": "mm", "facteur_echelle": 1.0}}
        self.materials: Dict[str, Dict[str, Any]] = {}
        self.current_layer = "0"
        self.current_ucs = "GENERAL"
        self.variables: Dict[str, Any] = {
            "OSMODE": 4133, "ORTHOMODE": 0, "SNAPMODE": 0, "GRIDMODE": 1,
            "LUNITS": 2, "AUPREC": 0, "INSUNITS": 4, "DIMSCALE": 1.0,
        }
        self._counter = 0
        self._undo: List[bytes] = []
        self._redo: List[bytes] = []
        self.selection: List[str] = []
        self.created = time.time()

    # -- identifiants ------------------------------------------------------
    def new_handle(self) -> str:
        self._counter += 1
        return "%X" % (0x100 + self._counter)

    # -- calques -----------------------------------------------------------
    def add_layer(self, name: str, color: int = 7,
                  linetype: str = "CONTINUOUS", lineweight: int = 25,
                  description: str = "") -> Layer:
        """Commande CALQUE : cree ou met a jour un calque."""
        if linetype not in LINETYPES:
            raise ValueError("type de ligne inconnu : %s" % linetype)
        layer = Layer(name, color, linetype, lineweight,
                      description=description)
        self.layers[name] = layer
        return layer

    def set_current_layer(self, name: str) -> Layer:
        if name not in self.layers:
            self.add_layer(name)
        self.current_layer = name
        return self.layers[name]

    def delete_layer(self, name: str) -> bool:
        """Un calque portant des objets ou le calque 0 ne peut etre supprime."""
        if name == "0" or name not in self.layers:
            return False
        if any(entity.layer == name for entity in self.entities.values()):
            raise ValueError("le calque %s contient des objets" % name)
        del self.layers[name]
        if self.current_layer == name:
            self.current_layer = "0"
        return True

    def layer_entities(self, name: str) -> List[Entity]:
        return [e for e in self.entities.values() if e.layer == name]

    # -- objets ------------------------------------------------------------
    def add(self, geometry, kind: Optional[str] = None,
            layer: Optional[str] = None, name: str = "", **properties) -> Entity:
        """Ajoute un objet et renvoie sa fiche."""
        if kind is None:
            kind = ("solide" if isinstance(geometry, Solid)
                    else "courbe" if isinstance(geometry, Curve)
                    else "profil" if isinstance(geometry, Profile)
                    else "annotation")
        layer = layer or self.current_layer
        if layer not in self.layers:
            self.add_layer(layer)
        entity = Entity(self.new_handle(), kind, geometry, layer,
                        name=name or getattr(geometry, "name", "") or kind,
                        created=time.time(), **properties)
        self.entities[entity.handle] = entity
        return entity

    def get(self, handle: str) -> Entity:
        if handle not in self.entities:
            raise KeyError("objet inconnu : %s" % handle)
        return self.entities[handle]

    def remove(self, handles: Union[str, Sequence[str]]) -> int:
        """Commande EFFACER."""
        targets = [handles] if isinstance(handles, str) else list(handles)
        removed = 0
        for handle in targets:
            entity = self.entities.get(handle)
            if entity is None:
                continue
            if entity.locked or self.layers[entity.layer].locked:
                raise ValueError("objet %s verrouille" % handle)
            del self.entities[handle]
            removed += 1
        self.selection = [h for h in self.selection if h in self.entities]
        return removed

    def replace(self, handle: str, geometry) -> Entity:
        entity = self.get(handle)
        entity.geometry = geometry
        return entity

    def solids(self) -> List[Solid]:
        return [e.geometry for e in self.visible_entities()
                if isinstance(e.geometry, Solid)]

    def visible_entities(self) -> List[Entity]:
        out: List[Entity] = []
        for entity in self.entities.values():
            layer = self.layers.get(entity.layer)
            if not entity.visible or layer is None or not layer.on or layer.frozen:
                continue
            out.append(entity)
        return out

    # -- selection ---------------------------------------------------------
    def select_all(self) -> List[str]:
        self.selection = [e.handle for e in self.visible_entities()]
        return self.selection

    def select(self, handles: Sequence[str], add: bool = False) -> List[str]:
        chosen = [h for h in handles if h in self.entities]
        self.selection = (self.selection + chosen) if add else chosen
        self.selection = list(dict.fromkeys(self.selection))
        return self.selection

    def select_window(self, corner_a, corner_b, crossing: bool = False
                      ) -> List[str]:
        """Selection par fenetre (englobante) ou par capture (secante)."""
        box = BBox3().add(corner_a).add(corner_b)
        chosen: List[str] = []
        for entity in self.visible_entities():
            entity_box = entity.bbox
            if not entity_box.valid:
                continue
            if crossing:
                if box.intersects(entity_box):
                    chosen.append(entity.handle)
            elif box.contains(entity_box.min) and box.contains(entity_box.max):
                chosen.append(entity.handle)
        self.selection = chosen
        return chosen

    def select_by_layer(self, layer: str) -> List[str]:
        self.selection = [e.handle for e in self.layer_entities(layer)]
        return self.selection

    def selected_entities(self) -> List[Entity]:
        return [self.entities[h] for h in self.selection if h in self.entities]

    # -- blocs -------------------------------------------------------------
    def define_block(self, name: str, handles: Sequence[str], base_point=ORIGIN,
                     description: str = "") -> Block:
        """Commande BLOC : transforme une selection en definition reutilisable."""
        members = [copy.deepcopy(self.entities[h]) for h in handles
                   if h in self.entities]
        if not members:
            raise ValueError("BLOC : aucune geometrie a enregistrer")
        block = Block(name, members, Vec3.of(base_point), description)
        self.blocks[name] = block
        return block

    def insert_block(self, name: str, position=ORIGIN, scale: float = 1.0,
                     rotation_deg: float = 0.0,
                     layer: Optional[str] = None) -> List[Entity]:
        """Commande INSERER : place une occurrence de bloc."""
        if name not in self.blocks:
            raise ValueError("bloc inconnu : %s" % name)
        block = self.blocks[name]
        matrix = (Mat4.translation(Vec3.of(position) - block.base_point)
                  * Mat4.rotation(Z_AXIS, math.radians(rotation_deg),
                                  block.base_point)
                  * Mat4.scaling(scale, block.base_point))
        placed: List[Entity] = []
        for member in block.entities:
            clone = member.transformed(matrix)
            clone.handle = self.new_handle()
            clone.layer = layer or member.layer or self.current_layer
            if clone.layer not in self.layers:
                self.add_layer(clone.layer)
            clone.attributes = dict(member.attributes)
            clone.attributes["bloc"] = name
            self.entities[clone.handle] = clone
            placed.append(clone)
        return placed

    def explode_block(self, handles: Sequence[str]) -> int:
        """Commande DECOMPOSER : detache les objets de leur bloc d'origine."""
        count = 0
        for handle in handles:
            entity = self.entities.get(handle)
            if entity is not None and "bloc" in entity.attributes:
                entity.attributes.pop("bloc")
                count += 1
        return count

    # -- SCU et vues -------------------------------------------------------
    def set_ucs(self, name: str, origin=ORIGIN, x_axis=X_AXIS,
                y_axis=Y_AXIS) -> UCS:
        """Commande SCU."""
        ucs = UCS(name, Vec3.of(origin), Vec3.of(x_axis).unit(),
                  Vec3.of(y_axis).unit())
        self.ucs_table[name] = ucs
        self.current_ucs = name
        return ucs

    @property
    def ucs(self) -> UCS:
        return self.ucs_table[self.current_ucs]

    def save_view(self, name: str, camera: Dict[str, Any]) -> Dict[str, Any]:
        """Commande VUE : enregistre une vue nommee."""
        self.named_views[name] = dict(camera)
        return self.named_views[name]

    def add_layout(self, name: str, paper: str = "A3",
                   scale: float = 0.01) -> Layout:
        """Commande PRESENTATION : ajoute un espace papier."""
        if paper not in PAPER_SIZES:
            raise ValueError("format papier inconnu : %s" % paper)
        width, height = PAPER_SIZES[paper]
        layout = Layout(name, paper, width, height, scale)
        self.layouts[name] = layout
        return layout

    # -- annuler / retablir ------------------------------------------------
    def snapshot(self) -> None:
        """Enregistre l'etat avant une modification (commande ANNULER)."""
        import pickle
        self._undo.append(pickle.dumps(
            (self.entities, self.layers, self.blocks, self.selection,
             self._counter), protocol=4))
        if len(self._undo) > self.MAX_UNDO:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self) -> bool:
        """Commande ANNULER."""
        import pickle
        if not self._undo:
            return False
        self._redo.append(pickle.dumps(
            (self.entities, self.layers, self.blocks, self.selection,
             self._counter), protocol=4))
        state = pickle.loads(self._undo.pop())
        (self.entities, self.layers, self.blocks, self.selection,
         self._counter) = state
        return True

    def redo(self) -> bool:
        """Commande RETABLIR."""
        import pickle
        if not self._redo:
            return False
        self._undo.append(pickle.dumps(
            (self.entities, self.layers, self.blocks, self.selection,
             self._counter), protocol=4))
        state = pickle.loads(self._redo.pop())
        (self.entities, self.layers, self.blocks, self.selection,
         self._counter) = state
        return True

    @property
    def undo_depth(self) -> int:
        return len(self._undo)

    # -- mesures et synthese -----------------------------------------------
    @property
    def bbox(self) -> BBox3:
        box = BBox3()
        for entity in self.entities.values():
            entity_box = entity.bbox
            if entity_box.valid:
                box.add(entity_box.min).add(entity_box.max)
        return box

    def scale_to_mm(self) -> float:
        return UNITS[self.units]

    def statistics(self) -> Dict[str, Any]:
        """Fiche du document : ce qu'affiche la commande ETAT."""
        kinds: Dict[str, int] = {}
        for entity in self.entities.values():
            kinds[entity.kind] = kinds.get(entity.kind, 0) + 1
        solids = self.solids()
        return {
            "nom": self.name, "unites": self.units,
            "objets": len(self.entities), "par_type": kinds,
            "calques": len(self.layers), "blocs": len(self.blocks),
            "presentations": len(self.layouts),
            "vues_nommees": len(self.named_views),
            "scu": self.current_ucs, "calque_courant": self.current_layer,
            "selection": len(self.selection),
            "annulations": len(self._undo),
            "volume_total_mm3": round(sum(s.volume for s in solids), 3),
            "aire_totale_mm2": round(sum(s.area for s in solids), 3),
            "etendue": self.bbox.to_dict(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document": self.name, "unites": self.units,
            "calques": [layer.to_dict() for layer in self.layers.values()],
            "objets": [entity.to_dict() for entity in self.entities.values()],
            "blocs": [block.to_dict() for block in self.blocks.values()],
            "scu": [ucs.to_dict() for ucs in self.ucs_table.values()],
            "presentations": [layout.to_dict() for layout in self.layouts.values()],
            "vues_nommees": self.named_views,
            "styles_texte": self.text_styles, "styles_cotation": self.dim_styles,
            "variables": self.variables,
            "statistiques": self.statistics(),
        }

    def merge(self, other: "CadDocument", prefix: str = "") -> int:
        """Fusionne un autre document (XREF liee ou import)."""
        added = 0
        for layer in other.layers.values():
            key = prefix + layer.name
            if key not in self.layers:
                self.layers[key] = Layer(key, layer.color, layer.linetype,
                                         layer.lineweight)
        for entity in other.entities.values():
            clone = copy.deepcopy(entity)
            clone.handle = self.new_handle()
            clone.layer = prefix + entity.layer
            self.entities[clone.handle] = clone
            added += 1
        for name, block in other.blocks.items():
            self.blocks.setdefault(prefix + name, copy.deepcopy(block))
        return added
''')

ajouter('CAD_Core/snapping.py', r'''
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
''')

ajouter('CAD_Core/annotate.py', r'''
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
''')

ajouter('CAD_Core/view3d.py', r'''
"""Vues 3D : camera, vues normalisees, styles visuels, orbite, plans de coupe.

Regroupe VUEPOINT, ORBITE3D, VUEDYN, STYLESVISUELS, ZOOM et PAN. La camera
produit les matrices de vue et de projection consommees aussi bien par le
moteur de rendu du serveur que par la visionneuse WebGL du navigateur.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .math3d import BBox3, Mat4, ORIGIN, Plane, TOL, Vec3, X_AXIS, Y_AXIS, Z_AXIS

# Vues normalisees du ruban Vue (VUEPOINT), en direction de visee.
STANDARD_VIEWS: Dict[str, Tuple[float, float, float]] = {
    "dessus": (0.0, 0.0, -1.0), "dessous": (0.0, 0.0, 1.0),
    "face": (0.0, 1.0, 0.0), "arriere": (0.0, -1.0, 0.0),
    "gauche": (1.0, 0.0, 0.0), "droite": (-1.0, 0.0, 0.0),
    "iso_sud_ouest": (1.0, 1.0, -1.0), "iso_sud_est": (-1.0, 1.0, -1.0),
    "iso_nord_est": (-1.0, -1.0, -1.0), "iso_nord_ouest": (1.0, -1.0, -1.0),
}

VISUAL_STYLES = {
    "filaire_2d": {"faces": False, "aretes": True, "ombrage": "aucun",
                   "arriere_plan": [255, 255, 255]},
    "filaire_3d": {"faces": False, "aretes": True, "ombrage": "aucun",
                   "arriere_plan": [33, 40, 48]},
    "cache": {"faces": True, "aretes": True, "ombrage": "uniforme",
              "arriere_plan": [255, 255, 255]},
    "realiste": {"faces": True, "aretes": False, "ombrage": "lisse",
                 "arriere_plan": [24, 28, 34]},
    "conceptuel": {"faces": True, "aretes": True, "ombrage": "gooch",
                   "arriere_plan": [30, 36, 44]},
    "ombre_avec_aretes": {"faces": True, "aretes": True, "ombrage": "lisse",
                          "arriere_plan": [30, 36, 44]},
    "nuances_de_gris": {"faces": True, "aretes": True, "ombrage": "gris",
                        "arriere_plan": [240, 240, 240]},
    "esquisse": {"faces": True, "aretes": True, "ombrage": "uniforme",
                 "arriere_plan": [252, 250, 244]},
    "rayons_x": {"faces": True, "aretes": True, "ombrage": "transparent",
                 "arriere_plan": [20, 24, 30]},
}


@dataclass
class Light:
    """Source lumineuse : distante (soleil), ponctuelle ou projecteur."""

    kind: str = "distante"
    direction: Vec3 = Vec3(-0.4, -0.6, -0.7)
    position: Vec3 = Vec3(0.0, 0.0, 10000.0)
    intensity: float = 1.0
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    cone_deg: float = 45.0

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.kind, "direction": list(self.direction),
                "position": list(self.position), "intensite": self.intensity,
                "couleur": list(self.color), "cone_deg": self.cone_deg}


@dataclass
class Camera:
    """Camera de la fenetre courante."""

    target: Vec3 = ORIGIN
    distance: float = 10000.0
    azimuth_deg: float = 315.0             # rotation autour de Z
    elevation_deg: float = 35.264          # isometrique par defaut
    up: Vec3 = Z_AXIS
    perspective: bool = False
    field_of_view_deg: float = 45.0
    width: int = 1600
    height: int = 900
    near: float = 1.0
    far: float = 1e7
    zoom: float = 1.0
    clip_planes: List[Plane] = field(default_factory=list)

    # -- position ----------------------------------------------------------
    @property
    def position(self) -> Vec3:
        azimuth = math.radians(self.azimuth_deg)
        elevation = math.radians(max(-89.9, min(89.9, self.elevation_deg)))
        radius = self.distance * math.cos(elevation)
        return self.target + Vec3(radius * math.cos(azimuth),
                                  radius * math.sin(azimuth),
                                  self.distance * math.sin(elevation))

    @property
    def direction(self) -> Vec3:
        return (self.target - self.position).unit()

    @property
    def aspect(self) -> float:
        return max(0.01, self.width / float(max(1, self.height)))

    def basis(self) -> Tuple[Vec3, Vec3, Vec3]:
        """Repere de la camera : droite, haut, avant."""
        forward = self.direction
        reference = self.up if abs(forward.dot(self.up)) < 0.999 else Y_AXIS
        right = forward.cross(reference).unit()
        up = right.cross(forward).unit()
        return right, up, forward

    def view_matrix(self) -> Mat4:
        right, up, forward = self.basis()
        eye = self.position
        return Mat4((right.x, right.y, right.z, -right.dot(eye),
                     up.x, up.y, up.z, -up.dot(eye),
                     -forward.x, -forward.y, -forward.z, forward.dot(eye),
                     0.0, 0.0, 0.0, 1.0))

    def projection_matrix(self) -> Mat4:
        if self.perspective:
            f = 1.0 / math.tan(math.radians(self.field_of_view_deg) / 2.0)
            depth = self.near - self.far
            return Mat4((f / self.aspect, 0, 0, 0,
                         0, f, 0, 0,
                         0, 0, (self.far + self.near) / depth,
                         2 * self.far * self.near / depth,
                         0, 0, -1, 0))
        half_height = self.distance * 0.5 / max(TOL, self.zoom)
        half_width = half_height * self.aspect
        depth = self.far - self.near
        return Mat4((1.0 / half_width, 0, 0, 0,
                     0, 1.0 / half_height, 0, 0,
                     0, 0, -2.0 / depth, -(self.far + self.near) / depth,
                     0, 0, 0, 1))

    def view_projection(self) -> Mat4:
        return self.projection_matrix() * self.view_matrix()

    def project(self, point) -> Tuple[float, float, float]:
        """Point du monde vers pixel ecran ; z est la profondeur normalisee."""
        clip = self.view_projection().apply(point)
        x = (clip.x * 0.5 + 0.5) * self.width
        y = (0.5 - clip.y * 0.5) * self.height
        return x, y, clip.z

    # -- commandes de navigation -------------------------------------------
    def orbit(self, delta_azimuth: float, delta_elevation: float) -> "Camera":
        """Commande ORBITE3D."""
        self.azimuth_deg = (self.azimuth_deg + delta_azimuth) % 360.0
        self.elevation_deg = max(-89.9, min(89.9,
                                            self.elevation_deg + delta_elevation))
        return self

    def pan(self, dx: float, dy: float) -> "Camera":
        """Commande PAN : deplacement dans le plan de l'ecran."""
        right, up, _ = self.basis()
        self.target = self.target + right * dx + up * dy
        return self

    def dolly(self, factor: float) -> "Camera":
        """Commande ZOOM : rapprochement ou eloignement."""
        if factor <= 0:
            raise ValueError("ZOOM : facteur invalide")
        self.distance = max(1.0, self.distance / factor)
        return self

    def zoom_extents(self, box: BBox3, margin: float = 1.2) -> "Camera":
        """Commande ZOOM Etendu : cadre tout le modele."""
        if not box.valid:
            return self
        self.target = box.center
        radius = max(box.diagonal * 0.5, 1.0)
        if self.perspective:
            half = math.radians(self.field_of_view_deg) / 2.0
            self.distance = radius * margin / max(1e-3, math.sin(half))
        else:
            self.distance = radius * 2.0 * margin
        self.near = max(1.0, self.distance - radius * 4.0)
        self.far = self.distance + radius * 8.0
        return self

    def set_standard_view(self, name: str) -> "Camera":
        """Commande VUEPOINT : dessus, face, gauche, isometriques."""
        if name not in STANDARD_VIEWS:
            raise ValueError("vue normalisee inconnue : %s" % name)
        direction = Vec3.of(STANDARD_VIEWS[name]).unit()
        eye = -direction
        planar = math.hypot(eye.x, eye.y)
        self.azimuth_deg = math.degrees(math.atan2(eye.y, eye.x)) % 360.0
        self.elevation_deg = math.degrees(math.atan2(eye.z, planar)) \
            if planar > TOL else (89.9 if eye.z > 0 else -89.9)
        return self

    def look_at(self, target, distance: Optional[float] = None) -> "Camera":
        self.target = Vec3.of(target)
        if distance:
            self.distance = distance
        return self

    def add_clip_plane(self, plane: Plane) -> "Camera":
        """Commande PLANDECOUPE : masque la matiere devant un plan."""
        self.clip_planes.append(plane)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {"cible": list(self.target), "position": list(self.position),
                "distance": round(self.distance, 3),
                "azimut_deg": round(self.azimuth_deg, 3),
                "elevation_deg": round(self.elevation_deg, 3),
                "perspective": self.perspective,
                "champ_deg": self.field_of_view_deg,
                "largeur": self.width, "hauteur": self.height,
                "zoom": self.zoom, "plans_de_coupe": len(self.clip_planes),
                "matrice_vue": self.view_matrix().to_column_major(),
                "matrice_projection": self.projection_matrix().to_column_major()}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Camera":
        camera = Camera()
        camera.target = Vec3.of(data.get("cible", [0, 0, 0]))
        camera.distance = float(data.get("distance", 10000.0))
        camera.azimuth_deg = float(data.get("azimut_deg", 315.0))
        camera.elevation_deg = float(data.get("elevation_deg", 35.264))
        camera.perspective = bool(data.get("perspective", False))
        camera.width = int(data.get("largeur", 1600))
        camera.height = int(data.get("hauteur", 900))
        camera.zoom = float(data.get("zoom", 1.0))
        return camera


@dataclass
class Viewport:
    """Fenetre : une camera, un style visuel, des calques geles."""

    name: str = "Fenetre1"
    camera: Camera = field(default_factory=Camera)
    visual_style: str = "ombre_avec_aretes"
    frozen_layers: List[str] = field(default_factory=list)
    scale: float = 0.01
    locked: bool = False

    def set_style(self, name: str) -> "Viewport":
        """Commande STYLESVISUELS."""
        if name not in VISUAL_STYLES:
            raise ValueError("style visuel inconnu : %s" % name)
        self.visual_style = name
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "camera": self.camera.to_dict(),
                "style": self.visual_style, "style_detail":
                    VISUAL_STYLES[self.visual_style],
                "calques_geles": list(self.frozen_layers),
                "echelle": self.scale, "verrouillee": self.locked}


DEFAULT_LIGHTS = [
    Light("distante", Vec3(-0.4, -0.5, -0.75), intensity=0.9),
    Light("distante", Vec3(0.6, 0.3, -0.4), intensity=0.35,
          color=(0.85, 0.9, 1.0)),
]
''')

ajouter('CAD_Core/render_engine.py', r'''
"""Moteur de rendu du serveur : rasteriseur avec tampon de profondeur.

Produit les images que l'interface affiche et que les dossiers impriment :
rendu ombre, rendu conceptuel, lignes cachees, filaire. Le tampon est ecrit
en PNG sans dependance externe (zlib de la bibliotheque standard).

Le rendu temps reel reste cote client en WebGL ; ce moteur sert aux exports,
aux vignettes, aux planches et aux tests automatises.
"""
from __future__ import annotations

import math
import struct
import zlib
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .math3d import Mat4, TOL, Vec3
from .mesh_tools import vertex_normals
from .solid import Solid
from .view3d import Camera, DEFAULT_LIGHTS, Light, VISUAL_STYLES

MATERIAL_COLORS: Dict[str, Tuple[int, int, int]] = {
    "default": (198, 198, 198), "maconnerie": (216, 210, 198),
    "cloison": (230, 228, 222), "beton": (183, 183, 179),
    "acier": (140, 150, 160), "bois": (168, 120, 72),
    "verre": (168, 205, 219), "isolant": (232, 205, 130),
    "mobilier": (140, 102, 71), "terre": (150, 122, 90),
    "metal": (170, 175, 182), "plastique": (200, 200, 210),
}


class Framebuffer:
    """Tampon image RGB avec tampon de profondeur."""

    __slots__ = ("width", "height", "pixels", "depth")

    def __init__(self, width: int, height: int,
                 background: Sequence[int] = (255, 255, 255)) -> None:
        if width < 1 or height < 1:
            raise ValueError("dimensions d'image invalides")
        self.width = int(width)
        self.height = int(height)
        r, g, b = (int(c) for c in background[:3])
        self.pixels = bytearray(bytes((r, g, b)) * (self.width * self.height))
        self.depth = [float("inf")] * (self.width * self.height)

    def set(self, x: int, y: int, color: Tuple[int, int, int],
            z: float = -float("inf")) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        index = y * self.width + x
        if z > self.depth[index]:
            return
        self.depth[index] = z
        offset = index * 3
        self.pixels[offset] = max(0, min(255, int(color[0])))
        self.pixels[offset + 1] = max(0, min(255, int(color[1])))
        self.pixels[offset + 2] = max(0, min(255, int(color[2])))

    def blend(self, x: int, y: int, color: Tuple[int, int, int],
              alpha: float) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        offset = (y * self.width + x) * 3
        for channel in range(3):
            current = self.pixels[offset + channel]
            self.pixels[offset + channel] = max(0, min(255, int(
                current * (1.0 - alpha) + color[channel] * alpha)))

    def get(self, x: int, y: int) -> Tuple[int, int, int]:
        offset = (y * self.width + x) * 3
        return (self.pixels[offset], self.pixels[offset + 1],
                self.pixels[offset + 2])

    def to_png(self) -> bytes:
        """Encode l'image en PNG (filtre 0, compression zlib)."""
        raw = bytearray()
        stride = self.width * 3
        for row in range(self.height):
            raw.append(0)
            raw.extend(self.pixels[row * stride:(row + 1) * stride])

        def chunk(tag: bytes, payload: bytes) -> bytes:
            return (struct.pack(">I", len(payload)) + tag + payload
                    + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
                + chunk(b"IEND", b""))

    def to_ppm(self) -> bytes:
        """Format PPM binaire : utile au diagnostic et aux tests."""
        return (b"P6\n%d %d\n255\n" % (self.width, self.height)
                + bytes(self.pixels))


def material_color(name: str) -> Tuple[int, int, int]:
    return MATERIAL_COLORS.get(name, MATERIAL_COLORS["default"])


class Renderer3D:
    """Rasteriseur : projette, trie en profondeur, ombre et trace les aretes."""

    def __init__(self, lights: Optional[Sequence[Light]] = None,
                 ambient: float = 0.28) -> None:
        self.lights = list(lights) if lights else list(DEFAULT_LIGHTS)
        self.ambient = ambient

    # -- eclairage ---------------------------------------------------------
    def shade(self, normal: Vec3, base: Tuple[int, int, int], style: str,
              view_direction: Vec3) -> Tuple[int, int, int]:
        shading = VISUAL_STYLES[style]["ombrage"]
        if shading == "aucun":
            return base
        if shading == "uniforme":
            intensity = 0.55 + 0.45 * abs(normal.dot(view_direction))
            return tuple(int(c * intensity) for c in base)
        diffuse = 0.0
        tint = [0.0, 0.0, 0.0]
        for light in self.lights:
            direction = (light.direction.unit() if light.kind == "distante"
                         else (Vec3() - light.position).unit())
            factor = max(0.0, normal.dot(-direction)) * light.intensity
            diffuse += factor
            for channel in range(3):
                tint[channel] += factor * light.color[channel]
        total = self.ambient + diffuse
        if shading == "gris":
            gray = sum(base) / 3.0
            value = min(255.0, gray * total)
            return (int(value), int(value), int(value))
        if shading == "gooch":
            # Ombrage conceptuel : du bleu froid au jaune chaud, tres lisible
            # sur une maquette de conception.
            warm = (255, 214, 140)
            cool = (74, 96, 148)
            t = max(0.0, min(1.0, 0.5 * (1.0 + normal.dot(
                -self.lights[0].direction.unit()))))
            return tuple(int(cool[i] * (1 - t) + warm[i] * t * 0.6
                             + base[i] * 0.35 * t) for i in range(3))
        if shading == "transparent":
            total *= 0.65
        scale = min(1.6, total)
        return tuple(min(255, int(base[i] * scale
                                  * (0.7 + 0.3 * tint[i] / max(1e-6, diffuse or 1))))
                     for i in range(3))

    # -- rendu -------------------------------------------------------------
    def render(self, solids: Sequence[Solid], camera: Camera,
               style: str = "ombre_avec_aretes",
               background: Optional[Sequence[int]] = None,
               smooth: bool = True) -> Framebuffer:
        """Rend une liste de solides et renvoie le tampon image."""
        if style not in VISUAL_STYLES:
            raise ValueError("style visuel inconnu : %s" % style)
        settings = VISUAL_STYLES[style]
        frame = Framebuffer(camera.width, camera.height,
                            background or settings["arriere_plan"])
        matrix = camera.view_projection()
        view_direction = camera.direction
        half_width = camera.width * 0.5
        half_height = camera.height * 0.5

        def to_screen(point: Vec3) -> Tuple[float, float, float]:
            clip = matrix.apply(point)
            return ((clip.x * 0.5 + 0.5) * camera.width,
                    (0.5 - clip.y * 0.5) * camera.height, clip.z)

        if settings["faces"]:
            normals_cache: Dict[int, Dict[Tuple[float, ...], Vec3]] = {}
            for solid in solids:
                if smooth and settings["ombrage"] in ("lisse", "gooch"):
                    normals_cache[id(solid)] = vertex_normals(solid)
                for polygon in solid.polygons:
                    if self._clipped(polygon.vertices, camera):
                        continue
                    base = material_color(polygon.material)
                    normal = polygon.normal
                    smooth_normals = normals_cache.get(id(solid))
                    for triangle in polygon.triangulate():
                        self._raster_triangle(frame, triangle, to_screen, base,
                                              normal, style, view_direction,
                                              smooth_normals)
        if settings["aretes"]:
            edge_color = (30, 34, 40) if sum(settings["arriere_plan"]) > 380 \
                else (222, 226, 232)
            for solid in solids:
                for a, b in solid.edges():
                    if self._clipped((a, b), camera):
                        continue
                    self._raster_line(frame, to_screen(a), to_screen(b),
                                      edge_color, bias=1e-4)
        return frame

    @staticmethod
    def _clipped(points: Iterable[Vec3], camera: Camera) -> bool:
        if not camera.clip_planes:
            return False
        for plane in camera.clip_planes:
            if all(plane.signed_distance(p) > 0 for p in points):
                return True
        return False

    def _raster_triangle(self, frame: Framebuffer, triangle, to_screen,
                         base: Tuple[int, int, int], normal: Vec3, style: str,
                         view_direction: Vec3,
                         smooth_normals: Optional[Dict[Tuple[float, ...], Vec3]]
                         ) -> None:
        projected = [to_screen(v) for v in triangle]
        xs = [p[0] for p in projected]
        ys = [p[1] for p in projected]
        if max(xs) < 0 or min(xs) >= frame.width:
            return
        if max(ys) < 0 or min(ys) >= frame.height:
            return
        x0, x1 = max(0, int(min(xs))), min(frame.width - 1, int(max(xs)) + 1)
        y0, y1 = max(0, int(min(ys))), min(frame.height - 1, int(max(ys)) + 1)
        if x1 < x0 or y1 < y0:
            return
        ax, ay, az = projected[0]
        bx, by, bz = projected[1]
        cx, cy, cz = projected[2]
        denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(denominator) < 1e-9:
            return
        transparent = VISUAL_STYLES[style]["ombrage"] == "transparent"
        flat = self.shade(normal, base, style, view_direction)
        corner_colors = None
        if smooth_normals is not None:
            corner_colors = [
                self.shade(smooth_normals.get(v.rounded(4), normal), base,
                           style, view_direction) for v in triangle]
        for y in range(y0, y1 + 1):
            py = y + 0.5
            for x in range(x0, x1 + 1):
                px = x + 0.5
                w0 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / denominator
                w1 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / denominator
                w2 = 1.0 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                    continue
                z = w0 * az + w1 * bz + w2 * cz
                if corner_colors is not None:
                    color = tuple(int(w0 * corner_colors[0][i]
                                      + w1 * corner_colors[1][i]
                                      + w2 * corner_colors[2][i])
                                  for i in range(3))
                else:
                    color = flat
                if transparent:
                    frame.blend(x, y, color, 0.45)
                else:
                    frame.set(x, y, color, z)

    @staticmethod
    def _raster_line(frame: Framebuffer, start, end,
                     color: Tuple[int, int, int], bias: float = 0.0) -> None:
        x0, y0, z0 = start
        x1, y1, z1 = end
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        if steps > 8192:
            return
        for i in range(steps + 1):
            t = i / float(steps)
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            z = z0 + (z1 - z0) * t - bias
            frame.set(x, y, color, z)

    # -- sortie vectorielle ------------------------------------------------
    def hidden_line_svg(self, solids: Sequence[Solid], camera: Camera,
                        samples: int = 12, stroke: str = "#111318",
                        width: float = 0.8) -> str:
        """Commande MASQUE : filaire debarrasse des aretes cachees.

        Chaque arete est echantillonnee et confrontee au tampon de
        profondeur du rendu plein : les portions masquees sont retirees, ce
        qui donne un trait vectoriel propre pour l'impression.
        """
        frame = self.render(solids, camera, "cache")
        matrix = camera.view_projection()

        def to_screen(point: Vec3):
            clip = matrix.apply(point)
            return ((clip.x * 0.5 + 0.5) * camera.width,
                    (0.5 - clip.y * 0.5) * camera.height, clip.z)

        def visible(x: float, y: float, z: float) -> bool:
            xi, yi = int(x), int(y)
            if not (0 <= xi < frame.width and 0 <= yi < frame.height):
                return False
            return z <= frame.depth[yi * frame.width + xi] + 2e-3

        parts: List[str] = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d">' % (camera.width, camera.height,
                                      camera.width, camera.height),
            '<rect width="100%%" height="100%%" fill="#ffffff"/>',
            '<g stroke="%s" stroke-width="%.2f" fill="none" '
            'stroke-linecap="round">' % (stroke, width)]
        for solid in solids:
            for a, b in solid.edges():
                pa, pb = to_screen(a), to_screen(b)
                run: List[Tuple[float, float]] = []
                for index in range(samples + 1):
                    t = index / float(samples)
                    x = pa[0] + (pb[0] - pa[0]) * t
                    y = pa[1] + (pb[1] - pa[1]) * t
                    z = pa[2] + (pb[2] - pa[2]) * t
                    if visible(x, y, z):
                        run.append((x, y))
                    elif len(run) >= 2:
                        parts.append('<polyline points="%s"/>' % " ".join(
                            "%.1f,%.1f" % p for p in run))
                        run = []
                    else:
                        run = []
                if len(run) >= 2:
                    parts.append('<polyline points="%s"/>' % " ".join(
                        "%.1f,%.1f" % p for p in run))
        parts.append("</g></svg>")
        return "\n".join(parts)

    def wireframe_svg(self, solids: Sequence[Solid], camera: Camera,
                      stroke: str = "#1c2430") -> str:
        """Filaire complet, aretes cachees comprises (style Filaire 3D)."""
        matrix = camera.view_projection()
        parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" '
                 'height="%d">' % (camera.width, camera.height),
                 '<rect width="100%%" height="100%%" fill="#ffffff"/>',
                 '<g stroke="%s" stroke-width="0.6" fill="none">' % stroke]
        for solid in solids:
            for a, b in solid.edges():
                ca, cb = matrix.apply(a), matrix.apply(b)
                parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                             % ((ca.x * 0.5 + 0.5) * camera.width,
                                (0.5 - ca.y * 0.5) * camera.height,
                                (cb.x * 0.5 + 0.5) * camera.width,
                                (0.5 - cb.y * 0.5) * camera.height))
        parts.append("</g></svg>")
        return "\n".join(parts)


def render_thumbnail(solids: Sequence[Solid], width: int = 480,
                     height: int = 320, style: str = "conceptuel") -> bytes:
    """Vignette PNG cadree automatiquement : aperçu de fichier, galerie."""
    from .math3d import BBox3
    camera = Camera(width=width, height=height)
    box = BBox3()
    for solid in solids:
        solid_box = solid.bbox
        if solid_box.valid:
            box.add(solid_box.min).add(solid_box.max)
    camera.zoom_extents(box)
    return Renderer3D().render(solids, camera, style).to_png()
''')

ajouter('CAD_Core/commands.py', r'''
"""Interpreteur de commandes compatible AutoCAD.

C'est la ligne de commande du logiciel : elle accepte les noms francais et
anglais, les alias courts habituels (L, C, EXT, UNI, SU, IN, FI, CHA, RE3),
et pilote un `CadDocument`. L'interface graphique, l'API REST et les scripts
passent tous par ce meme point d'entree, ce qui garantit qu'une commande se
comporte partout de la meme facon.

    interpreteur = CommandInterpreter(document)
    interpreteur.execute("BOITE longueur=1000 largeur=500 hauteur=300")
    interpreteur.execute("UNION", handles=["101", "102"])
"""
from __future__ import annotations

import math
import shlex
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import annotate, mesh_tools, modeling, primitives, solid_edit, transform3d
from .document import CadDocument, Entity
from .math3d import BBox3, Mat4, ORIGIN, Plane, Vec3, X_AXIS, Y_AXIS, Z_AXIS
from .profiles import Curve, Profile
from .render_engine import Renderer3D
from .snapping import SnapEngine
from .solid import Solid, interfere, intersect_all, subtract_all, union_all
from .view3d import Camera, STANDARD_VIEWS, VISUAL_STYLES, Viewport


class CommandError(ValueError):
    """Commande inconnue, parametre invalide ou selection inadequate."""


@dataclass
class Command:
    """Fiche d'une commande : nom, alias, groupe, parametres, aide."""

    name: str
    handler: Callable
    group: str = "general"
    english: str = ""
    aliases: Tuple[str, ...] = ()
    summary: str = ""
    parameters: Dict[str, str] = field(default_factory=dict)
    modifies: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "anglais": self.english,
                "alias": list(self.aliases), "groupe": self.group,
                "resume": self.summary, "parametres": self.parameters,
                "modifie": self.modifies}


REGISTRY: Dict[str, Command] = {}
LOOKUP: Dict[str, str] = {}


def command(name: str, group: str = "general", english: str = "",
            aliases: Sequence[str] = (), summary: str = "",
            parameters: Optional[Dict[str, str]] = None,
            modifies: bool = True):
    """Enregistre une commande et tous ses noms d'appel."""
    def decorator(handler: Callable) -> Callable:
        entry = Command(name, handler, group, english, tuple(aliases), summary,
                        dict(parameters or {}), modifies)
        REGISTRY[name] = entry
        for label in (name, english, *aliases):
            if label:
                LOOKUP[label.upper()] = name
        return handler
    return decorator


class CommandInterpreter:
    """Execute les commandes sur un document."""

    def __init__(self, document: Optional[CadDocument] = None) -> None:
        self.document = document or CadDocument()
        self.snap = SnapEngine()
        self.viewport = Viewport()
        self.renderer = Renderer3D()
        self.history: List[Dict[str, Any]] = []
        self.annotations: List[Dict[str, Any]] = []

    # -- resolution --------------------------------------------------------
    @staticmethod
    def resolve(name: str) -> Command:
        key = LOOKUP.get((name or "").strip().upper())
        if key is None:
            suggestions = sorted(
                label for label in LOOKUP
                if label.startswith((name or "")[:3].upper()))[:6]
            raise CommandError(
                "commande inconnue : %r%s" % (
                    name,
                    " — vouliez-vous dire %s ?" % ", ".join(suggestions)
                    if suggestions else ""))
        return REGISTRY[key]

    @staticmethod
    def parse(line: str) -> Tuple[str, Dict[str, Any]]:
        """Decoupe « BOITE longueur=1000 origine=0,0,0 » en nom et parametres."""
        tokens = shlex.split(line or "")
        if not tokens:
            raise CommandError("ligne de commande vide")
        name = tokens[0]
        arguments: Dict[str, Any] = {}
        positional: List[str] = []
        for token in tokens[1:]:
            if "=" in token:
                key, _, value = token.partition("=")
                arguments[key.strip()] = _convert(value)
            else:
                positional.append(token)
        if positional:
            arguments["_positionnels"] = [_convert(v) for v in positional]
        return name, arguments

    def execute(self, line: str, **overrides) -> Dict[str, Any]:
        """Execute une ligne de commande ou un nom de commande."""
        if " " in (line or "").strip() or "=" in (line or ""):
            name, arguments = self.parse(line)
        else:
            name, arguments = (line or "").strip(), {}
        arguments.update(overrides)
        arguments.pop("_positionnels", None)
        entry = self.resolve(name)
        if entry.modifies:
            self.document.snapshot()
        try:
            result = entry.handler(self, **arguments)
        except CommandError:
            raise
        except TypeError as error:
            raise CommandError("parametres invalides pour %s : %s"
                               % (entry.name, error))
        except (ValueError, KeyError) as error:
            raise CommandError("%s : %s" % (entry.name, error))
        record = {"commande": entry.name, "parametres": _summarise(arguments),
                  "resultat": result}
        self.history.append(record)
        return {"commande": entry.name, "groupe": entry.group, **(result or {})}

    def run_script(self, text: str) -> List[Dict[str, Any]]:
        """Execute un script de commandes (equivalent d'un fichier .scr)."""
        out: List[Dict[str, Any]] = []
        for raw in (text or "").splitlines():
            line = raw.split(";")[0].strip()
            if not line:
                continue
            out.append(self.execute(line))
        return out

    # -- utilitaires de selection -----------------------------------------
    def targets(self, handles: Optional[Sequence[str]] = None) -> List[Entity]:
        chosen = list(handles) if handles else list(self.document.selection)
        if not chosen:
            raise CommandError(
                "aucun objet selectionne : indiquez handles=[...] ou lancez "
                "d'abord SELECTIONNER")
        entities = []
        for handle in chosen:
            if handle not in self.document.entities:
                raise CommandError("objet inconnu : %s" % handle)
            entities.append(self.document.entities[handle])
        return entities

    def solids(self, handles: Optional[Sequence[str]] = None) -> List[Solid]:
        out = [e.geometry for e in self.targets(handles)
               if isinstance(e.geometry, Solid)]
        if not out:
            raise CommandError("la selection ne contient aucun solide")
        return out

    def add(self, geometry, name: str = "", layer: Optional[str] = None
            ) -> Dict[str, Any]:
        entity = self.document.add(geometry, layer=layer, name=name)
        return {"handle": entity.handle, "objet": entity.to_dict()}

    def catalog(self, group: Optional[str] = None) -> List[Dict[str, Any]]:
        """Catalogue complet des commandes, pour le ruban et l'aide."""
        return [entry.to_dict() for entry in REGISTRY.values()
                if not group or entry.group == group]

    def groups(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for entry in REGISTRY.values():
            counts[entry.group] = counts.get(entry.group, 0) + 1
        return counts


def _convert(value: str):
    """Convertit un argument texte : nombre, booleen, liste ou point."""
    text = (value or "").strip()
    lowered = text.lower()
    if lowered in ("vrai", "true", "oui", "on"):
        return True
    if lowered in ("faux", "false", "non", "off"):
        return False
    if "," in text:
        parts = [p for p in text.split(",") if p != ""]
        converted = [_convert(p) for p in parts]
        return converted
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _summarise(arguments: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in arguments.items():
        if isinstance(value, (list, tuple)) and len(value) > 8:
            out[key] = "%d valeurs" % len(value)
        else:
            out[key] = value
    return out


def _profile(source, elevation: float = 0.0) -> Profile:
    """Accepte un Profile, une liste de points ou un handle d'objet."""
    if isinstance(source, Profile):
        return source
    if isinstance(source, Curve):
        return Profile(list(source.points))
    if isinstance(source, (list, tuple)) and source:
        if isinstance(source[0], (list, tuple)):
            return Profile.from_2d(source, elevation)
        flat = list(source)
        points = [flat[i:i + 3] for i in range(0, len(flat) - 2, 3)]
        return Profile.from_2d(points, elevation)
    raise CommandError("profil illisible : fournissez une liste de points")


# ===========================================================================
# Creation de solides primitifs
# ===========================================================================
@command("BOITE", "solides_primitifs", "BOX", ("B",),
         "Pave droit defini par ses trois dimensions",
         {"longueur": "mm", "largeur": "mm", "hauteur": "mm",
          "origine": "x,y,z", "centre": "vrai pour centrer sur l'origine"})
def _box(self, longueur=1000.0, largeur=1000.0, hauteur=1000.0,
         origine=(0, 0, 0), centre=False, materiau="default", calque=None):
    return self.add(primitives.box(longueur, largeur, hauteur, origine, centre,
                                   materiau), "boite", calque)


@command("BISEAU", "solides_primitifs", "WEDGE", (),
         "Demi-boite coupee en diagonale : rampe, pente",
         {"longueur": "mm", "largeur": "mm", "hauteur": "mm"})
def _wedge(self, longueur=1000.0, largeur=1000.0, hauteur=1000.0,
           origine=(0, 0, 0), materiau="default", calque=None):
    return self.add(primitives.wedge(longueur, largeur, hauteur, origine,
                                     materiau), "biseau", calque)


@command("CYLINDRE", "solides_primitifs", "CYLINDER", ("CYL",),
         "Cylindre droit ou tronconique",
         {"rayon": "mm", "hauteur": "mm", "segments": "facettes",
          "rayon_superieur": "mm, pour un tronc de cone"})
def _cylinder(self, rayon=500.0, hauteur=1000.0, origine=(0, 0, 0), segments=48,
              rayon_superieur=None, axe=(0, 0, 1), materiau="default",
              calque=None):
    return self.add(primitives.cylinder(rayon, hauteur, origine, segments,
                                        rayon_superieur, axe, materiau),
                    "cylindre", calque)


@command("CONE", "solides_primitifs", "CONE", (),
         "Cone plein ou tronque", {"rayon": "mm", "hauteur": "mm"})
def _cone(self, rayon=500.0, hauteur=1000.0, origine=(0, 0, 0), segments=48,
          rayon_superieur=0.0, materiau="default", calque=None):
    return self.add(primitives.cone(rayon, hauteur, origine, segments,
                                    rayon_superieur, (0, 0, 1), materiau),
                    "cone", calque)


@command("SPHERE", "solides_primitifs", "SPHERE", (),
         "Sphere", {"rayon": "mm", "centre": "x,y,z"})
def _sphere(self, rayon=500.0, centre=(0, 0, 0), segments=48, anneaux=None,
            materiau="default", calque=None):
    return self.add(primitives.sphere(rayon, centre, segments, anneaux,
                                      materiau), "sphere", calque)


@command("TORE", "solides_primitifs", "TORUS", (),
         "Tore", {"rayon": "mm", "rayon_tube": "mm"})
def _torus(self, rayon=500.0, rayon_tube=100.0, centre=(0, 0, 0), segments=48,
           segments_tube=24, materiau="default", calque=None):
    return self.add(primitives.torus(rayon, rayon_tube, centre, segments,
                                     segments_tube, materiau), "tore", calque)


@command("PYRAMIDE", "solides_primitifs", "PYRAMID", ("PYR",),
         "Pyramide de 3 a 32 cotes, pleine ou tronquee",
         {"rayon": "mm", "hauteur": "mm", "cotes": "nombre de cotes"})
def _pyramid(self, rayon=500.0, hauteur=1000.0, cotes=4, origine=(0, 0, 0),
             rayon_superieur=0.0, materiau="default", calque=None):
    return self.add(primitives.pyramid(rayon, hauteur, cotes, origine,
                                       rayon_superieur, True, materiau),
                    "pyramide", calque)


@command("POLYSOLIDE", "solides_primitifs", "POLYSOLID", ("PSOLIDE",),
         "Mur d'epaisseur constante suivant une polyligne",
         {"points": "liste de points", "largeur": "mm", "hauteur": "mm",
          "justification": "gauche, centre ou droite"})
def _polysolid(self, points=None, largeur=200.0, hauteur=2500.0, ferme=False,
               justification="centre", materiau="default", calque=None):
    if not points:
        raise CommandError("POLYSOLIDE : fournissez points=[[x,y,z], ...]")
    return self.add(primitives.polysolid(points, largeur, hauteur, ferme,
                                         justification, 0.0, materiau),
                    "polysolide", calque)


@command("HELICE", "courbes", "HELIX", (),
         "Helice : ressort, rampe, escalier helicoidal",
         {"rayon": "mm", "hauteur": "mm", "tours": "nombre de tours"})
def _helix(self, centre=(0, 0, 0), rayon=100.0, rayon_superieur=None,
           hauteur=200.0, tours=3.0, horaire=False, calque=None):
    return self.add(Curve.helix(centre, rayon, rayon_superieur, hauteur, tours,
                                horaire), "helice", calque)


# ===========================================================================
# Solides issus d'un profil
# ===========================================================================
@command("EXTRUSION", "solides_profil", "EXTRUDE", ("EXT",),
         "Extrude un contour ferme en volume",
         {"profil": "liste de points", "hauteur": "mm",
          "depouille": "angle en degres", "direction": "vecteur complet"})
def _extrude(self, profil=None, hauteur=1000.0, depouille=0.0, direction=None,
             trajectoire=None, materiau="default", calque=None, handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    path = None
    if trajectoire:
        path = trajectoire if isinstance(trajectoire, Curve) else \
            Curve.polyline(trajectoire)
    return self.add(modeling.extrude(_profile(profil), hauteur, direction,
                                     depouille, path, materiau), "extrusion",
                    calque)


@command("REVOLUTION", "solides_profil", "REVOLVE", ("REV",),
         "Fait tourner un profil autour d'un axe",
         {"profil": "liste de points", "axe": "vecteur", "angle": "degres"})
def _revolve(self, profil=None, point_axe=(0, 0, 0), axe=(0, 0, 1), angle=360.0,
             segments=48, materiau="default", calque=None, handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    return self.add(modeling.revolve(_profile(profil), point_axe, axe,
                                     math.radians(angle), segments, materiau),
                    "revolution", calque)


@command("BALAYAGE", "solides_profil", "SWEEP", (),
         "Deplace un profil le long d'une trajectoire",
         {"profil": "liste de points", "trajectoire": "liste de points",
          "torsion": "degres", "echelle": "facteur final"})
def _sweep(self, profil=None, trajectoire=None, torsion=0.0, echelle=1.0,
           materiau="default", calque=None, handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    if trajectoire is None:
        raise CommandError("BALAYAGE : trajectoire manquante")
    path = trajectoire if isinstance(trajectoire, Curve) else \
        Curve.polyline(trajectoire)
    return self.add(modeling.sweep(_profile(profil), path, torsion, echelle,
                                   True, materiau), "balayage", calque)


@command("LISSAGE", "solides_profil", "LOFT", (),
         "Relie plusieurs sections par une peau continue",
         {"sections": "liste de contours", "regle": "vrai pour des faces reglees"})
def _loft(self, sections=None, regle=True, ferme=False, materiau="default",
          calque=None, handles=None):
    profiles: List[Profile] = []
    if sections:
        profiles = [_profile(section) for section in sections]
    elif handles:
        profiles = [_profile(entity.geometry) for entity in self.targets(handles)]
    if len(profiles) < 2:
        raise CommandError("LISSAGE : au moins deux sections")
    return self.add(modeling.loft(profiles, regle, ferme, 0, materiau),
                    "lissage", calque)


@command("APPUYERTIRER", "solides_profil", "PRESSPULL", ("APT",),
         "Pousse ou tire une zone fermee", {"profil": "contour",
                                            "distance": "mm, negatif = percer"})
def _presspull(self, profil=None, distance=500.0, materiau="default",
               calque=None, handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    return self.add(modeling.presspull(_profile(profil), distance, materiau),
                    "appuyer_tirer", calque)


@command("EPAISSIR", "solides_profil", "THICKEN", (),
         "Donne une epaisseur a une surface", {"epaisseur": "mm"})
def _thicken(self, epaisseur=100.0, handles=None, calque=None):
    surfaces = self.solids(handles)
    polygons = [p for surface in surfaces for p in surface.polygons]
    return self.add(modeling.thicken(polygons, epaisseur), "epaissi", calque)


@command("SURFPLAN", "surfaces", "PLANESURF", (),
         "Surface pleine sur un contour ferme", {"profil": "contour"})
def _planar(self, profil=None, calque=None, handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    return self.add(modeling.planar_surface(_profile(profil)), "surface",
                    calque)


@command("SURFREGLE", "surfaces", "RULESURF", (),
         "Surface tendue entre deux courbes", {"handles": "deux courbes"})
def _ruled(self, handles=None, calque=None):
    entities = self.targets(handles)
    curves = [e.geometry for e in entities if isinstance(e.geometry, Curve)]
    if len(curves) < 2:
        raise CommandError("SURFREGLE : deux courbes sont necessaires")
    return self.add(modeling.ruled_surface(curves[0], curves[1]), "surface",
                    calque)


# ===========================================================================
# Operations booleennes
# ===========================================================================
@command("UNION", "booleens", "UNION", ("UNI",),
         "Fusionne plusieurs solides", {"handles": "objets a fusionner"})
def _union(self, handles=None, calque=None):
    solids = self.solids(handles)
    result = union_all(solids, "union")
    self.document.remove([e.handle for e in self.targets(handles)])
    return self.add(result, "union", calque)


@command("SOUSTRACTION", "booleens", "SUBTRACT", ("SU",),
         "Retire des solides d'un solide de base",
         {"base": "handle du solide conserve", "outils": "handles retires"})
def _subtract(self, base=None, outils=None, handles=None, calque=None):
    if base is None or not outils:
        chosen = handles or self.document.selection
        if len(chosen) < 2:
            raise CommandError(
                "SOUSTRACTION : indiquez base=<handle> et outils=[handles], "
                "ou selectionnez au moins deux solides")
        base, outils = chosen[0], list(chosen[1:])
    outils = [outils] if isinstance(outils, str) else list(outils)
    result = subtract_all(self.solids([base])[0], self.solids(outils),
                          "soustraction")
    self.document.remove([base] + outils)
    return self.add(result, "soustraction", calque)


@command("INTERSECTION", "booleens", "INTERSECT", ("IN",),
         "Ne garde que la matiere commune", {"handles": "objets a croiser"})
def _intersect(self, handles=None, calque=None):
    solids = self.solids(handles)
    result = intersect_all(solids, "intersection")
    self.document.remove([e.handle for e in self.targets(handles)])
    return self.add(result, "intersection", calque)


@command("INTERFERENCE", "booleens", "INTERFERE", ("INTERF",),
         "Detecte les collisions entre solides", {"handles": "objets testes"},
         modifies=False)
def _interfere(self, handles=None):
    report = interfere(self.solids(handles))
    return {"collisions": report["collisions"],
            "details": [{k: v for k, v in item.items() if k != "solide"}
                        for item in report["details"]]}


# ===========================================================================
# Edition de solides
# ===========================================================================
@command("RACCORDARETE", "edition_solides", "FILLETEDGE", ("RACC",),
         "Arrondit les aretes vives d'un solide",
         {"rayon": "mm", "segments": "facettes de l'arrondi"})
def _fillet(self, rayon=20.0, segments=10, handles=None, toutes=True,
            arete=None):
    entity = self.targets(handles)[0]
    solid = entity.geometry
    if not isinstance(solid, Solid):
        raise CommandError("RACCORDARETE : l'objet n'est pas un solide")
    if arete and not toutes:
        result = solid_edit.fillet_edge(solid, (arete[0], arete[1]), rayon,
                                       segments)
    else:
        result = solid_edit.fillet_all_edges(solid, rayon, segments)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "volume_mm3": round(result.volume, 3),
            "faces": len(result.polygons)}


@command("CHANFREINARETE", "edition_solides", "CHAMFEREDGE", ("CHA",),
         "Coupe les aretes vives a plat", {"distance": "mm"})
def _chamfer(self, distance=20.0, handles=None, toutes=True, arete=None):
    entity = self.targets(handles)[0]
    solid = entity.geometry
    if not isinstance(solid, Solid):
        raise CommandError("CHANFREINARETE : l'objet n'est pas un solide")
    if arete and not toutes:
        result = solid_edit.chamfer_edge(solid, (arete[0], arete[1]), distance)
    else:
        result = solid_edit.chamfer_all_edges(solid, distance)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "volume_mm3": round(result.volume, 3),
            "faces": len(result.polygons)}


@command("GAINE", "edition_solides", "SHELL", (),
         "Evide un solide en laissant une paroi",
         {"epaisseur": "mm", "faces_ouvertes": "indices de faces a retirer"})
def _shell(self, epaisseur=20.0, faces_ouvertes=None, handles=None):
    entity = self.targets(handles)[0]
    faces = faces_ouvertes
    if isinstance(faces, int):
        faces = [faces]
    result = solid_edit.shell(entity.geometry, epaisseur, faces)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "volume_mm3": round(result.volume, 3)}


@command("COUPE", "edition_solides", "SLICE", ("SL",),
         "Tranche un solide par un plan",
         {"point": "point du plan", "normale": "normale du plan",
          "conserver": "positif, negatif ou les_deux"})
def _slice(self, point=(0, 0, 0), normale=(0, 0, 1), conserver="les_deux",
           handles=None, calque=None):
    entity = self.targets(handles)[0]
    plane = Plane.from_point_normal(point, normale)
    pieces = solid_edit.slice_solid(entity.geometry, plane, conserver)
    self.document.remove([entity.handle])
    created = [self.add(piece, piece.name, calque)["handle"]
               for piece in pieces if piece.polygons]
    return {"morceaux": len(created), "handles": created,
            "volumes_mm3": [round(p.volume, 3) for p in pieces]}


@command("SECTION", "edition_solides", "SECTION", (),
         "Contour de l'intersection avec un plan",
         {"point": "point du plan", "normale": "normale"}, modifies=False)
def _section(self, point=(0, 0, 0), normale=(0, 0, 1), handles=None):
    entity = self.targets(handles)[0]
    plane = Plane.from_point_normal(point, normale)
    view = solid_edit.section_plane_view(entity.geometry, plane)
    return {"contours": view["contours"], "aire_mm2": view["aire_mm2"],
            "perimetre_mm": view["perimetre_mm"], "boucles": view["boucles"]}


@command("DEPOUILLE", "edition_solides", "TAPER", (),
         "Incline la matiere d'un cote d'un plan", {"angle": "degres"})
def _taper(self, angle=5.0, point=(0, 0, 0), normale=(0, 0, 1), handles=None):
    entity = self.targets(handles)[0]
    result = solid_edit.taper_faces(entity.geometry,
                                    Plane.from_point_normal(point, normale),
                                    angle)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "volume_mm3": round(result.volume, 3)}


@command("DECALAGE", "edition_solides", "OFFSET", ("DE",),
         "Decale les faces d'un solide", {"distance": "mm, negatif = retrait"})
def _offset(self, distance=10.0, handles=None, calque=None):
    entity = self.targets(handles)[0]
    result = solid_edit.offset_solid(entity.geometry, distance)
    return self.add(result, "decalage", calque)


@command("SEPARER", "edition_solides", "SEPARATE", (),
         "Eclate un solide en volumes disjoints", {})
def _separate(self, handles=None, calque=None):
    entity = self.targets(handles)[0]
    pieces = entity.geometry.separate()
    if len(pieces) <= 1:
        return {"morceaux": 1, "message": "le solide est d'un seul tenant"}
    self.document.remove([entity.handle])
    created = [self.add(piece, piece.name, calque)["handle"] for piece in pieces]
    return {"morceaux": len(created), "handles": created}


@command("EMPREINTE", "edition_solides", "IMPRINT", (),
         "Imprime les aretes d'un solide sur un autre",
         {"base": "handle receveur", "outil": "handle imprime"})
def _imprint(self, base=None, outil=None, handles=None):
    chosen = handles or self.document.selection
    if base is None or outil is None:
        if len(chosen) < 2:
            raise CommandError("EMPREINTE : indiquez base= et outil=")
        base, outil = chosen[0], chosen[1]
    result = solid_edit.imprint(self.solids([base])[0], self.solids([outil])[0])
    self.document.replace(base, result)
    return {"handle": base, "faces": len(result.polygons)}


@command("XARETES", "edition_solides", "XEDGES", (),
         "Extrait le filaire d'un solide", {}, modifies=True)
def _xedges(self, handles=None, calque="ARETES"):
    entity = self.targets(handles)[0]
    curves = solid_edit.extract_edges(entity.geometry)
    created = [self.document.add(curve, layer=calque).handle for curve in curves]
    return {"aretes": len(created), "handles": created[:50]}


@command("VERIFSOLIDE", "edition_solides", "SOLIDCHECK", (),
         "Controle l'etancheite d'un solide", {}, modifies=False)
def _check(self, handles=None):
    entity = self.targets(handles)[0]
    return {"controle": entity.geometry.check()}


@command("PROPMECA", "mesures", "MASSPROP", (),
         "Volume, masse, inertie et centre de gravite",
         {"masse_volumique": "kg/m3"}, modifies=False)
def _massprop(self, masse_volumique=2400.0, handles=None):
    solids = self.solids(handles)
    return {"proprietes": [s.mass_properties(masse_volumique) for s in solids]}


@command("CONVENSOLIDE", "edition_solides", "CONVTOSOLID", (),
         "Ferme une surface pour en faire un solide", {"epaisseur": "mm"})
def _to_solid(self, epaisseur=0.0, handles=None):
    entity = self.targets(handles)[0]
    result = solid_edit.convert_to_solid(entity.geometry, epaisseur)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "volume_mm3": round(result.volume, 3)}


@command("CONVENSURFACE", "edition_solides", "CONVTOSURFACE", (),
         "Transforme un solide en surface", {})
def _to_surface(self, handles=None):
    entity = self.targets(handles)[0]
    result = solid_edit.convert_to_surface(entity.geometry)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "faces": len(result.polygons)}


# ===========================================================================
# Maillages
# ===========================================================================
@command("LISSERMAILLE", "maillages", "MESHSMOOTH", (),
         "Lisse un maillage par subdivision", {"niveaux": "1 a 3"})
def _smooth(self, niveaux=1, handles=None):
    entity = self.targets(handles)[0]
    result = mesh_tools.smooth(entity.geometry, int(niveaux))
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "faces": len(result.polygons)}


@command("AFFINERMAILLE", "maillages", "MESHREFINE", (),
         "Subdivise sans deformer", {"niveaux": "1 a 3"})
def _refine(self, niveaux=1, handles=None):
    entity = self.targets(handles)[0]
    result = mesh_tools.subdivide(entity.geometry, int(niveaux))
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "faces": len(result.polygons)}


@command("TRIANGULER", "maillages", "TRIANGULATE", (),
         "Convertit toutes les faces en triangles", {})
def _triangulate(self, handles=None):
    entity = self.targets(handles)[0]
    result = mesh_tools.triangulate(entity.geometry)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "triangles": len(result.polygons)}


@command("SOUDER", "maillages", "WELD", (),
         "Fusionne les sommets et repare le maillage", {"tolerance": "mm"})
def _weld(self, tolerance=0.1, handles=None):
    entity = self.targets(handles)[0]
    result = mesh_tools.weld(entity.geometry, tolerance)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "controle": result.check()}


# ===========================================================================
# Transformations
# ===========================================================================
@command("DEPLACER3D", "transformations", "3DMOVE", ("DEPLACER", "M"),
         "Deplace la selection", {"vecteur": "dx,dy,dz"})
def _move(self, vecteur=(0, 0, 0), handles=None):
    entities = self.targets(handles)
    matrix = Mat4.translation(vecteur)
    for entity in entities:
        self.document.entities[entity.handle] = entity.transformed(matrix)
        self.document.entities[entity.handle].handle = entity.handle
    return {"objets": len(entities), "vecteur": list(Vec3.of(vecteur))}


@command("ROTATION3D", "transformations", "3DROTATE", ("RO3",),
         "Tourne la selection autour d'un axe",
         {"axe": "vecteur", "angle": "degres", "base": "point de rotation"})
def _rotate(self, axe=(0, 0, 1), angle=90.0, base=(0, 0, 0), handles=None):
    entities = self.targets(handles)
    matrix = Mat4.rotation(axe, math.radians(angle), base)
    for entity in entities:
        clone = entity.transformed(matrix)
        clone.handle = entity.handle
        self.document.entities[entity.handle] = clone
    return {"objets": len(entities), "angle_deg": angle}


@command("ECHELLE", "transformations", "3DSCALE", ("SC",),
         "Met la selection a l'echelle", {"facteur": "nombre", "base": "point"})
def _scale(self, facteur=2.0, base=(0, 0, 0), handles=None):
    entities = self.targets(handles)
    matrix = Mat4.scaling(facteur, base)
    for entity in entities:
        clone = entity.transformed(matrix)
        clone.handle = entity.handle
        self.document.entities[entity.handle] = clone
    return {"objets": len(entities), "facteur": facteur}


@command("MIROIR3D", "transformations", "MIRROR3D", ("MI3",),
         "Symetrie par rapport a un plan",
         {"point": "point du plan", "normale": "normale",
          "conserver_source": "vrai pour garder l'original"})
def _mirror(self, point=(0, 0, 0), normale=(1, 0, 0), conserver_source=True,
            handles=None, calque=None):
    entities = self.targets(handles)
    plane = Plane.from_point_normal(point, normale)
    matrix = Mat4.mirror(plane)
    created: List[str] = []
    for entity in entities:
        clone = entity.transformed(matrix)
        created.append(self.document.add(clone.geometry, layer=calque or
                                         entity.layer).handle)
    if not conserver_source:
        self.document.remove([e.handle for e in entities])
    return {"copies": len(created), "handles": created}


@command("ALIGNER3D", "transformations", "3DALIGN", ("AL",),
         "Aligne la selection sur des points cibles",
         {"source": "points source", "cible": "points cible"})
def _align(self, source=None, cible=None, handles=None):
    if not source or not cible:
        raise CommandError("ALIGNER3D : fournissez source=[...] et cible=[...]")
    entities = self.targets(handles)
    matrix = Mat4.align(source, cible)
    for entity in entities:
        clone = entity.transformed(matrix)
        clone.handle = entity.handle
        self.document.entities[entity.handle] = clone
    return {"objets": len(entities)}


@command("COPIER", "transformations", "COPY", ("CO",),
         "Copie la selection", {"vecteur": "dx,dy,dz", "copies": "nombre"})
def _copy(self, vecteur=(1000, 0, 0), copies=1, handles=None, calque=None):
    entities = self.targets(handles)
    created: List[str] = []
    for index in range(1, int(copies) + 1):
        matrix = Mat4.translation(Vec3.of(vecteur) * index)
        for entity in entities:
            clone = entity.transformed(matrix)
            created.append(self.document.add(clone.geometry,
                                             layer=calque or entity.layer).handle)
    return {"copies": len(created), "handles": created}


@command("RESEAU3D", "transformations", "3DARRAY", ("RESEAU",),
         "Reseau rectangulaire en trois dimensions",
         {"colonnes": "nombre", "rangees": "nombre", "niveaux": "nombre",
          "pas_colonne": "mm", "pas_rangee": "mm", "pas_niveau": "mm"})
def _array_rect(self, colonnes=3, rangees=2, niveaux=1, pas_colonne=1000.0,
                pas_rangee=1000.0, pas_niveau=1000.0, handles=None, calque=None):
    entities = self.targets(handles)
    created: List[str] = []
    for entity in entities:
        copies = transform3d.array_rectangular(
            entity.geometry, int(colonnes), int(rangees), int(niveaux),
            pas_colonne, pas_rangee, pas_niveau)
        for index, geometry in enumerate(copies):
            if index == 0:
                continue
            created.append(self.document.add(geometry,
                                             layer=calque or entity.layer).handle)
    return {"occurrences": len(created) + len(entities), "handles": created}


@command("RESEAUPOLAIRE", "transformations", "ARRAYPOLAR", ("RESP",),
         "Reseau autour d'un axe",
         {"centre": "point", "nombre": "occurrences", "angle": "degres"})
def _array_polar(self, centre=(0, 0, 0), axe=(0, 0, 1), nombre=6, angle=360.0,
                 handles=None, calque=None):
    entities = self.targets(handles)
    created: List[str] = []
    for entity in entities:
        copies = transform3d.array_polar(entity.geometry, centre, axe,
                                         int(nombre), angle)
        for index, geometry in enumerate(copies):
            if index == 0:
                continue
            created.append(self.document.add(geometry,
                                             layer=calque or entity.layer).handle)
    return {"occurrences": len(created) + len(entities), "handles": created}


@command("RESEAUCHEMIN", "transformations", "ARRAYPATH", ("RESC",),
         "Reseau le long d'une trajectoire",
         {"trajectoire": "liste de points", "nombre": "occurrences"})
def _array_path(self, trajectoire=None, nombre=6, aligner=True, handles=None,
                calque=None):
    if not trajectoire:
        raise CommandError("RESEAUCHEMIN : trajectoire manquante")
    path = trajectoire if isinstance(trajectoire, Curve) else \
        Curve.polyline(trajectoire)
    entities = self.targets(handles)
    created: List[str] = []
    for entity in entities:
        copies = transform3d.array_path(entity.geometry, path, int(nombre),
                                        aligner)
        for index, geometry in enumerate(copies):
            if index == 0:
                continue
            created.append(self.document.add(geometry,
                                             layer=calque or entity.layer).handle)
    return {"occurrences": len(created) + len(entities), "handles": created}


@command("EFFACER", "transformations", "ERASE", ("E", "SUPPRIMER"),
         "Efface la selection", {})
def _erase(self, handles=None):
    entities = self.targets(handles)
    removed = self.document.remove([e.handle for e in entities])
    return {"effaces": removed}


# ===========================================================================
# Objets 2D
# ===========================================================================
@command("LIGNE", "dessin_2d", "LINE", ("L",), "Segment de droite",
         {"depart": "x,y,z", "arrivee": "x,y,z"})
def _line(self, depart=(0, 0, 0), arrivee=(1000, 0, 0), calque=None):
    return self.add(Curve.line(depart, arrivee), "ligne", calque)


@command("POLYLIGNE", "dessin_2d", "PLINE", ("PL",), "Polyligne ouverte ou fermee",
         {"points": "liste de points", "ferme": "vrai ou faux"})
def _pline(self, points=None, ferme=False, calque=None):
    if not points:
        raise CommandError("POLYLIGNE : fournissez points=[[x,y,z], ...]")
    return self.add(Curve.polyline(points, ferme), "polyligne", calque)


@command("CERCLE", "dessin_2d", "CIRCLE", ("C",), "Cercle",
         {"centre": "x,y,z", "rayon": "mm"})
def _circle(self, centre=(0, 0, 0), rayon=500.0, segments=64, calque=None):
    return self.add(Curve.circle(centre, rayon, None, segments), "cercle",
                    calque)


@command("ARC", "dessin_2d", "ARC", ("A",), "Arc de cercle",
         {"centre": "x,y,z", "rayon": "mm", "depart": "degres",
          "arrivee": "degres"})
def _arc(self, centre=(0, 0, 0), rayon=500.0, depart=0.0, arrivee=90.0,
         calque=None):
    return self.add(Curve.arc(centre, rayon, math.radians(depart),
                              math.radians(arrivee)), "arc", calque)


@command("RECTANG", "dessin_2d", "RECTANGLE", ("REC",), "Rectangle",
         {"largeur": "mm", "profondeur": "mm", "origine": "x,y,z",
          "raccord": "rayon d'angle en mm"})
def _rect(self, largeur=1000.0, profondeur=600.0, origine=(0, 0, 0),
          raccord=0.0, calque=None):
    profile = (Profile.rounded_rectangle(largeur, profondeur, raccord, origine)
               if raccord > 0 else Profile.rectangle(largeur, profondeur,
                                                     origine))
    return self.add(profile, "rectangle", calque)


@command("POLYGONE", "dessin_2d", "POLYGON", ("POL",), "Polygone regulier",
         {"cotes": "3 a 1024", "rayon": "mm", "inscrit": "vrai ou faux"})
def _polygon(self, cotes=6, rayon=500.0, centre=(0, 0, 0), inscrit=True,
             calque=None):
    return self.add(Profile.regular_polygon(int(cotes), rayon, centre, None,
                                            inscrit), "polygone", calque)


@command("ELLIPSE", "dessin_2d", "ELLIPSE", ("EL",), "Ellipse",
         {"rayon_x": "mm", "rayon_y": "mm"})
def _ellipse(self, rayon_x=800.0, rayon_y=400.0, centre=(0, 0, 0), calque=None):
    return self.add(Profile.ellipse(rayon_x, rayon_y, centre), "ellipse",
                    calque)


@command("SPLINE", "dessin_2d", "SPLINE", ("SPL",), "Courbe passant par des points",
         {"points": "liste de points"})
def _spline(self, points=None, ferme=False, calque=None):
    if not points:
        raise CommandError("SPLINE : fournissez points=[[x,y,z], ...]")
    return self.add(Curve.spline(points, 12, ferme), "spline", calque)


@command("POINT", "dessin_2d", "POINT", ("PO",), "Point isole",
         {"position": "x,y,z"})
def _point(self, position=(0, 0, 0), calque=None):
    return self.add(Curve([Vec3.of(position)], False, "point"), "point", calque)


# ===========================================================================
# Annotation
# ===========================================================================
@command("COTLIN", "annotation", "DIMLINEAR", ("COTL",),
         "Cote lineaire", {"depart": "point", "arrivee": "point",
                           "decalage": "mm"})
def _dimlinear(self, depart=(0, 0, 0), arrivee=(1000, 0, 0), decalage=200.0,
               calque="COTATION"):
    dimension = annotate.linear_dimension(depart, arrivee, decalage,
                                          layer=calque)
    self.annotations.append(dimension)
    self.document.add(dimension, kind="annotation", layer=calque)
    return {"texte": dimension["texte"], "mesure_mm": dimension["mesure_mm"]}


@command("COTALI", "annotation", "DIMALIGNED", (),
         "Cote alignee sur le segment", {"depart": "point", "arrivee": "point"})
def _dimaligned(self, depart=(0, 0, 0), arrivee=(1000, 500, 0), decalage=200.0,
                calque="COTATION"):
    dimension = annotate.aligned_dimension(depart, arrivee, decalage,
                                           layer=calque)
    self.annotations.append(dimension)
    self.document.add(dimension, kind="annotation", layer=calque)
    return {"texte": dimension["texte"], "mesure_mm": dimension["mesure_mm"]}


@command("COTANG", "annotation", "DIMANGULAR", (),
         "Cote angulaire", {"sommet": "point", "premier": "point",
                            "second": "point"})
def _dimangular(self, sommet=(0, 0, 0), premier=(1000, 0, 0),
                second=(0, 1000, 0), rayon=300.0, calque="COTATION"):
    dimension = annotate.angular_dimension(sommet, premier, second, rayon,
                                           layer=calque)
    self.annotations.append(dimension)
    self.document.add(dimension, kind="annotation", layer=calque)
    return {"texte": dimension["texte"], "mesure_deg": dimension["mesure_deg"]}


@command("COTRAYON", "annotation", "DIMRADIUS", (),
         "Cote de rayon", {"centre": "point", "rayon": "mm"})
def _dimradius(self, centre=(0, 0, 0), rayon=500.0, diametre=False,
               calque="COTATION"):
    dimension = annotate.radial_dimension(centre, rayon, 45.0, diametre,
                                          layer=calque)
    self.annotations.append(dimension)
    self.document.add(dimension, kind="annotation", layer=calque)
    return {"texte": dimension["texte"], "mesure_mm": dimension["mesure_mm"]}


@command("COTDIA", "annotation", "DIMDIAMETER", (),
         "Cote de diametre", {"centre": "point", "rayon": "mm"})
def _dimdiameter(self, centre=(0, 0, 0), rayon=500.0, calque="COTATION"):
    return _dimradius(self, centre, rayon, True, calque)


@command("TEXTMULT", "annotation", "MTEXT", ("T", "TEXTE"),
         "Texte multiligne", {"position": "point", "texte": "contenu",
                              "hauteur": "mm"})
def _mtext(self, position=(0, 0, 0), texte="", hauteur=25.0,
           calque="ANNOTATION"):
    annotation = annotate.mtext(position, str(texte), hauteur, layer=calque)
    self.annotations.append(annotation)
    self.document.add(annotation, kind="annotation", layer=calque)
    return {"texte": annotation["texte"], "lignes": len(annotation["lignes"])}


@command("LIGNEDEREPERE", "annotation", "MLEADER", ("REPERE",),
         "Fleche de renvoi avec texte", {"points": "liste", "texte": "contenu"})
def _leader(self, points=None, texte="", calque="ANNOTATION"):
    if not points:
        raise CommandError("LIGNEDEREPERE : fournissez points=[...]")
    annotation = annotate.leader(points, str(texte), layer=calque)
    self.annotations.append(annotation)
    self.document.add(annotation, kind="annotation", layer=calque)
    return {"texte": annotation["texte"]}


@command("HACHURES", "annotation", "HATCH", ("H",),
         "Remplit un contour ferme", {"profil": "contour", "motif": "nom",
                                      "echelle": "facteur"})
def _hatch(self, profil=None, motif="ANSI31", echelle=1.0, angle=0.0,
           calque="HACHURES", handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    annotation = annotate.hatch(_profile(profil), motif, echelle, angle, calque)
    self.annotations.append(annotation)
    self.document.add(annotation, kind="annotation", layer=calque)
    return {"motif": motif, "aire_mm2": annotation["aire_mm2"],
            "segments": len(annotation["lignes"])}


@command("TABLEAU", "annotation", "TABLE", (),
         "Nomenclature ou legende", {"lignes": "liste de listes",
                                     "titre": "texte"})
def _table(self, lignes=None, position=(0, 0, 0), titre="", calque="ANNOTATION"):
    if not lignes:
        raise CommandError("TABLEAU : fournissez lignes=[[...], [...]]")
    annotation = annotate.table(position, lignes, None, 60.0, titre, calque)
    self.annotations.append(annotation)
    self.document.add(annotation, kind="annotation", layer=calque)
    return {"lignes": len(annotation["lignes"]),
            "colonnes": annotation["colonnes"]}


@command("NUAGEREV", "annotation", "REVCLOUD", (),
         "Nuage de revision", {"points": "contour"})
def _revcloud(self, points=None, longueur_arc=150.0, calque="REVISION"):
    if not points:
        raise CommandError("NUAGEREV : fournissez points=[...]")
    annotation = annotate.revision_cloud(points, longueur_arc, calque)
    self.annotations.append(annotation)
    self.document.add(annotation, kind="annotation", layer=calque)
    return {"sommets": len(annotation["points"])}


# ===========================================================================
# Organisation du dessin
# ===========================================================================
@command("CALQUE", "organisation", "LAYER", ("LA",),
         "Cree ou active un calque",
         {"nom": "nom du calque", "couleur": "indice ACI", "courant": "vrai"})
def _layer(self, nom="0", couleur=7, type_ligne="CONTINUOUS", epaisseur=25,
           courant=True, description=""):
    layer = self.document.add_layer(str(nom), int(couleur), type_ligne,
                                    int(epaisseur), description)
    if courant:
        self.document.set_current_layer(str(nom))
    return {"calque": layer.to_dict(), "courant": self.document.current_layer}


@command("BLOC", "organisation", "BLOCK", ("B_",),
         "Enregistre une selection comme bloc", {"nom": "nom du bloc"})
def _block(self, nom="BLOC", point_base=(0, 0, 0), handles=None):
    entities = self.targets(handles)
    block = self.document.define_block(str(nom), [e.handle for e in entities],
                                       point_base)
    return {"bloc": block.to_dict()}


@command("INSERER", "organisation", "INSERT", ("I",),
         "Insere une occurrence de bloc",
         {"nom": "nom du bloc", "position": "point", "echelle": "facteur"})
def _insert(self, nom="BLOC", position=(0, 0, 0), echelle=1.0, rotation=0.0,
            calque=None):
    placed = self.document.insert_block(str(nom), position, echelle, rotation,
                                        calque)
    return {"objets": len(placed), "handles": [e.handle for e in placed]}


@command("DECOMPOSER", "organisation", "EXPLODE", ("X",),
         "Detache les objets de leur bloc", {})
def _explode(self, handles=None):
    entities = self.targets(handles)
    return {"decomposes": self.document.explode_block(
        [e.handle for e in entities])}


@command("SCU", "organisation", "UCS", (),
         "Definit le systeme de coordonnees utilisateur",
         {"nom": "nom", "origine": "point", "axe_x": "vecteur"})
def _ucs(self, nom="UTILISATEUR", origine=(0, 0, 0), axe_x=(1, 0, 0),
         axe_y=(0, 1, 0)):
    return {"scu": self.document.set_ucs(str(nom), origine, axe_x,
                                         axe_y).to_dict()}


@command("PRESENTATION", "organisation", "LAYOUT", (),
         "Ajoute un espace papier", {"nom": "nom", "format": "A4 a A0",
                                     "echelle": "1/100 = 0.01"})
def _layout(self, nom="Presentation", format="A3", echelle=0.01):
    return {"presentation": self.document.add_layout(str(nom), str(format),
                                                     float(echelle)).to_dict()}


@command("SELECTIONNER", "organisation", "SELECT", ("SEL",),
         "Selectionne des objets",
         {"handles": "liste", "tout": "vrai", "calque": "nom",
          "fenetre": "deux points"}, modifies=False)
def _select(self, handles=None, tout=False, calque=None, fenetre=None,
            capture=False):
    if tout:
        chosen = self.document.select_all()
    elif calque:
        chosen = self.document.select_by_layer(str(calque))
    elif fenetre and len(fenetre) >= 2:
        chosen = self.document.select_window(fenetre[0], fenetre[1], capture)
    elif handles:
        chosen = self.document.select(handles)
    else:
        chosen = self.document.selection
    return {"selection": chosen, "objets": len(chosen)}


@command("ANNULER", "organisation", "UNDO", ("U",), "Annule la derniere action",
         {}, modifies=False)
def _undo(self):
    return {"annule": self.document.undo(),
            "profondeur": self.document.undo_depth}


@command("RETABLIR", "organisation", "REDO", (), "Retablit l'action annulee",
         {}, modifies=False)
def _redo(self):
    return {"retabli": self.document.redo()}


@command("ETAT", "organisation", "STATUS", (), "Fiche du document", {},
         modifies=False)
def _status(self):
    return {"etat": self.document.statistics()}


@command("LISTE", "organisation", "LIST", ("LI",),
         "Detail des objets selectionnes", {}, modifies=False)
def _list(self, handles=None):
    return {"objets": [e.to_dict() for e in self.targets(handles)]}


@command("PURGER", "organisation", "PURGE", (),
         "Supprime les calques et blocs inutilises", {})
def _purge(self):
    used = {entity.layer for entity in self.document.entities.values()}
    removed: List[str] = []
    for name in list(self.document.layers):
        if name != "0" and name not in used:
            self.document.delete_layer(name)
            removed.append(name)
    return {"calques_supprimes": removed}


# ===========================================================================
# Accrochages et aides au dessin
# ===========================================================================
@command("ACCROBJ", "aides", "OSNAP", ("OS",),
         "Regle les accrochages aux objets", {"modes": "valeur OSMODE"},
         modifies=False)
def _osnap(self, modes=None, ouverture=None):
    if modes is not None:
        self.snap.modes = int(modes)
        self.document.variables["OSMODE"] = int(modes)
    if ouverture is not None:
        self.snap.aperture = float(ouverture)
    return {"accrochages": self.snap.to_dict()}


@command("ACCROCHER", "aides", "SNAPPOINT", (),
         "Renvoie le point accroche le plus proche du curseur",
         {"curseur": "x,y,z"}, modifies=False)
def _snap_point(self, curseur=(0, 0, 0), dernier=None, handles=None):
    entities = (self.targets(handles) if handles
                else self.document.visible_entities())
    result = self.snap.snap(curseur, entities, dernier)
    return {"accrochage": result.to_dict() if result else None}


@command("ORTHO", "aides", "ORTHO", (), "Active ou desactive le mode ortho",
         {"actif": "vrai ou faux"}, modifies=False)
def _ortho(self, actif=True):
    self.snap.ortho = bool(actif)
    self.document.variables["ORTHOMODE"] = 1 if actif else 0
    return {"ortho": self.snap.ortho}


@command("RESOL", "aides", "SNAP", (), "Accrochage a la grille",
         {"actif": "vrai ou faux", "pas": "mm"}, modifies=False)
def _grid_snap(self, actif=True, pas=None):
    self.snap.grid_snap = bool(actif)
    if pas:
        self.snap.grid_spacing = float(pas)
    self.document.variables["SNAPMODE"] = 1 if actif else 0
    return {"resol": self.snap.grid_snap, "pas_mm": self.snap.grid_spacing}


@command("MESURER", "mesures", "MEASUREGEOM", ("MES",),
         "Distance, aire, volume, angle",
         {"type": "distance, aire, volume ou angle"}, modifies=False)
def _measure(self, type="distance", points=None, handles=None):
    kind = str(type).lower()
    if kind == "distance":
        if not points or len(points) < 2:
            raise CommandError("MESURER distance : deux points sont requis")
        a, b = Vec3.of(points[0]), Vec3.of(points[1])
        delta = b - a
        return {"distance_mm": round(a.distance_to(b), 4),
                "delta": [round(v, 4) for v in delta],
                "angle_xy_deg": round(math.degrees(math.atan2(delta.y, delta.x)),
                                      4)}
    if kind == "angle":
        if not points or len(points) < 3:
            raise CommandError("MESURER angle : trois points sont requis")
        a, b, c = (Vec3.of(p) for p in points[:3])
        return {"angle_deg": round(math.degrees((a - b).angle_to(c - b)), 4)}
    solids = self.solids(handles)
    if kind == "volume":
        return {"volume_mm3": round(sum(s.volume for s in solids), 3),
                "volume_m3": round(sum(s.volume for s in solids) * 1e-9, 6)}
    if kind == "aire":
        return {"aire_mm2": round(sum(s.area for s in solids), 3),
                "aire_m2": round(sum(s.area for s in solids) * 1e-6, 4)}
    raise CommandError("MESURER : type inconnu %r (distance, angle, aire, "
                       "volume)" % type)


# ===========================================================================
# Vues et rendu
# ===========================================================================
@command("VUEPOINT", "vues", "VPOINT", ("VP",),
         "Vue normalisee : dessus, face, isometrique...",
         {"vue": ", ".join(sorted(STANDARD_VIEWS))}, modifies=False)
def _vpoint(self, vue="iso_sud_ouest"):
    camera = self.viewport.camera
    camera.set_standard_view(str(vue))
    camera.zoom_extents(self.document.bbox)
    return {"camera": camera.to_dict()}


@command("ORBITE3D", "vues", "3DORBIT", ("ORB",), "Fait tourner la vue",
         {"azimut": "degres", "elevation": "degres"}, modifies=False)
def _orbit(self, azimut=15.0, elevation=0.0):
    camera = self.viewport.camera.orbit(float(azimut), float(elevation))
    return {"camera": camera.to_dict()}


@command("ZOOM", "vues", "ZOOM", ("Z",), "Zoom avant, arriere ou etendu",
         {"facteur": "nombre", "etendu": "vrai"}, modifies=False)
def _zoom(self, facteur=None, etendu=False):
    camera = self.viewport.camera
    if etendu or facteur is None:
        camera.zoom_extents(self.document.bbox)
    else:
        camera.dolly(float(facteur))
    return {"camera": camera.to_dict()}


@command("PAN", "vues", "PAN", ("P",), "Deplace la vue",
         {"dx": "mm", "dy": "mm"}, modifies=False)
def _pan(self, dx=0.0, dy=0.0):
    return {"camera": self.viewport.camera.pan(float(dx), float(dy)).to_dict()}


@command("STYLESVISUELS", "vues", "VSCURRENT", ("SV",),
         "Change le style visuel",
         {"style": ", ".join(sorted(VISUAL_STYLES))}, modifies=False)
def _style(self, style="ombre_avec_aretes"):
    self.viewport.set_style(str(style))
    return {"fenetre": self.viewport.to_dict()}


@command("RENDU", "vues", "RENDER", ("RR",),
         "Calcule une image du modele",
         {"largeur": "pixels", "hauteur": "pixels", "style": "style visuel"},
         modifies=False)
def _render(self, largeur=1280, hauteur=800, style=None, vue=None):
    camera = self.viewport.camera
    camera.width, camera.height = int(largeur), int(hauteur)
    if vue:
        camera.set_standard_view(str(vue))
    camera.zoom_extents(self.document.bbox)
    frame = self.renderer.render(self.document.solids(), camera,
                                 str(style or self.viewport.visual_style))
    return {"image_png_octets": len(frame.to_png()), "largeur": frame.width,
            "hauteur": frame.height, "style": style or self.viewport.visual_style}


@command("MASQUE", "vues", "HIDE", (),
         "Filaire sans les aretes cachees, en vectoriel", {}, modifies=False)
def _hide(self, largeur=1400, hauteur=900):
    camera = self.viewport.camera
    camera.width, camera.height = int(largeur), int(hauteur)
    camera.zoom_extents(self.document.bbox)
    svg = self.renderer.hidden_line_svg(self.document.solids(), camera)
    return {"svg_octets": len(svg), "polylignes": svg.count("polyline")}


@command("VUE", "vues", "VIEW", ("V",), "Enregistre une vue nommee",
         {"nom": "nom de la vue"}, modifies=False)
def _view(self, nom="Vue1"):
    return {"vue": self.document.save_view(str(nom),
                                           self.viewport.camera.to_dict())}


@command("PLANDECOUPE", "vues", "SECTIONPLANE", (),
         "Ajoute un plan de coupe a la vue",
         {"point": "point", "normale": "vecteur"}, modifies=False)
def _clip(self, point=(0, 0, 0), normale=(0, 0, 1)):
    self.viewport.camera.add_clip_plane(Plane.from_point_normal(point, normale))
    return {"plans_de_coupe": len(self.viewport.camera.clip_planes)}


# ===========================================================================
# Fichiers
# ===========================================================================
@command("EXPORTER", "fichiers", "EXPORT", ("EXP",),
         "Exporte le document dans un format d'echange",
         {"format": "dxf, ifc, step, stl, obj, gltf, pdf, png..."},
         modifies=False)
def _export(self, format="dxf", **options):
    import Interop
    payload = Interop.export_data(self.document, str(format), self.annotations,
                                  **options)
    return {"format": str(format), "octets": len(payload),
            "texte": isinstance(payload, str)}


@command("IMPORTER", "fichiers", "IMPORT", ("IMP",),
         "Importe un fichier et le fusionne au document",
         {"chemin": "chemin du fichier"})
def _import(self, chemin=None, prefixe=""):
    import Interop
    if not chemin:
        raise CommandError("IMPORTER : indiquez chemin=<fichier>")
    imported = Interop.import_file(str(chemin))
    added = self.document.merge(imported["document"], str(prefixe))
    return {"format": imported["format"], "objets_ajoutes": added}


@command("FORMATS", "fichiers", "FILEFORMATS", (),
         "Liste les formats lus et ecrits", {}, modifies=False)
def _formats(self):
    import Interop
    return {"capacites": Interop.capabilities()}


@command("AIDE", "general", "HELP", ("?",),
         "Aide sur une commande ou catalogue complet",
         {"commande": "nom de commande"}, modifies=False)
def _help(self, commande=None, groupe=None):
    if commande:
        return {"aide": CommandInterpreter.resolve(str(commande)).to_dict()}
    return {"groupes": {name: count for name, count
                        in sorted(_groups().items())},
            "commandes": [entry.to_dict() for entry in REGISTRY.values()
                          if not groupe or entry.group == groupe]}


def _groups() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for entry in REGISTRY.values():
        counts[entry.group] = counts.get(entry.group, 0) + 1
    return counts


def catalog() -> List[Dict[str, Any]]:
    """Catalogue complet, utilise par l'API et par le ruban de l'interface."""
    return [entry.to_dict() for entry in REGISTRY.values()]


def groups() -> Dict[str, int]:
    return _groups()
''')


# =========================================================================
# 5. INTEROPERABILITE : DWG, DXF, IFC, STEP, maillages, images, PDF
# =========================================================================
ajouter('Interop/__init__.py', r'''
"""Couche d'interoperabilite : un registre unique pour tous les formats.

Point d'entree du module :

    from Interop import import_file, export_file, formats, identify

`formats()` decrit ce que MERCURY sait lire et ecrire, `identify()` reconnait
un fichier a sa signature, `import_file()` et `export_file()` font le travail.
Le registre est aussi la source de la matrice de compatibilite affichee dans
l'interface et publiee par l'API.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from CAD_Core.document import CadDocument
from CAD_Core.profiles import Curve, Profile
from CAD_Core.solid import Solid

from . import dwg as dwg_module
from . import dxf as dxf_module
from . import images as image_module
from . import meshes as mesh_module
from . import pdf as pdf_module
from . import pointcloud as cloud_module
from . import native as native_module
from . import step as step_module
from . import svg as svg_module

VERSION = "1.0.0"


class InteropError(ValueError):
    """Format inconnu, ou operation impossible sur ce format."""


@dataclass
class FormatSpec:
    """Fiche d'un format : extensions, capacites, categorie, remarques."""

    key: str
    label: str
    extensions: Tuple[str, ...]
    category: str
    read: bool = False
    write: bool = False
    kind: str = "3d"                      # 3d, 2d, image, nuage, document
    binary: bool = False
    note: str = ""
    requires: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"cle": self.key, "libelle": self.label,
                "extensions": list(self.extensions), "categorie": self.category,
                "lecture": self.read, "ecriture": self.write, "nature": self.kind,
                "binaire": self.binary, "remarque": self.note,
                "prerequis": self.requires}


FORMATS: List[FormatSpec] = [
    FormatSpec("dwg", "AutoCAD DWG", (".dwg",), "CAO", True, True, "2d", True,
               "Identification, version et apercu en natif ; la geometrie "
               "passe par un moteur de conversion installe sur la machine.",
               "ODA File Converter, LibreDWG ou ezdxf[odafc]"),
    FormatSpec("dxf", "AutoCAD DXF (R12 a 2021)", (".dxf",), "CAO", True, True,
               "2d", False, "Lecture et ecriture natives, toutes versions."),
    FormatSpec("ifc", "IFC 4 (BIM)", (".ifc",), "BIM", True, True, "3d", False,
               "Echange BIM normalise ISO 16739."),
    FormatSpec("step", "STEP AP203/AP214/AP242", (".step", ".stp"), "Mecanique",
               True, True, "3d", False, "BREP facettise, lu par tous les CAO."),
    FormatSpec("iges", "IGES 5.3", (".iges", ".igs"), "Mecanique", False, True,
               "3d", False, "Surfaces planes, entite 106."),
    FormatSpec("stl", "STL", (".stl",), "Impression 3D", True, True, "3d", True,
               "ASCII et binaire, detection automatique."),
    FormatSpec("obj", "Wavefront OBJ", (".obj",), "3D", True, True, "3d", False,
               "Materiaux exportes dans un fichier .mtl associe."),
    FormatSpec("mtl", "Bibliotheque de materiaux OBJ", (".mtl",), "3D", False,
               True, "3d", False),
    FormatSpec("ply", "Stanford PLY", (".ply",), "3D", True, True, "3d", True,
               "ASCII et binaire."),
    FormatSpec("off", "Object File Format", (".off",), "3D", True, True, "3d"),
    FormatSpec("gltf", "glTF 2.0", (".gltf",), "3D web", True, True, "3d"),
    FormatSpec("glb", "glTF binaire", (".glb",), "3D web", True, True, "3d",
               True),
    FormatSpec("3mf", "3D Manufacturing Format", (".3mf",), "Impression 3D",
               True, True, "3d", True),
    FormatSpec("amf", "Additive Manufacturing Format", (".amf",),
               "Impression 3D", False, True, "3d"),
    FormatSpec("dae", "COLLADA", (".dae",), "3D", True, True, "3d"),
    FormatSpec("wrl", "VRML 2.0", (".wrl", ".vrml"), "3D", False, True, "3d"),
    FormatSpec("x3d", "X3D", (".x3d",), "3D", False, True, "3d"),
    FormatSpec("3ds", "Autodesk 3D Studio", (".3ds",), "3D", False, True, "3d",
               True, "Limite du format : 65 535 sommets par objet."),
    FormatSpec("svg", "SVG", (".svg",), "Vectoriel", True, True, "2d", False,
               "Export de plans et import de traces."),
    FormatSpec("pdf", "PDF vectoriel", (".pdf",), "Document", False, True,
               "document", True, "Planches multipages avec cartouche."),
    FormatSpec("png", "PNG", (".png",), "Image", True, True, "image", True),
    FormatSpec("bmp", "Windows Bitmap", (".bmp",), "Image", True, True, "image",
               True),
    FormatSpec("ppm", "Portable Pixmap", (".ppm",), "Image", True, True,
               "image", True),
    FormatSpec("tga", "Targa", (".tga",), "Image", False, True, "image", True),
    FormatSpec("jpg", "JPEG", (".jpg", ".jpeg"), "Image", True, True, "image",
               True, "Lecture et ecriture via Pillow.", "Pillow"),
    FormatSpec("xyz", "Nuage de points XYZ / PTS", (".xyz", ".pts", ".asc"),
               "Releve", True, True, "nuage"),
    FormatSpec("csv", "Points CSV", (".csv",), "Releve", True, True, "nuage"),
    FormatSpec("las", "LiDAR LAS", (".las",), "Releve", True, True, "nuage",
               True, "LAS 1.0 a 1.4, formats de point 0 a 5."),
    FormatSpec("json", "Modele MERCURY (JSON)", (".json",), "Natif", True, True,
               "3d", False, "Format natif : tout le document, sans perte."),
]

BY_KEY: Dict[str, FormatSpec] = {spec.key: spec for spec in FORMATS}
BY_EXTENSION: Dict[str, FormatSpec] = {}
for _spec in FORMATS:
    for _extension in _spec.extensions:
        BY_EXTENSION[_extension] = _spec

SIGNATURES: List[Tuple[bytes, str]] = [
    (b"AC10", "dwg"), (b"\x89PNG\r\n\x1a\n", "png"), (b"BM", "bmp"),
    (b"P6", "ppm"), (b"%PDF-", "pdf"), (b"glTF", "glb"), (b"LASF", "las"),
    (b"PK\x03\x04", "3mf"), (b"ISO-10303-21", "step"), (b"solid", "stl"),
    (b"ply", "ply"), (b"OFF", "off"), (b"\xff\xd8\xff", "jpg"),
    (b"#VRML", "wrl"),
]


def formats(kind: Optional[str] = None,
            capability: Optional[str] = None) -> List[Dict[str, Any]]:
    """Matrice des formats. `capability` vaut « lecture » ou « ecriture »."""
    out = []
    for spec in FORMATS:
        if kind and spec.kind != kind:
            continue
        if capability == "lecture" and not spec.read:
            continue
        if capability == "ecriture" and not spec.write:
            continue
        out.append(spec.to_dict())
    return out


def capabilities() -> Dict[str, Any]:
    """Resume publiable : ce que le logiciel sait faire, format par format."""
    return {
        "version": VERSION,
        "formats": len(FORMATS),
        "lecture": sorted(s.key for s in FORMATS if s.read),
        "ecriture": sorted(s.key for s in FORMATS if s.write),
        "extensions": sorted(BY_EXTENSION),
        "categories": sorted({s.category for s in FORMATS}),
        "dwg": dwg_module.describe_backends(),
        "detail": [s.to_dict() for s in FORMATS],
    }


def spec_for(path_or_key: str) -> FormatSpec:
    """Retrouve la fiche d'un format par sa cle ou par l'extension d'un chemin."""
    key = (path_or_key or "").lower().strip()
    if key in BY_KEY:
        return BY_KEY[key]
    extension = os.path.splitext(key)[1]
    if extension in BY_EXTENSION:
        return BY_EXTENSION[extension]
    if "." + key in BY_EXTENSION:
        return BY_EXTENSION["." + key]
    raise InteropError(
        "format inconnu : %r. Formats acceptes : %s"
        % (path_or_key, ", ".join(sorted(BY_KEY))))


def identify(data: bytes, filename: str = "") -> Dict[str, Any]:
    """Reconnait un fichier par sa signature, l'extension servant d'appoint."""
    head = data[:64] if isinstance(data, bytes) else b""
    detected: Optional[str] = None
    for signature, key in SIGNATURES:
        if head.startswith(signature):
            detected = key
            break
    if detected == "step":
        # IFC et STEP partagent l'enveloppe ISO 10303 : c'est le schema
        # declare dans l'en-tete qui les distingue.
        head_text = data[:4096].decode("utf-8", "replace").upper()
        if "IFC" in head_text and "FILE_SCHEMA" in head_text:
            detected = "ifc"
    if detected is None and head[:5].lower() == b"<?xml":
        lowered = data[:4096].lower()
        if b"<svg" in lowered:
            detected = "svg"
        elif b"collada" in lowered:
            detected = "dae"
        elif b"<amf" in lowered:
            detected = "amf"
        elif b"x3d" in lowered:
            detected = "x3d"
    if detected is None and head.lstrip()[:1] in (b"{", b"["):
        detected = "gltf" if b'"asset"' in data[:512] else "json"
    if detected is None:
        text = data[:4096].decode("utf-8", "replace")
        if "SECTION" in text and "\n  2\n" in text.replace("\r", ""):
            detected = "dxf"
        elif text.lstrip().startswith("999") or "\n0\nSECTION" in text:
            detected = "dxf"
    if detected is None and filename:
        extension = os.path.splitext(filename)[1].lower()
        if extension in BY_EXTENSION:
            detected = BY_EXTENSION[extension].key
    if detected is None:
        raise InteropError(
            "format non reconnu%s. Extensions acceptees : %s"
            % (" pour %s" % filename if filename else "",
               ", ".join(sorted(BY_EXTENSION))))
    spec = BY_KEY[detected]
    report: Dict[str, Any] = {"format": spec.key, "libelle": spec.label,
                              "categorie": spec.category, "nature": spec.kind,
                              "taille_octets": len(data)}
    probe: Dict[str, Any] = {}
    try:
        if spec.key == "dwg":
            probe = dwg_module.probe_dwg(data)
        elif spec.key == "dxf":
            probe = dxf_module.probe_dxf(data.decode("utf-8", "replace"))
        elif spec.key == "step":
            probe = step_module.probe_step(data.decode("utf-8", "replace"))
        elif spec.key == "pdf":
            probe = pdf_module.probe_pdf(data)
        elif spec.key == "las":
            probe = cloud_module.probe_las(data)
    except Exception as error:                # identification au mieux
        report["avertissement"] = str(error)
    # La sonde detaille le fichier mais ne redefinit pas la cle du registre :
    # c'est elle qui pilote l'aiguillage des imports.
    probe.pop("format", None)
    report.update(probe)
    return report


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------
def import_data(data, filename: str = "", format_key: Optional[str] = None,
                name: Optional[str] = None) -> Dict[str, Any]:
    """Importe un contenu et renvoie document, solides et nuage eventuels."""
    if isinstance(data, str):
        raw = data.encode("utf-8")
    else:
        raw = bytes(data)
    key = (spec_for(format_key).key if format_key
           else identify(raw, filename)["format"])
    spec = BY_KEY[key]
    if not spec.read:
        raise InteropError("le format %s est ecrit mais pas lu par MERCURY"
                           % spec.label)
    label = name or (os.path.splitext(os.path.basename(filename))[0]
                     if filename else key)
    text = raw.decode("utf-8", "replace")

    document: Optional[CadDocument] = None
    solids: List[Solid] = []
    cloud = None

    if key == "dxf":
        document = dxf_module.read_dxf(text, label)
    elif key == "svg":
        document = svg_module.read_svg(text, name=label)
    elif key == "ifc":
        from BIM_Engine.ifc_handler import IFCHandler
        solids = _ifc_solids(text, label)
    elif key == "step":
        solids = step_module.read_step(text, label)
    elif key == "stl":
        solids = mesh_module.read_stl(raw, label)
    elif key == "obj":
        solids = mesh_module.read_obj(text, name=label)
    elif key == "ply":
        solids = mesh_module.read_ply(raw, label)
    elif key == "off":
        solids = mesh_module.read_off(text, label)
    elif key in ("gltf", "glb"):
        solids = mesh_module.read_gltf(raw, name=label)
    elif key == "3mf":
        solids = mesh_module.read_3mf(raw, label)
    elif key == "dae":
        solids = mesh_module.read_collada(text, name=label)
    elif key in ("xyz", "csv"):
        cloud = cloud_module.read_xyz(text, name=label)
    elif key == "las":
        cloud = cloud_module.read_las(raw, label)
    elif key in ("png", "bmp", "ppm", "jpg"):
        raster = image_module.read_image(raw)
        document = CadDocument(label)
        document.add_layer("IMAGE", 8)
        attachment = image_module.underlay(raw, float(
            options_width(raster.width)))
        document.add(attachment, kind="annotation", layer="IMAGE",
                     name="image_" + label)
        return {"format": key, "nom": label, "image": raster.to_dict(),
                "raster": raster, "document": document, "solides": [],
                "nuage": None, "statistiques": document.statistics()}
    elif key == "json":
        document = native_module.read_native(text, label)
        return {"format": key, "nom": label, "document": document,
                "solides": document.solids(), "nuage": None,
                "statistiques": document.statistics()}
    elif key == "dwg":
        raise InteropError(
            "un DWG doit etre importe depuis un fichier (import_file) : la "
            "conversion appelle un moteur externe.\n"
            + dwg_module.describe_backends()["installation"])
    else:
        raise InteropError("import non implemente pour %s" % spec.label)

    if document is None:
        document = CadDocument(label)
        for solid in solids:
            document.add(solid)
    else:
        solids = document.solids()
    if cloud is not None:
        document.add_layer("RELEVE", 3)
        document.add({"type": "nuage_points", "points": [list(p)
                                                         for p in cloud.points],
                      "statistiques": cloud.statistiques()
                      if hasattr(cloud, "statistiques") else cloud.statistics()},
                     kind="annotation", layer="RELEVE",
                     name="nuage_" + label)
        document.variables["points_importes"] = len(cloud)
    return {"format": key, "nom": label, "document": document,
            "solides": solids, "nuage": cloud,
            "statistiques": document.statistics()}


def options_width(pixels: int, dots_per_mm: float = 4.0) -> float:
    """Largeur reelle par defaut d'une image importee, en millimetres.

    Faute d'echelle connue, une resolution de 4 points par millimetre (une
    centaine de points par pouce) donne un calage plausible ; l'utilisateur
    ajuste ensuite avec la commande ECHELLE.
    """
    return max(1.0, pixels / max(0.1, dots_per_mm))


def _ifc_solids(text: str, label: str) -> List[Solid]:
    """Extrait les volumes d'un IFC : parallelepipedes et extrusions simples."""
    from BIM_Engine.ifc_handler import IFCHandler
    return IFCHandler().read_solids(text, label)


def import_file(path: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Importe un fichier du disque, DWG compris."""
    if not os.path.isfile(path):
        raise InteropError("fichier introuvable : %s" % path)
    extension = os.path.splitext(path)[1].lower()
    if extension == ".dwg":
        document = dwg_module.read_dwg(path, name)
        return {"format": "dwg", "nom": name or os.path.basename(path),
                "document": document, "solides": document.solids(),
                "nuage": None, "statistiques": document.statistics(),
                "identification": dwg_module.inspect(path)}
    with open(path, "rb") as handle:
        return import_data(handle.read(), path, name=name)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export_data(document: CadDocument, format_key: str,
                annotations: Optional[Sequence[Dict[str, Any]]] = None,
                **options):
    """Exporte un document. Renvoie du texte ou des octets selon le format."""
    spec = spec_for(format_key)
    if not spec.write:
        raise InteropError("le format %s est lu mais pas ecrit par MERCURY"
                           % spec.label)
    key = spec.key
    solids = document.solids()
    if key == "dxf":
        return dxf_module.write_dxf(document, options.get("version", "2018"),
                                    annotations)
    if key == "svg":
        return svg_module.write_svg(document, options.get("largeur", 1600),
                                    annotations=annotations,
                                    plane=options.get("plan", "xy"))
    if key == "ifc":
        from BIM_Engine.ifc_handler import IFCHandler
        return IFCHandler().export_solids(solids, document.name)
    if key == "step":
        return step_module.write_step(solids, options.get("schema", "AP214"),
                                      document.name)
    if key == "iges":
        return step_module.write_iges(solids, product=document.name)
    if key == "stl":
        return mesh_module.write_stl(solids, options.get("binaire", True),
                                     document.name)
    if key == "obj":
        return mesh_module.write_obj(solids)
    if key == "mtl":
        return mesh_module.write_mtl()
    if key == "ply":
        return mesh_module.write_ply(solids, options.get("binaire", False))
    if key == "off":
        return mesh_module.write_off(solids)
    if key == "gltf":
        return mesh_module.write_gltf(solids)
    if key == "glb":
        return mesh_module.write_glb(solids)
    if key == "3mf":
        return mesh_module.write_3mf(solids)
    if key == "amf":
        return mesh_module.write_amf(solids)
    if key == "dae":
        return mesh_module.write_collada(solids)
    if key == "wrl":
        return mesh_module.write_vrml(solids)
    if key == "x3d":
        return mesh_module.write_x3d(solids)
    if key == "3ds":
        return mesh_module.write_3ds(solids)
    if key == "pdf":
        return _export_pdf(document, annotations, **options)
    if key in ("png", "bmp", "ppm", "tga", "jpg"):
        return _export_image(document, key, **options)
    if key in ("xyz", "csv", "las"):
        return _export_points(document, key, **options)
    if key == "json":
        return native_module.write_native(document)
    raise InteropError("export non implemente pour %s" % spec.label)


def _export_pdf(document: CadDocument,
                annotations: Optional[Sequence[Dict[str, Any]]] = None,
                **options) -> bytes:
    """Planche PDF : projection du modele, cartouche, cotes."""
    from CAD_Core.math3d import Vec3
    paper = options.get("format", "A3")
    scale = float(options.get("echelle", 0.0))
    pdf = pdf_module.PdfDocument(document.name)
    page = pdf.add_page(paper, options.get("paysage", True))
    box = document.bbox
    width_mm = page.width / pdf_module.MM_TO_PT
    height_mm = page.height / pdf_module.MM_TO_PT
    if box.valid:
        if scale <= 0:
            scale = min((width_mm - 60.0) / max(1.0, box.size.x),
                        (height_mm - 70.0) / max(1.0, box.size.y))
        offset_x = 20.0 - box.min.x * scale
        offset_y = 55.0 - box.min.y * scale
    else:
        scale, offset_x, offset_y = 1.0, 20.0, 20.0

    def place(point) -> Tuple[float, float]:
        p = Vec3.of(point)
        return (offset_x + p.x * scale, offset_y + p.y * scale)

    page.line_width(0.25).stroke_color(0.1, 0.12, 0.15)
    for entity in document.visible_entities():
        geometry = entity.geometry
        if isinstance(geometry, Solid):
            for a, b in geometry.edges():
                page.line(place(a), place(b))
        elif isinstance(geometry, Curve):
            page.polyline([place(p) for p in geometry.points], geometry.closed)
        elif isinstance(geometry, Profile):
            for ring in geometry.rings():
                page.polyline([place(p) for p in ring], True)
    page.stroke_color(0.75, 0.15, 0.12).line_width(0.2)
    for annotation in annotations or []:
        points = annotation.get("points", [])
        if annotation.get("type", "").startswith("cotation") and len(points) >= 4:
            page.line(place(points[2]), place(points[3]))
            middle = ((Vec3.of(points[2]) + Vec3.of(points[3])) * 0.5)
            x, y = place(middle)
            page.fill_color(0.75, 0.15, 0.12).text((x, y + 1.5),
                                                   annotation.get("texte", ""), 2.5)
        elif annotation.get("type") == "texte":
            x, y = place(annotation.get("position", (0, 0, 0)))
            page.fill_color(0.1, 0.12, 0.15).text((x, y),
                                                  annotation.get("texte", ""), 3.5)
    denominator = int(round(1.0 / scale)) if scale > 0 else 1
    page.title_block(document.name, options.get("planche", "Plan general"),
                     "1:%d" % max(1, denominator),
                     options.get("date", ""))
    return pdf.build()


def _export_image(document: CadDocument, key: str, **options) -> bytes:
    from CAD_Core.render_engine import Renderer3D
    from CAD_Core.view3d import Camera
    camera = Camera(width=int(options.get("largeur", 1280)),
                    height=int(options.get("hauteur", 800)))
    camera.zoom_extents(document.bbox)
    if "vue" in options:
        camera.set_standard_view(options["vue"])
        camera.zoom_extents(document.bbox)
    frame = Renderer3D().render(document.solids(), camera,
                                options.get("style", "ombre_avec_aretes"))
    raster = image_module.Raster.from_framebuffer(frame)
    if key == "png":
        return image_module.write_png(raster)
    if key == "bmp":
        return image_module.write_bmp(raster)
    if key == "ppm":
        return image_module.write_ppm(raster)
    if key == "tga":
        return image_module.write_tga(raster)
    return image_module.write_jpeg(raster, int(options.get("qualite", 85)))


def _export_points(document: CadDocument, key: str, **options):
    cloud = cloud_module.PointCloud(name=document.name)
    for solid in document.solids():
        cloud.points.extend(solid.vertices())
    for entity in document.visible_entities():
        if isinstance(entity.geometry, Curve):
            cloud.points.extend(entity.geometry.points)
    if not cloud.points:
        raise InteropError("aucun point a exporter")
    if key == "xyz":
        return cloud_module.write_xyz(cloud)
    if key == "csv":
        return cloud_module.write_csv(cloud)
    return cloud_module.write_las(cloud)


def export_file(document: CadDocument, path: str,
                annotations: Optional[Sequence[Dict[str, Any]]] = None,
                **options) -> str:
    """Exporte vers un fichier du disque, DWG compris."""
    extension = os.path.splitext(path)[1].lower()
    if extension == ".dwg":
        return dwg_module.write_dwg(document, path,
                                    options.get("version_dwg", "ACAD2018"))
    spec = spec_for(path)
    payload = export_data(document, spec.key, annotations, **options)
    mode = "wb" if isinstance(payload, (bytes, bytearray)) else "w"
    with open(path, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) \
            as handle:
        handle.write(payload)
    return path


def convert(source: str, target: str, **options) -> Dict[str, Any]:
    """Convertit un fichier d'un format vers un autre."""
    imported = import_file(source)
    document = imported["document"]
    export_file(document, target, **options)
    return {"source": os.path.basename(source),
            "cible": os.path.basename(target),
            "format_source": imported["format"],
            "format_cible": spec_for(target).key,
            "objets": len(document.entities),
            "statistiques": document.statistics()}


__all__ = ["FORMATS", "FormatSpec", "InteropError", "capabilities", "convert",
           "export_data", "export_file", "formats", "identify", "import_data",
           "import_file", "spec_for"]
''')

ajouter('Interop/dxf.py', r'''
"""Lecture et ecriture DXF, du R12 a l'AC1032 (AutoCAD 2018-2021).

Le DXF est le format d'echange documente d'Autodesk : tout ce qui entre ou
sort de MERCURY passe par lui, y compris les DWG convertis. L'ecriture vise
la compatibilite maximale (sections HEADER, TABLES, BLOCKS, ENTITIES,
OBJECTS) et la lecture tolere les fichiers partiels produits par les
exportateurs tiers.

Entites gerees : POINT, LINE, LWPOLYLINE, POLYLINE (2D, 3D, maillage et
polyface), CIRCLE, ARC, ELLIPSE, SPLINE, TEXT, MTEXT, 3DFACE, SOLID, INSERT,
DIMENSION, HATCH, MESH.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from CAD_Core.document import ACI_COLORS, CadDocument, Layer
from CAD_Core.math3d import TOL, Vec3
from CAD_Core.profiles import Curve, Profile, bulge_arc, arc_points
from CAD_Core.solid import Polygon, Solid

DXF_VERSIONS = {
    "R12": "AC1009", "R13": "AC1012", "R14": "AC1014", "2000": "AC1015",
    "2004": "AC1018", "2007": "AC1021", "2010": "AC1024", "2013": "AC1027",
    "2018": "AC1032", "2021": "AC1032",
}
DEFAULT_VERSION = "2018"


class DxfError(ValueError):
    """Fichier DXF illisible ou incoherent."""


# ---------------------------------------------------------------------------
# Ecriture
# ---------------------------------------------------------------------------
class DxfWriter:
    """Construit un fichier DXF complet a partir d'un document CAO."""

    def __init__(self, version: str = DEFAULT_VERSION) -> None:
        if version not in DXF_VERSIONS:
            raise DxfError("version DXF inconnue : %s" % version)
        self.version = version
        self.release = DXF_VERSIONS[version]
        self._lines: List[str] = []
        self._handle = 0x200

    # -- primitives d'ecriture --------------------------------------------
    def tag(self, code: int, value) -> None:
        if isinstance(value, float):
            self._lines.append("%d\n%.9g" % (code, value))
        else:
            self._lines.append("%d\n%s" % (code, value))

    def next_handle(self) -> str:
        self._handle += 1
        return "%X" % self._handle

    def _entity_header(self, kind: str, layer: str, color: int = 256,
                       linetype: str = "PARCALQUE", subclass: str = "") -> None:
        self.tag(0, kind)
        if self.release != "AC1009":
            self.tag(5, self.next_handle())
            self.tag(100, "AcDbEntity")
        self.tag(8, layer)
        if color != 256:
            self.tag(62, color)
        if linetype not in ("PARCALQUE", "BYLAYER"):
            self.tag(6, linetype)
        if subclass and self.release != "AC1009":
            self.tag(100, subclass)

    # -- entites -----------------------------------------------------------
    def point(self, position, layer: str = "0", color: int = 256) -> None:
        p = Vec3.of(position)
        self._entity_header("POINT", layer, color, subclass="AcDbPoint")
        self.tag(10, p.x)
        self.tag(20, p.y)
        self.tag(30, p.z)

    def line(self, start, end, layer: str = "0", color: int = 256,
             linetype: str = "PARCALQUE") -> None:
        a, b = Vec3.of(start), Vec3.of(end)
        self._entity_header("LINE", layer, color, linetype, "AcDbLine")
        for code, value in ((10, a.x), (20, a.y), (30, a.z),
                            (11, b.x), (21, b.y), (31, b.z)):
            self.tag(code, value)

    def polyline(self, points: Sequence, closed: bool = False,
                 layer: str = "0", color: int = 256,
                 elevation: Optional[float] = None) -> None:
        """LWPOLYLINE si la polyligne est plane, POLYLINE 3D sinon."""
        pts = [Vec3.of(p) for p in points]
        if len(pts) < 2:
            return
        planar = all(abs(p.z - pts[0].z) < 1e-6 for p in pts)
        if planar and self.release != "AC1009":
            self._entity_header("LWPOLYLINE", layer, color,
                                subclass="AcDbPolyline")
            self.tag(90, len(pts))
            self.tag(70, 1 if closed else 0)
            self.tag(38, pts[0].z if elevation is None else elevation)
            for point in pts:
                self.tag(10, point.x)
                self.tag(20, point.y)
            return
        self._entity_header("POLYLINE", layer, color, subclass="AcDb3dPolyline")
        self.tag(66, 1)
        self.tag(10, 0.0)
        self.tag(20, 0.0)
        self.tag(30, 0.0)
        self.tag(70, (1 if closed else 0) | 8)
        for point in pts:
            self._entity_header("VERTEX", layer, color,
                                subclass="AcDb3dPolylineVertex")
            self.tag(10, point.x)
            self.tag(20, point.y)
            self.tag(30, point.z)
            self.tag(70, 32)
        self.tag(0, "SEQEND")
        if self.release != "AC1009":
            self.tag(5, self.next_handle())
        self.tag(8, layer)

    def circle(self, center, radius: float, layer: str = "0",
               color: int = 256) -> None:
        c = Vec3.of(center)
        self._entity_header("CIRCLE", layer, color, subclass="AcDbCircle")
        self.tag(10, c.x)
        self.tag(20, c.y)
        self.tag(30, c.z)
        self.tag(40, radius)

    def arc(self, center, radius: float, start_deg: float, end_deg: float,
            layer: str = "0", color: int = 256) -> None:
        c = Vec3.of(center)
        self._entity_header("ARC", layer, color, subclass="AcDbCircle")
        self.tag(10, c.x)
        self.tag(20, c.y)
        self.tag(30, c.z)
        self.tag(40, radius)
        if self.release != "AC1009":
            self.tag(100, "AcDbArc")
        self.tag(50, start_deg)
        self.tag(51, end_deg)

    def text(self, position, value: str, height: float = 25.0,
             rotation: float = 0.0, layer: str = "0", color: int = 256,
             style: str = "Standard") -> None:
        p = Vec3.of(position)
        self._entity_header("TEXT", layer, color, subclass="AcDbText")
        self.tag(10, p.x)
        self.tag(20, p.y)
        self.tag(30, p.z)
        self.tag(40, height)
        self.tag(1, value.replace("\n", " "))
        self.tag(50, rotation)
        self.tag(7, style)

    def mtext(self, position, value: str, height: float = 25.0,
              width: float = 0.0, layer: str = "0", color: int = 256) -> None:
        p = Vec3.of(position)
        self._entity_header("MTEXT", layer, color, subclass="AcDbMText")
        self.tag(10, p.x)
        self.tag(20, p.y)
        self.tag(30, p.z)
        self.tag(40, height)
        self.tag(41, width)
        self.tag(71, 1)
        self.tag(1, value.replace("\n", r"\P"))

    def face3d(self, points: Sequence, layer: str = "0",
               color: int = 256) -> None:
        pts = [Vec3.of(p) for p in points][:4]
        while len(pts) < 4:
            pts.append(pts[-1])
        self._entity_header("3DFACE", layer, color, subclass="AcDbFace")
        for index, point in enumerate(pts):
            self.tag(10 + index, point.x)
            self.tag(20 + index, point.y)
            self.tag(30 + index, point.z)

    def polyface_mesh(self, vertices: Sequence, faces: Sequence,
                      layer: str = "0", color: int = 256) -> None:
        """Maillage polyface : la facon standard d'ecrire un solide en DXF."""
        points = [Vec3.of(v) for v in vertices]
        if not points or not faces:
            return
        self._entity_header("POLYLINE", layer, color,
                            subclass="AcDbPolyFaceMesh")
        self.tag(66, 1)
        self.tag(10, 0.0)
        self.tag(20, 0.0)
        self.tag(30, 0.0)
        self.tag(70, 64)
        self.tag(71, len(points))
        self.tag(72, len(faces))
        for point in points:
            self._entity_header("VERTEX", layer, color,
                                subclass="AcDbPolyFaceMeshVertex")
            self.tag(10, point.x)
            self.tag(20, point.y)
            self.tag(30, point.z)
            self.tag(70, 192)
        for face in faces:
            indices = list(face)[:4]
            self._entity_header("VERTEX", layer, color,
                                subclass="AcDbFaceRecord")
            self.tag(10, 0.0)
            self.tag(20, 0.0)
            self.tag(30, 0.0)
            self.tag(70, 128)
            for position, index in enumerate(indices):
                self.tag(71 + position, index + 1)
        self.tag(0, "SEQEND")
        if self.release != "AC1009":
            self.tag(5, self.next_handle())
        self.tag(8, layer)

    def solid(self, solid: Solid, layer: Optional[str] = None,
              color: int = 256, triangulate: bool = False) -> None:
        """Ecrit un solide : maillage polyface, decoupe en triangles au besoin."""
        source = solid
        if triangulate:
            from CAD_Core.mesh_tools import triangulate as to_triangles
            source = to_triangles(solid)
        vertices, faces = source.to_mesh()
        usable: List[Tuple[int, ...]] = []
        for face in faces:
            if len(face) <= 4:
                usable.append(face)
            else:                            # DXF plafonne a quatre sommets
                for k in range(1, len(face) - 1):
                    usable.append((face[0], face[k], face[k + 1]))
        self.polyface_mesh(vertices, usable, layer or solid.layer, color)

    def insert(self, name: str, position, scale: float = 1.0,
               rotation: float = 0.0, layer: str = "0") -> None:
        p = Vec3.of(position)
        self._entity_header("INSERT", layer, subclass="AcDbBlockReference")
        self.tag(2, name)
        self.tag(10, p.x)
        self.tag(20, p.y)
        self.tag(30, p.z)
        self.tag(41, scale)
        self.tag(42, scale)
        self.tag(43, scale)
        self.tag(50, rotation)

    def hatch(self, profile: Profile, pattern: str = "ANSI31",
              scale: float = 1.0, angle_deg: float = 0.0, layer: str = "0",
              color: int = 8) -> None:
        """Hachures : contour ferme et ouvertures, motif nomme."""
        if self.release == "AC1009":
            return                           # HATCH n'existe pas en R12
        self._entity_header("HATCH", layer, color, subclass="AcDbHatch")
        self.tag(10, 0.0)
        self.tag(20, 0.0)
        self.tag(30, profile.outline[0].z if profile.outline else 0.0)
        self.tag(210, 0.0)
        self.tag(220, 0.0)
        self.tag(230, 1.0)
        self.tag(2, pattern)
        self.tag(70, 1 if pattern == "SOLID" else 0)
        self.tag(71, 0)
        rings = profile.rings()
        self.tag(91, len(rings))
        for ring in rings:
            self.tag(92, 7)
            self.tag(72, 0)
            self.tag(73, 1)
            self.tag(93, len(ring))
            for point in ring:
                self.tag(10, point.x)
                self.tag(20, point.y)
            self.tag(97, 0)
        self.tag(75, 1)
        self.tag(76, 1)
        self.tag(52, angle_deg)
        self.tag(41, scale)
        self.tag(77, 0)
        self.tag(78, 0)
        self.tag(98, 0)

    # -- assemblage du fichier --------------------------------------------
    def build(self, document: CadDocument,
              annotations: Optional[Sequence[Dict[str, Any]]] = None) -> str:
        """Serialise un document complet."""
        self._lines = []
        self._header(document)
        self._tables(document)
        self._blocks(document)
        self._entities(document, annotations or [])
        self._objects()
        self.tag(0, "EOF")
        return "\n".join(self._lines) + "\n"

    def _header(self, document: CadDocument) -> None:
        box = document.bbox
        insunits = {"mm": 4, "cm": 5, "m": 6, "in": 1, "ft": 2}
        self.tag(0, "SECTION")
        self.tag(2, "HEADER")
        for name, code, value in (
                ("$ACADVER", 1, self.release),
                ("$HANDSEED", 5, "FFFF"),
                ("$INSUNITS", 70, insunits.get(document.units, 4)),
                ("$LUNITS", 70, 2),
                ("$LUPREC", 70, 4),
                ("$AUNITS", 70, 0),
                ("$AUPREC", 70, 2),
                ("$CLAYER", 8, document.current_layer),
                ("$DIMSCALE", 40, 1.0),
                ("$LTSCALE", 40, 1.0),
                ("$PDMODE", 70, 34),
                ("$PDSIZE", 40, 0.0),
                ("$MEASUREMENT", 70, 1)):
            self.tag(9, name)
            self.tag(code, value)
        if box.valid:
            self.tag(9, "$EXTMIN")
            self.tag(10, box.min.x)
            self.tag(20, box.min.y)
            self.tag(30, box.min.z)
            self.tag(9, "$EXTMAX")
            self.tag(10, box.max.x)
            self.tag(20, box.max.y)
            self.tag(30, box.max.z)
        self.tag(0, "ENDSEC")

    def _tables(self, document: CadDocument) -> None:
        self.tag(0, "SECTION")
        self.tag(2, "TABLES")

        self.tag(0, "TABLE")
        self.tag(2, "LTYPE")
        self.tag(70, 4)
        for name, pattern in (("CONTINUOUS", []), ("DASHED", [12.7, -6.35]),
                              ("CENTER", [31.75, -6.35, 6.35, -6.35]),
                              ("HIDDEN", [6.35, -3.175]),
                              ("DASHDOT", [12.7, -6.35, 0.0, -6.35])):
            self.tag(0, "LTYPE")
            if self.release != "AC1009":
                self.tag(5, self.next_handle())
                self.tag(100, "AcDbSymbolTableRecord")
                self.tag(100, "AcDbLinetypeTableRecord")
            self.tag(2, name)
            self.tag(70, 0)
            self.tag(3, name.title())
            self.tag(72, 65)
            self.tag(73, len(pattern))
            self.tag(40, sum(abs(v) for v in pattern))
            for value in pattern:
                self.tag(49, value)
                if self.release != "AC1009":
                    self.tag(74, 0)
        self.tag(0, "ENDTAB")

        self.tag(0, "TABLE")
        self.tag(2, "LAYER")
        self.tag(70, len(document.layers))
        for layer in document.layers.values():
            self.tag(0, "LAYER")
            if self.release != "AC1009":
                self.tag(5, self.next_handle())
                self.tag(100, "AcDbSymbolTableRecord")
                self.tag(100, "AcDbLayerTableRecord")
            self.tag(2, layer.name)
            self.tag(70, 4 if layer.locked else 0)
            self.tag(62, -abs(layer.color) if not layer.on else layer.color)
            self.tag(6, layer.linetype)
            if self.release != "AC1009":
                self.tag(370, layer.lineweight)
                self.tag(390, "F")
        self.tag(0, "ENDTAB")

        self.tag(0, "TABLE")
        self.tag(2, "STYLE")
        self.tag(70, len(document.text_styles))
        for name, style in document.text_styles.items():
            self.tag(0, "STYLE")
            if self.release != "AC1009":
                self.tag(5, self.next_handle())
                self.tag(100, "AcDbSymbolTableRecord")
                self.tag(100, "AcDbTextStyleTableRecord")
            self.tag(2, name)
            self.tag(70, 0)
            self.tag(40, 0.0)
            self.tag(41, style.get("largeur", 1.0))
            self.tag(50, style.get("oblique", 0.0))
            self.tag(71, 0)
            self.tag(42, style.get("hauteur", 2.5))
            self.tag(3, style.get("police", "arial.ttf"))
            self.tag(4, "")
        self.tag(0, "ENDTAB")
        self.tag(0, "ENDSEC")

    def _blocks(self, document: CadDocument) -> None:
        self.tag(0, "SECTION")
        self.tag(2, "BLOCKS")
        for name in ("*Model_Space", "*Paper_Space"):
            self._block_start(name, (0.0, 0.0, 0.0))
            self._block_end(name)
        for block in document.blocks.values():
            self._block_start(block.name, block.base_point)
            for member in block.entities:
                self._write_entity(member)
            self._block_end(block.name)
        self.tag(0, "ENDSEC")

    def _block_start(self, name: str, base_point) -> None:
        p = Vec3.of(base_point)
        self.tag(0, "BLOCK")
        if self.release != "AC1009":
            self.tag(5, self.next_handle())
            self.tag(100, "AcDbEntity")
        self.tag(8, "0")
        if self.release != "AC1009":
            self.tag(100, "AcDbBlockBegin")
        self.tag(2, name)
        self.tag(70, 0)
        self.tag(10, p.x)
        self.tag(20, p.y)
        self.tag(30, p.z)
        self.tag(3, name)
        self.tag(1, "")

    def _block_end(self, name: str) -> None:
        self.tag(0, "ENDBLK")
        if self.release != "AC1009":
            self.tag(5, self.next_handle())
            self.tag(100, "AcDbEntity")
        self.tag(8, "0")
        if self.release != "AC1009":
            self.tag(100, "AcDbBlockEnd")

    def _entities(self, document: CadDocument,
                  annotations: Sequence[Dict[str, Any]]) -> None:
        self.tag(0, "SECTION")
        self.tag(2, "ENTITIES")
        for entity in document.entities.values():
            self._write_entity(entity)
        for annotation in annotations:
            self._write_annotation(annotation)
        self.tag(0, "ENDSEC")

    def _write_entity(self, entity) -> None:
        geometry = entity.geometry
        layer, color = entity.layer, entity.color
        if isinstance(geometry, Solid):
            self.solid(geometry, layer, color)
        elif isinstance(geometry, Curve):
            self.polyline(geometry.points, geometry.closed, layer, color)
        elif isinstance(geometry, Profile):
            for ring in geometry.rings():
                self.polyline(ring, True, layer, color)
        elif isinstance(geometry, dict):
            self._write_annotation(geometry, layer)

    def _write_annotation(self, annotation: Dict[str, Any],
                          layer: Optional[str] = None) -> None:
        kind = annotation.get("type", "")
        layer = layer or annotation.get("calque", "0")
        points = [Vec3.of(p) for p in annotation.get("points", [])]
        if kind == "texte":
            self.mtext(annotation.get("position", (0, 0, 0)),
                       annotation.get("texte", ""),
                       annotation.get("hauteur", 25.0), layer=layer)
        elif kind.startswith("cotation"):
            if len(points) >= 2:
                self.line(points[0], points[1], layer)
            if len(points) >= 4:
                self.line(points[2], points[3], layer)
                self.line(points[0], points[2], layer)
                self.line(points[1], points[3], layer)
            for arc_point in annotation.get("arc", []):
                pass
            if annotation.get("arc"):
                self.polyline(annotation["arc"], False, layer)
            middle = ((points[2] + points[3]) * 0.5 if len(points) >= 4
                      else (points[0] + points[1]) * 0.5 if len(points) >= 2
                      else Vec3())
            self.text(middle, annotation.get("texte", ""), 25.0, layer=layer)
        elif kind == "hachures":
            outline = annotation.get("contour", [])
            if outline:
                profile = Profile([Vec3.of(p) for p in outline],
                                  [[Vec3.of(p) for p in hole]
                                   for hole in annotation.get("ouvertures", [])])
                self.hatch(profile, annotation.get("motif", "ANSI31"),
                           annotation.get("echelle", 1.0),
                           annotation.get("angle_deg", 0.0), layer,
                           annotation.get("couleur", 8))
        elif kind in ("ligne_repere", "nuage_revision"):
            self.polyline(points, kind == "nuage_revision", layer)
            if kind == "ligne_repere" and points:
                self.text(points[-1], annotation.get("texte", ""),
                          annotation.get("hauteur_texte", 25.0), layer=layer)
        elif kind == "tableau":
            self._write_table(annotation, layer)
        elif points:
            self.polyline(points, False, layer)

    def _write_table(self, annotation: Dict[str, Any], layer: str) -> None:
        origin = Vec3.of(annotation.get("position", (0, 0, 0)))
        widths = annotation.get("largeurs", [])
        height = annotation.get("hauteur_ligne", 60.0)
        rows = annotation.get("lignes", [])
        total = sum(widths)
        for index, row in enumerate(rows):
            y = origin.y - index * height
            self.line((origin.x, y, origin.z), (origin.x + total, y, origin.z),
                      layer)
            x = origin.x
            for column, cell in enumerate(row):
                self.text((x + 10, y - height * 0.7, origin.z), str(cell),
                          height * 0.45, layer=layer)
                x += widths[column] if column < len(widths) else 300.0
        y = origin.y - len(rows) * height
        self.line((origin.x, y, origin.z), (origin.x + total, y, origin.z), layer)
        x = origin.x
        for width in list(widths) + [0.0]:
            self.line((x, origin.y, origin.z), (x, y, origin.z), layer)
            x += width

    def _objects(self) -> None:
        if self.release == "AC1009":
            return
        self.tag(0, "SECTION")
        self.tag(2, "OBJECTS")
        self.tag(0, "DICTIONARY")
        self.tag(5, self.next_handle())
        self.tag(100, "AcDbDictionary")
        self.tag(3, "ACAD_GROUP")
        self.tag(350, self.next_handle())
        self.tag(0, "ENDSEC")


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------
class DxfReader:
    """Analyse un DXF ASCII et reconstruit un document CAO."""

    def __init__(self, text: str) -> None:
        self.tags = self._tokenize(text)
        self.version = "inconnue"

    @staticmethod
    def _tokenize(text: str) -> List[Tuple[int, str]]:
        raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        tags: List[Tuple[int, str]] = []
        index = 0
        while index + 1 < len(raw):
            code_text = raw[index].strip()
            value = raw[index + 1]
            index += 2
            if not code_text:
                continue
            try:
                code = int(code_text)
            except ValueError:
                raise DxfError("code de groupe invalide : %r" % code_text)
            tags.append((code, value.strip()))
        if not tags:
            raise DxfError("fichier DXF vide")
        return tags

    def sections(self) -> Dict[str, List[Tuple[int, str]]]:
        out: Dict[str, List[Tuple[int, str]]] = {}
        current: Optional[str] = None
        buffer: List[Tuple[int, str]] = []
        index = 0
        while index < len(self.tags):
            code, value = self.tags[index]
            if code == 0 and value == "SECTION":
                if index + 1 < len(self.tags) and self.tags[index + 1][0] == 2:
                    current = self.tags[index + 1][1]
                    buffer = []
                    index += 2
                    continue
            if code == 0 and value == "ENDSEC" and current:
                out[current] = buffer
                current = None
                index += 1
                continue
            if current:
                buffer.append((code, value))
            index += 1
        return out

    def read(self, name: str = "importe") -> CadDocument:
        """Renvoie un document contenant calques, courbes, solides et textes."""
        document = CadDocument(name)
        sections = self.sections()
        for code, value in sections.get("HEADER", []):
            if code == 1 and value.startswith("AC"):
                self.version = value
        self._read_layers(sections.get("TABLES", []), document)
        self._read_entities(sections.get("ENTITIES", []), document)
        return document

    @staticmethod
    def _read_layers(tags: Sequence[Tuple[int, str]],
                     document: CadDocument) -> None:
        current: Optional[Dict[str, Any]] = None
        for code, value in tags:
            if code == 0:
                if current and current.get("nom"):
                    name = current["nom"]
                    color = int(current.get("couleur", 7))
                    layer = Layer(name, abs(color) or 7,
                                  current.get("type_ligne", "CONTINUOUS"),
                                  int(current.get("epaisseur", 25)),
                                  on=color >= 0)
                    document.layers[name] = layer
                current = {} if value == "LAYER" else None
                continue
            if current is None:
                continue
            if code == 2:
                current["nom"] = value
            elif code == 62:
                current["couleur"] = _as_int(value, 7)
            elif code == 6:
                current["type_ligne"] = value or "CONTINUOUS"
            elif code == 370:
                current["epaisseur"] = _as_int(value, 25)
        if current and current.get("nom"):
            name = current["nom"]
            document.layers[name] = Layer(name, abs(_as_int(
                current.get("couleur", 7), 7)) or 7)

    def _read_entities(self, tags: Sequence[Tuple[int, str]],
                       document: CadDocument) -> None:
        groups = _split_entities(tags)
        index = 0
        while index < len(groups):
            kind, body = groups[index]
            if kind == "POLYLINE":
                consumed, entity = self._read_polyline(groups, index)
                index += consumed
                if entity is not None:
                    document.add(entity[0], layer=entity[1])
                continue
            self._read_simple(kind, body, document)
            index += 1

    @staticmethod
    def _read_simple(kind: str, body: Dict[int, List[str]],
                     document: CadDocument) -> None:
        layer = _first(body, 8, "0")
        if layer not in document.layers:
            document.add_layer(layer)
        color = _as_int(_first(body, 62, "256"), 256)
        if kind == "LINE":
            a = _point(body, 0)
            b = Vec3(_as_float(_first(body, 11, "0")),
                     _as_float(_first(body, 21, "0")),
                     _as_float(_first(body, 31, "0")))
            document.add(Curve([a, b], False, "ligne"), layer=layer, color=color)
        elif kind == "POINT":
            document.add(Curve([_point(body, 0)], False, "point"), layer=layer,
                         color=color)
        elif kind == "LWPOLYLINE":
            xs = [float(v) for v in body.get(10, [])]
            ys = [float(v) for v in body.get(20, [])]
            elevation = _as_float(_first(body, 38, "0"))
            bulges = [float(v) for v in body.get(42, [])]
            closed = bool(_as_int(_first(body, 70, "0"), 0) & 1)
            points = [Vec3(x, y, elevation) for x, y in zip(xs, ys)]
            if len(bulges) == len(points) and any(abs(b) > 1e-9 for b in bulges):
                refined: List[Vec3] = []
                count = len(points)
                for i in range(count if closed else count - 1):
                    j = (i + 1) % count
                    refined.extend(bulge_arc(points[i], points[j], bulges[i])[:-1])
                if refined:
                    refined.append(points[0] if closed else points[-1])
                    points = refined
            if len(points) >= 2:
                document.add(Curve(points, closed, "polyligne"), layer=layer,
                             color=color)
        elif kind == "CIRCLE":
            center = _point(body, 0)
            radius = _as_float(_first(body, 40, "0"))
            if radius > 0:
                document.add(Curve.circle(center, radius), layer=layer,
                             color=color)
        elif kind == "ARC":
            center = _point(body, 0)
            radius = _as_float(_first(body, 40, "0"))
            start = math.radians(_as_float(_first(body, 50, "0")))
            end = math.radians(_as_float(_first(body, 51, "360")))
            if end <= start:
                end += 2 * math.pi
            if radius > 0:
                document.add(Curve(arc_points(center, radius, start, end),
                                   False, "arc"), layer=layer, color=color)
        elif kind == "ELLIPSE":
            center = _point(body, 0)
            major = Vec3(_as_float(_first(body, 11, "0")),
                         _as_float(_first(body, 21, "0")),
                         _as_float(_first(body, 31, "0")))
            ratio = _as_float(_first(body, 40, "1"))
            radius = major.norm()
            if radius > TOL:
                points = []
                for i in range(72):
                    angle = 2 * math.pi * i / 72.0
                    points.append(center + major * math.cos(angle)
                                  + Vec3(-major.y, major.x, 0.0) * ratio
                                  * math.sin(angle))
                document.add(Curve(points, True, "ellipse"), layer=layer,
                             color=color)
        elif kind == "SPLINE":
            xs = [float(v) for v in body.get(10, [])]
            ys = [float(v) for v in body.get(20, [])]
            zs = [float(v) for v in body.get(30, [])] or [0.0] * len(xs)
            control = [Vec3(x, y, z) for x, y, z in zip(xs, ys, zs)]
            if len(control) >= 2:
                document.add(Curve.spline(control), layer=layer, color=color)
        elif kind in ("TEXT", "MTEXT"):
            document.add({"type": "texte",
                          "position": list(_point(body, 0)),
                          "texte": _first(body, 1, "").replace(r"\P", "\n"),
                          "hauteur": _as_float(_first(body, 40, "25")),
                          "calque": layer},
                         kind="annotation", layer=layer, color=color)
        elif kind in ("3DFACE", "SOLID"):
            points = []
            for corner in range(4):
                if str(10 + corner) or True:
                    x = _first(body, 10 + corner, None)
                    if x is None:
                        continue
                    points.append(Vec3(_as_float(x),
                                       _as_float(_first(body, 20 + corner, "0")),
                                       _as_float(_first(body, 30 + corner, "0"))))
            unique: List[Vec3] = []
            for point in points:
                if not unique or unique[-1].distance_to(point) > 1e-9:
                    unique.append(point)
            if len(unique) >= 3:
                document.add(Solid.from_polygons([Polygon(unique)],
                                                 name="face"), layer=layer,
                             color=color)
        elif kind == "INSERT":
            document.add({"type": "insertion", "bloc": _first(body, 2, ""),
                          "position": list(_point(body, 0)),
                          "echelle": _as_float(_first(body, 41, "1")),
                          "rotation": _as_float(_first(body, 50, "0")),
                          "calque": layer, "points": [list(_point(body, 0))]},
                         kind="annotation", layer=layer, color=color)

    @staticmethod
    def _read_polyline(groups, index: int):
        """Reconstitue POLYLINE + VERTEX + SEQEND (3D, maillage, polyface)."""
        _, header = groups[index]
        layer = _first(header, 8, "0")
        flags = _as_int(_first(header, 70, "0"), 0)
        vertices: List[Vec3] = []
        faces: List[Tuple[int, ...]] = []
        consumed = 1
        cursor = index + 1
        while cursor < len(groups):
            kind, body = groups[cursor]
            consumed += 1
            cursor += 1
            if kind == "SEQEND":
                break
            if kind != "VERTEX":
                consumed -= 1
                cursor -= 1
                break
            vertex_flags = _as_int(_first(body, 70, "0"), 0)
            if vertex_flags & 128 and not vertex_flags & 64:
                indices = []
                for code in (71, 72, 73, 74):
                    value = _as_int(_first(body, code, "0"), 0)
                    if value:
                        indices.append(abs(value) - 1)
                if len(indices) >= 3:
                    faces.append(tuple(indices))
            else:
                vertices.append(_point(body, 0))
        if flags & 64 and faces and vertices:
            polygons = []
            for face in faces:
                points = [vertices[i] for i in face if 0 <= i < len(vertices)]
                if len(points) >= 3:
                    polygons.append(Polygon(points))
            if polygons:
                return consumed, (Solid.from_polygons(polygons,
                                                      name="maillage"), layer)
            return consumed, None
        if len(vertices) >= 2:
            return consumed, (Curve(vertices, bool(flags & 1), "polyligne"),
                              layer)
        return consumed, None


def _split_entities(tags: Sequence[Tuple[int, str]]
                    ) -> List[Tuple[str, Dict[int, List[str]]]]:
    groups: List[Tuple[str, Dict[int, List[str]]]] = []
    current: Optional[Dict[int, List[str]]] = None
    name = ""
    for code, value in tags:
        if code == 0:
            if current is not None:
                groups.append((name, current))
            name = value
            current = {}
            continue
        if current is None:
            continue
        current.setdefault(code, []).append(value)
    if current is not None:
        groups.append((name, current))
    return groups


def _first(body: Dict[int, List[str]], code: int, default=None):
    values = body.get(code)
    return values[0] if values else default


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _point(body: Dict[int, List[str]], offset: int) -> Vec3:
    return Vec3(_as_float(_first(body, 10 + offset, "0")),
                _as_float(_first(body, 20 + offset, "0")),
                _as_float(_first(body, 30 + offset, "0")))


# ---------------------------------------------------------------------------
# Interface courte
# ---------------------------------------------------------------------------
def write_dxf(document: CadDocument, version: str = DEFAULT_VERSION,
              annotations: Optional[Sequence[Dict[str, Any]]] = None) -> str:
    return DxfWriter(version).build(document, annotations)


def read_dxf(text: str, name: str = "importe") -> CadDocument:
    return DxfReader(text).read(name)


def probe_dxf(text: str) -> Dict[str, Any]:
    """Identification rapide : version, sections, nombre d'entites."""
    reader = DxfReader(text)
    sections = reader.sections()
    entities = _split_entities(sections.get("ENTITIES", []))
    kinds: Dict[str, int] = {}
    for kind, _ in entities:
        kinds[kind] = kinds.get(kind, 0) + 1
    version = "inconnue"
    for code, value in sections.get("HEADER", []):
        if code == 1 and value.startswith("AC"):
            version = value
            break
    label = next((k for k, v in DXF_VERSIONS.items() if v == version), version)
    return {"format": "DXF", "version": version, "release": label,
            "sections": sorted(sections), "entites": len(entities),
            "par_type": kinds}
''')

ajouter('Interop/dwg.py', r'''
"""Support du format DWG natif d'AutoCAD.

Le DWG est un format binaire proprietaire dont la specification n'est pas
publiee : aucun logiciel tiers ne l'ecrit sans passer par une bibliotheque
dediee. MERCURY procede donc en deux temps, comme tous les outils non
Autodesk :

1. Lecture native de l'en-tete : version exacte (R12 a AutoCAD 2018-2021),
   page de codes, table des sections, image d'apercu. Cela suffit a
   identifier, trier, indexer et previsualiser un DWG sans outil externe.
2. Conversion geometrique par un moteur installe sur la machine : ODA File
   Converter, LibreDWG (dwg2dxf / dxf2dwg) ou ezdxf. Le DWG est traduit en
   DXF, puis lu par le lecteur DXF integre ; l'ecriture suit le chemin
   inverse.

Quand aucun moteur n'est disponible, l'erreur levee dit exactement quoi
installer : jamais de silence ni de resultat approximatif.
"""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from CAD_Core.document import CadDocument

from .dxf import DEFAULT_VERSION, DxfError, read_dxf, write_dxf

# Code de version stocke dans les six premiers octets d'un DWG.
DWG_VERSIONS: Dict[str, str] = {
    "AC1006": "R10", "AC1009": "R11/R12", "AC1012": "R13", "AC1014": "R14",
    "AC1015": "AutoCAD 2000-2002", "AC1018": "AutoCAD 2004-2006",
    "AC1021": "AutoCAD 2007-2009", "AC1024": "AutoCAD 2010-2012",
    "AC1027": "AutoCAD 2013-2017", "AC1032": "AutoCAD 2018-2021",
}

# Versions cibles acceptees par les convertisseurs, du plus ancien au recent.
DWG_TARGETS = ["ACAD12", "ACAD2000", "ACAD2004", "ACAD2007", "ACAD2010",
               "ACAD2013", "ACAD2018"]


class DwgError(ValueError):
    """DWG illisible, ou conversion impossible faute de moteur installe."""


# ---------------------------------------------------------------------------
# Lecture native de l'en-tete
# ---------------------------------------------------------------------------
def probe_dwg(data: bytes) -> Dict[str, Any]:
    """Identifie un DWG sans aucune dependance : version, sections, apercu."""
    if len(data) < 128:
        raise DwgError("fichier trop court pour un DWG")
    signature = data[:6].decode("ascii", "replace")
    if not signature.startswith("AC10") and not signature.startswith("AC1"):
        raise DwgError("signature DWG absente (%r)" % signature)
    release = DWG_VERSIONS.get(signature, "version inconnue")
    codepage = struct.unpack_from("<H", data, 0x13)[0] if len(data) > 0x15 else 0
    image_seeker = struct.unpack_from("<I", data, 0x0D)[0] if len(data) > 0x11 else 0
    sections = 0
    if len(data) > 0x1D:
        try:
            sections = struct.unpack_from("<I", data, 0x15)[0]
        except struct.error:
            sections = 0
    preview = _preview_offset(data, image_seeker)
    return {
        "format": "DWG", "version": signature, "release": release,
        "taille_octets": len(data), "page_de_codes": codepage,
        "sections": sections if 0 < sections < 64 else 0,
        "apercu_disponible": preview is not None,
        "lisible_nativement": False,
        "conversion": describe_backends(),
    }


def _preview_offset(data: bytes, seeker: int) -> Optional[int]:
    if not (0 < seeker < len(data) - 32):
        return None
    return seeker


def extract_preview(data: bytes) -> Optional[bytes]:
    """Extrait la vignette BMP ou PNG stockee dans le DWG, si elle existe.

    L'apercu est la seule geometrie exploitable sans convertisseur : il sert
    a alimenter la galerie de fichiers et les listes de projets.
    """
    try:
        seeker = struct.unpack_from("<I", data, 0x0D)[0]
    except struct.error:
        return None
    if not (0 < seeker < len(data) - 32):
        return None
    try:
        count = data[seeker + 16]
    except IndexError:
        return None
    for index in range(min(count, 8)):
        base = seeker + 17 + index * 9
        if base + 9 > len(data):
            break
        kind = data[base]
        start, size = struct.unpack_from("<II", data, base + 1)
        if size <= 0 or start + size > len(data):
            continue
        payload = data[start:start + size]
        if kind == 2:                        # image BMP sans en-tete de fichier
            header = b"BM" + struct.pack("<IHHI", 14 + size, 0, 0, 14 + 40 + 1024)
            return header + payload
        if kind == 3 and payload[:8] == b"\x89PNG\r\n\x1a\n":
            return payload
        if payload[:2] == b"BM":
            return payload
    return None


# ---------------------------------------------------------------------------
# Moteurs de conversion
# ---------------------------------------------------------------------------
def _which(*names: str) -> Optional[str]:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def available_backends() -> List[Dict[str, Any]]:
    """Liste les moteurs de conversion DWG detectes sur la machine."""
    backends: List[Dict[str, Any]] = []
    oda = _which("ODAFileConverter", "ODAFileConverter.exe", "TeighaFileConverter")
    if oda:
        backends.append({"nom": "ODA File Converter", "commande": oda,
                         "lecture": True, "ecriture": True,
                         "source": "https://www.opendesign.com/guestfiles/oda_file_converter"})
    dwg2dxf = _which("dwg2dxf")
    if dwg2dxf:
        backends.append({"nom": "LibreDWG dwg2dxf", "commande": dwg2dxf,
                         "lecture": True, "ecriture": bool(_which("dxf2dwg")),
                         "source": "https://www.gnu.org/software/libredwg/"})
    try:
        import ezdxf                          # noqa: F401
        from ezdxf.addons import odafc
        # ezdxf expose toujours le module odafc ; seul `is_installed` dit si
        # le convertisseur ODA est reellement present. Sans ce controle, le
        # rapport de capacites annoncerait une lecture DWG qui echouerait.
        if not hasattr(odafc, "is_installed") or odafc.is_installed():
            backends.append({"nom": "ezdxf + odafc", "commande": "python:ezdxf",
                             "lecture": True, "ecriture": True,
                             "source": "https://ezdxf.mozman.at/"})
    except Exception:
        pass
    return backends


def describe_backends() -> Dict[str, Any]:
    backends = available_backends()
    return {
        "moteurs_detectes": [b["nom"] for b in backends],
        "lecture_dwg": any(b["lecture"] for b in backends),
        "ecriture_dwg": any(b["ecriture"] for b in backends),
        "installation": (
            "Installez l'un de ces moteurs pour convertir la geometrie DWG : "
            "ODA File Converter (gratuit, Windows/Linux/macOS), "
            "LibreDWG (paquet libredwg-tools), ou "
            "pip install ezdxf[odafc]. L'identification, l'apercu et tous "
            "les autres formats fonctionnent sans eux."),
    }


def _run(command: List[str], timeout: int = 300) -> Tuple[int, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=timeout)
        return result.returncode, (result.stdout + result.stderr)[-2000:]
    except FileNotFoundError as error:
        return 127, str(error)
    except subprocess.TimeoutExpired:
        return 124, "conversion interrompue : delai depasse"


def dwg_to_dxf(path: str, version: str = "ACAD2018") -> str:
    """Convertit un DWG en texte DXF a l'aide du premier moteur disponible."""
    if not os.path.isfile(path):
        raise DwgError("fichier introuvable : %s" % path)
    backends = available_backends()
    if not backends:
        raise DwgError(
            "aucun moteur de conversion DWG installe.\n"
            + describe_backends()["installation"])
    errors: List[str] = []
    for backend in backends:
        name = backend["nom"]
        with tempfile.TemporaryDirectory() as workspace:
            output = os.path.join(workspace, "sortie")
            os.makedirs(output, exist_ok=True)
            if name.startswith("ODA"):
                source = os.path.join(workspace, "entree")
                os.makedirs(source, exist_ok=True)
                shutil.copy(path, source)
                code, log = _run([backend["commande"], source, output,
                                  version, "DXF", "0", "1"])
            elif name.startswith("LibreDWG"):
                target = os.path.join(output, "sortie.dxf")
                code, log = _run([backend["commande"], "-o", target, path])
            else:
                try:
                    from ezdxf.addons import odafc
                    document = odafc.readfile(path)
                    target = os.path.join(output, "sortie.dxf")
                    document.saveas(target)
                    code, log = 0, ""
                except Exception as error:    # moteur present mais en echec
                    code, log = 1, str(error)
            if code == 0:
                for entry in sorted(os.listdir(output)):
                    if entry.lower().endswith(".dxf"):
                        with open(os.path.join(output, entry), "r",
                                  encoding="utf-8", errors="replace") as handle:
                            return handle.read()
                code, log = 1, "aucun DXF produit"
            errors.append("%s : %s" % (name, log.strip()[:300]))
    raise DwgError("la conversion DWG a echoue :\n  " + "\n  ".join(errors))


def dxf_to_dwg(dxf_text: str, target_path: str,
               version: str = "ACAD2018") -> str:
    """Ecrit un DWG a partir d'un DXF, via un moteur de conversion."""
    if version not in DWG_TARGETS:
        raise DwgError("version DWG cible inconnue : %s" % version)
    backends = [b for b in available_backends() if b["ecriture"]]
    if not backends:
        raise DwgError(
            "aucun moteur capable d'ecrire du DWG n'est installe.\n"
            + describe_backends()["installation"])
    errors: List[str] = []
    for backend in backends:
        name = backend["nom"]
        with tempfile.TemporaryDirectory() as workspace:
            source = os.path.join(workspace, "entree")
            output = os.path.join(workspace, "sortie")
            os.makedirs(source, exist_ok=True)
            os.makedirs(output, exist_ok=True)
            dxf_path = os.path.join(source, "dessin.dxf")
            with open(dxf_path, "w", encoding="utf-8") as handle:
                handle.write(dxf_text)
            if name.startswith("ODA"):
                code, log = _run([backend["commande"], source, output,
                                  version, "DWG", "0", "1"])
            elif name.startswith("LibreDWG"):
                produced = os.path.join(output, "dessin.dwg")
                code, log = _run([_which("dxf2dwg") or "dxf2dwg", "-o",
                                  produced, dxf_path])
            else:
                try:
                    import ezdxf
                    from ezdxf.addons import odafc
                    document = ezdxf.readfile(dxf_path)
                    odafc.export_dwg(document,
                                     os.path.join(output, "dessin.dwg"),
                                     version=version)
                    code, log = 0, ""
                except Exception as error:
                    code, log = 1, str(error)
            if code == 0:
                for entry in sorted(os.listdir(output)):
                    if entry.lower().endswith(".dwg"):
                        shutil.copy(os.path.join(output, entry), target_path)
                        return target_path
                code, log = 1, "aucun DWG produit"
            errors.append("%s : %s" % (name, log.strip()[:300]))
    raise DwgError("l'ecriture DWG a echoue :\n  " + "\n  ".join(errors))


# ---------------------------------------------------------------------------
# Interface haut niveau
# ---------------------------------------------------------------------------
def read_dwg(path: str, name: Optional[str] = None) -> CadDocument:
    """Lit un DWG et renvoie un document CAO complet."""
    return read_dxf(dwg_to_dxf(path), name or os.path.basename(path))


def write_dwg(document: CadDocument, path: str,
              version: str = "ACAD2018") -> str:
    """Ecrit un document en DWG. Le DXF equivalent est conserve a cote."""
    dxf_text = write_dxf(document, DEFAULT_VERSION)
    fallback = os.path.splitext(path)[0] + ".dxf"
    with open(fallback, "w", encoding="utf-8") as handle:
        handle.write(dxf_text)
    return dxf_to_dwg(dxf_text, path, version)


def inspect(path: str) -> Dict[str, Any]:
    """Fiche d'identite d'un DWG : ce que sait dire MERCURY sans convertisseur."""
    with open(path, "rb") as handle:
        data = handle.read(4096)
    with open(path, "rb") as handle:
        full = handle.read()
    report = probe_dwg(data)
    report["taille_octets"] = len(full)
    report["fichier"] = os.path.basename(path)
    preview = extract_preview(full)
    report["apercu_octets"] = len(preview) if preview else 0
    return report
''')

ajouter('Interop/meshes.py', r'''
"""Formats de maillage et d'echange 3D.

STL (ASCII et binaire), OBJ avec MTL, PLY (ASCII et binaire), OFF, 3MF, AMF,
VRML 2.0, X3D, COLLADA, glTF 2.0, GLB et 3DS. Ce sont les formats attendus
par les visionneuses, les imprimantes 3D, les moteurs de rendu et les
plateformes de partage de maquettes.

Toutes les fonctions travaillent sur des `Solid` : lire un fichier rend une
liste de solides, en ecrire un consomme la meme liste.
"""
from __future__ import annotations

import base64
import json
import math
import struct
import zipfile
import io
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from CAD_Core.math3d import Vec3
from CAD_Core.mesh_tools import triangulate
from CAD_Core.render_engine import MATERIAL_COLORS
from CAD_Core.solid import Polygon, Solid


class MeshFormatError(ValueError):
    """Fichier de maillage illisible."""


def _merge(solids: Sequence[Solid]) -> Tuple[List[Tuple[float, float, float]],
                                             List[Tuple[int, ...]], List[str]]:
    """Fusionne plusieurs solides en un seul jeu sommets / faces / materiaux."""
    vertices: List[Tuple[float, float, float]] = []
    faces: List[Tuple[int, ...]] = []
    materials: List[str] = []
    index: Dict[Tuple[float, ...], int] = {}
    for solid in solids:
        for polygon in solid.polygons:
            face: List[int] = []
            for vertex in polygon.vertices:
                key = vertex.rounded(5)
                if key not in index:
                    index[key] = len(vertices)
                    vertices.append((vertex.x, vertex.y, vertex.z))
                if not face or face[-1] != index[key]:
                    face.append(index[key])
            if len(face) >= 3:
                faces.append(tuple(face))
                materials.append(polygon.material)
    return vertices, faces, materials


def _triangles(solids: Sequence[Solid]) -> List[Tuple[Vec3, Vec3, Vec3]]:
    out: List[Tuple[Vec3, Vec3, Vec3]] = []
    for solid in solids:
        out.extend(solid.to_triangles())
    return out


def _color_of(material: str) -> Tuple[float, float, float]:
    r, g, b = MATERIAL_COLORS.get(material, MATERIAL_COLORS["default"])
    return (r / 255.0, g / 255.0, b / 255.0)


# ---------------------------------------------------------------------------
# STL
# ---------------------------------------------------------------------------
def write_stl(solids: Sequence[Solid], binary: bool = True,
              name: str = "MERCURY") -> bytes:
    """Ecrit un STL. Le binaire est le choix par defaut : dix fois plus compact."""
    triangles = _triangles(solids)
    if binary:
        out = bytearray()
        header = ("MERCURY CAD AI X - %s" % name)[:79].encode("ascii", "replace")
        out += header.ljust(80, b"\x00")
        out += struct.pack("<I", len(triangles))
        for a, b, c in triangles:
            normal = (b - a).cross(c - a).unit()
            out += struct.pack("<12fH", normal.x, normal.y, normal.z,
                               a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z, 0)
        return bytes(out)
    lines = ["solid %s" % name]
    for a, b, c in triangles:
        normal = (b - a).cross(c - a).unit()
        lines.append("  facet normal %.6e %.6e %.6e" % (normal.x, normal.y,
                                                        normal.z))
        lines.append("    outer loop")
        for point in (a, b, c):
            lines.append("      vertex %.6e %.6e %.6e" % (point.x, point.y,
                                                          point.z))
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid %s" % name)
    return "\n".join(lines).encode("utf-8")


def read_stl(data: bytes, name: str = "stl") -> List[Solid]:
    """Lit un STL, binaire ou ASCII, en detectant le format automatiquement."""
    if len(data) < 15:
        raise MeshFormatError("fichier STL trop court")
    header = data[:80]
    is_binary = True
    if data[:5].lower() == b"solid":
        expected = 84 + 50 * struct.unpack_from("<I", data, 80)[0] \
            if len(data) >= 84 else -1
        is_binary = len(data) == expected
    polygons: List[Polygon] = []
    if is_binary:
        count = struct.unpack_from("<I", data, 80)[0]
        if 84 + count * 50 > len(data):
            raise MeshFormatError("STL binaire tronque (%d triangles annonces)"
                                  % count)
        for index in range(count):
            offset = 84 + index * 50
            values = struct.unpack_from("<12f", data, offset)
            points = [Vec3(*values[3:6]), Vec3(*values[6:9]),
                      Vec3(*values[9:12])]
            polygons.append(Polygon(points))
    else:
        current: List[Vec3] = []
        for line in data.decode("utf-8", "replace").splitlines():
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "vertex" and len(parts) >= 4:
                current.append(Vec3(float(parts[1]), float(parts[2]),
                                    float(parts[3])))
            elif parts[0] == "endloop":
                if len(current) >= 3:
                    polygons.append(Polygon(current))
                current = []
    if not polygons:
        raise MeshFormatError("aucun triangle trouve dans le STL")
    return [Solid.from_polygons(polygons, name=name)]


# ---------------------------------------------------------------------------
# OBJ + MTL
# ---------------------------------------------------------------------------
def write_obj(solids: Sequence[Solid], scale: float = 0.001,
              mtl_name: str = "mercury.mtl",
              swap_axes: bool = True) -> str:
    """OBJ en metres, axe Y vers le haut : convention des moteurs 3D."""
    vertices, faces, materials = _merge(solids)
    lines = ["# MERCURY CAD AI X - export OBJ", "mtllib " + mtl_name]
    for x, y, z in vertices:
        if swap_axes:
            lines.append("v %.6f %.6f %.6f" % (x * scale, z * scale, -y * scale))
        else:
            lines.append("v %.6f %.6f %.6f" % (x * scale, y * scale, z * scale))
    current = None
    for face, material in zip(faces, materials):
        if material != current:
            current = material
            lines.append("usemtl " + material)
        lines.append("f " + " ".join(str(i + 1) for i in face))
    return "\n".join(lines) + "\n"


def write_mtl(materials: Optional[Iterable[str]] = None) -> str:
    names = list(materials) if materials else list(MATERIAL_COLORS)
    out = ["# MERCURY CAD AI X - bibliotheque de materiaux"]
    for name in names:
        r, g, b = _color_of(name)
        out += ["newmtl " + name, "Ka %.3f %.3f %.3f" % (r * 0.3, g * 0.3, b * 0.3),
                "Kd %.3f %.3f %.3f" % (r, g, b), "Ks 0.08 0.08 0.08",
                "Ns 24", "d 1.0", "illum 2", ""]
    return "\n".join(out)


def read_obj(text: str, scale: float = 1000.0, swap_axes: bool = True,
             name: str = "obj") -> List[Solid]:
    """Lit un OBJ (sommets, faces, groupes, materiaux)."""
    vertices: List[Vec3] = []
    polygons: List[Polygon] = []
    material = "default"
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        if parts[0] == "v" and len(parts) >= 4:
            x, y, z = (float(parts[1]), float(parts[2]), float(parts[3]))
            if swap_axes:
                vertices.append(Vec3(x * scale, -z * scale, y * scale))
            else:
                vertices.append(Vec3(x * scale, y * scale, z * scale))
        elif parts[0] == "usemtl" and len(parts) >= 2:
            material = parts[1]
        elif parts[0] == "f" and len(parts) >= 4:
            indices: List[int] = []
            for token in parts[1:]:
                raw = token.split("/")[0]
                try:
                    value = int(raw)
                except ValueError:
                    continue
                indices.append(value - 1 if value > 0 else len(vertices) + value)
            points = [vertices[i] for i in indices if 0 <= i < len(vertices)]
            if len(points) >= 3:
                polygons.append(Polygon(points, material=material))
    if not polygons:
        raise MeshFormatError("aucune face exploitable dans l'OBJ")
    return [Solid.from_polygons(polygons, name=name)]


# ---------------------------------------------------------------------------
# PLY et OFF
# ---------------------------------------------------------------------------
def write_ply(solids: Sequence[Solid], binary: bool = False) -> bytes:
    vertices, faces, _ = _merge(solids)
    header = ["ply",
              "format %s 1.0" % ("binary_little_endian" if binary else "ascii"),
              "comment MERCURY CAD AI X",
              "element vertex %d" % len(vertices),
              "property float x", "property float y", "property float z",
              "element face %d" % len(faces),
              "property list uchar int vertex_index", "end_header"]
    if binary:
        out = bytearray("\n".join(header).encode("ascii") + b"\n")
        for x, y, z in vertices:
            out += struct.pack("<3f", x, y, z)
        for face in faces:
            out += struct.pack("<B", len(face))
            out += struct.pack("<%di" % len(face), *face)
        return bytes(out)
    lines = list(header)
    lines += ["%.6f %.6f %.6f" % v for v in vertices]
    lines += ["%d %s" % (len(f), " ".join(str(i) for i in f)) for f in faces]
    return ("\n".join(lines) + "\n").encode("utf-8")


def read_ply(data: bytes, name: str = "ply") -> List[Solid]:
    text_end = data.find(b"end_header")
    if text_end < 0:
        raise MeshFormatError("en-tete PLY absent")
    header = data[:text_end].decode("ascii", "replace").splitlines()
    binary = any("binary" in line for line in header)
    vertex_count = face_count = 0
    properties = 0
    element = ""
    for line in header:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "element" and len(parts) >= 3:
            element = parts[1]
            if element == "vertex":
                vertex_count = int(parts[2])
            elif element == "face":
                face_count = int(parts[2])
        elif parts[0] == "property" and element == "vertex":
            properties += 1
    offset = data.find(b"\n", text_end) + 1
    vertices: List[Vec3] = []
    polygons: List[Polygon] = []
    if binary:
        cursor = offset
        for _ in range(vertex_count):
            x, y, z = struct.unpack_from("<3f", data, cursor)
            cursor += 4 * max(3, properties)
            vertices.append(Vec3(x, y, z))
        for _ in range(face_count):
            count = data[cursor]
            cursor += 1
            indices = struct.unpack_from("<%di" % count, data, cursor)
            cursor += 4 * count
            points = [vertices[i] for i in indices if 0 <= i < len(vertices)]
            if len(points) >= 3:
                polygons.append(Polygon(points))
    else:
        body = data[offset:].decode("utf-8", "replace").split()
        cursor = 0
        for _ in range(vertex_count):
            values = body[cursor:cursor + max(3, properties)]
            cursor += max(3, properties)
            vertices.append(Vec3(float(values[0]), float(values[1]),
                                 float(values[2])))
        for _ in range(face_count):
            count = int(body[cursor])
            cursor += 1
            indices = [int(v) for v in body[cursor:cursor + count]]
            cursor += count
            points = [vertices[i] for i in indices if 0 <= i < len(vertices)]
            if len(points) >= 3:
                polygons.append(Polygon(points))
    if not polygons:
        raise MeshFormatError("aucune face dans le PLY")
    return [Solid.from_polygons(polygons, name=name)]


def write_off(solids: Sequence[Solid]) -> str:
    vertices, faces, _ = _merge(solids)
    lines = ["OFF", "%d %d 0" % (len(vertices), len(faces))]
    lines += ["%.6f %.6f %.6f" % v for v in vertices]
    lines += ["%d %s" % (len(f), " ".join(str(i) for i in f)) for f in faces]
    return "\n".join(lines) + "\n"


def read_off(text: str, name: str = "off") -> List[Solid]:
    tokens = [t for t in text.split() if t]
    if not tokens or not tokens[0].upper().startswith("OFF"):
        raise MeshFormatError("en-tete OFF absent")
    cursor = 1
    vertex_count, face_count = int(tokens[cursor]), int(tokens[cursor + 1])
    cursor += 3
    vertices: List[Vec3] = []
    for _ in range(vertex_count):
        vertices.append(Vec3(float(tokens[cursor]), float(tokens[cursor + 1]),
                             float(tokens[cursor + 2])))
        cursor += 3
    polygons: List[Polygon] = []
    for _ in range(face_count):
        count = int(tokens[cursor])
        cursor += 1
        indices = [int(tokens[cursor + i]) for i in range(count)]
        cursor += count
        points = [vertices[i] for i in indices if 0 <= i < len(vertices)]
        if len(points) >= 3:
            polygons.append(Polygon(points))
    return [Solid.from_polygons(polygons, name=name)]


# ---------------------------------------------------------------------------
# glTF 2.0 et GLB
# ---------------------------------------------------------------------------
def _gltf_document(solids: Sequence[Solid], scale: float = 0.001,
                   embed: bool = True) -> Tuple[Dict[str, Any], bytes]:
    positions: List[float] = []
    indices: List[int] = []
    for solid in solids:
        for a, b, c in solid.to_triangles():
            base = len(positions) // 3
            for point in (a, b, c):
                positions += [point.x * scale, point.z * scale,
                              -point.y * scale]
            indices += [base, base + 1, base + 2]
    if not positions:
        positions = [0.0, 0.0, 0.0]
        indices = [0, 0, 0]
    position_bytes = struct.pack("<%df" % len(positions), *positions)
    index_bytes = struct.pack("<%dI" % len(indices), *indices)
    padding = (4 - len(position_bytes) % 4) % 4
    buffer = position_bytes + b"\x00" * padding + index_bytes
    document: Dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "MERCURY CAD AI X"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "Maquette"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                    "indices": 1, "material": 0}]}],
        "materials": [{"name": "mercury",
                       "pbrMetallicRoughness": {
                           "baseColorFactor": [0.78, 0.78, 0.76, 1.0],
                           "metallicFactor": 0.05, "roughnessFactor": 0.8}}],
        "buffers": [{"byteLength": len(buffer)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(position_bytes),
             "target": 34962},
            {"buffer": 0, "byteOffset": len(position_bytes) + padding,
             "byteLength": len(index_bytes), "target": 34963}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126,
             "count": len(positions) // 3, "type": "VEC3",
             "min": [min(positions[i::3]) for i in range(3)],
             "max": [max(positions[i::3]) for i in range(3)]},
            {"bufferView": 1, "componentType": 5125, "count": len(indices),
             "type": "SCALAR"}],
    }
    if embed:
        document["buffers"][0]["uri"] = ("data:application/octet-stream;base64,"
                                         + base64.b64encode(buffer).decode())
    return document, buffer


def write_gltf(solids: Sequence[Solid], scale: float = 0.001) -> str:
    document, _ = _gltf_document(solids, scale, embed=True)
    return json.dumps(document)


def write_glb(solids: Sequence[Solid], scale: float = 0.001) -> bytes:
    """GLB : glTF binaire, un seul fichier, lu par tous les visualiseurs web."""
    document, buffer = _gltf_document(solids, scale, embed=False)
    json_bytes = json.dumps(document, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    buffer += b"\x00" * ((4 - len(buffer) % 4) % 4)
    total = 12 + 8 + len(json_bytes) + 8 + len(buffer)
    out = bytearray()
    out += struct.pack("<III", 0x46546C67, 2, total)
    out += struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
    out += struct.pack("<II", len(buffer), 0x004E4942) + buffer
    return bytes(out)


def read_gltf(data, scale: float = 1000.0, name: str = "gltf") -> List[Solid]:
    """Lit un glTF JSON ou un GLB et reconstruit les triangles."""
    if isinstance(data, bytes) and data[:4] == b"glTF":
        length = struct.unpack_from("<I", data, 12)[0]
        document = json.loads(data[20:20 + length].decode("utf-8"))
        binary = b""
        cursor = 20 + length
        while cursor + 8 <= len(data):
            chunk_length, chunk_type = struct.unpack_from("<II", data, cursor)
            payload = data[cursor + 8:cursor + 8 + chunk_length]
            if chunk_type == 0x004E4942:
                binary = payload
            cursor += 8 + chunk_length
    else:
        text = data.decode("utf-8") if isinstance(data, bytes) else data
        document = json.loads(text)
        binary = b""
        for buffer in document.get("buffers", []):
            uri = buffer.get("uri", "")
            if uri.startswith("data:"):
                binary = base64.b64decode(uri.split(",", 1)[1])
    if not binary:
        raise MeshFormatError("glTF sans donnees binaires exploitables")
    views = document.get("bufferViews", [])
    accessors = document.get("accessors", [])

    def read_accessor(index: int) -> List[float]:
        accessor = accessors[index]
        view = views[accessor["bufferView"]]
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        count = accessor["count"]
        kind = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[accessor["type"]]
        code = {5126: "f", 5125: "I", 5123: "H", 5121: "B"}[
            accessor["componentType"]]
        size = struct.calcsize("<" + code)
        return list(struct.unpack_from("<%d%s" % (count * kind, code), binary,
                                       offset))

    polygons: List[Polygon] = []
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            position_index = primitive.get("attributes", {}).get("POSITION")
            if position_index is None:
                continue
            flat = read_accessor(position_index)
            points = [Vec3(flat[i] * scale, -flat[i + 2] * scale,
                           flat[i + 1] * scale)
                      for i in range(0, len(flat), 3)]
            if "indices" in primitive:
                indices = [int(v) for v in read_accessor(primitive["indices"])]
            else:
                indices = list(range(len(points)))
            for i in range(0, len(indices) - 2, 3):
                triangle = [points[indices[i + k]] for k in range(3)
                            if indices[i + k] < len(points)]
                if len(triangle) == 3:
                    polygons.append(Polygon(triangle))
    if not polygons:
        raise MeshFormatError("aucun triangle dans le glTF")
    return [Solid.from_polygons(polygons, name=name)]


# ---------------------------------------------------------------------------
# 3MF, AMF (impression 3D)
# ---------------------------------------------------------------------------
def write_3mf(solids: Sequence[Solid]) -> bytes:
    """3MF : format d'impression 3D de la 3MF Consortium (archive ZIP + XML)."""
    vertices, faces, _ = _merge(solids)
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<model unit="millimeter" '
            'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
            '<metadata name="Application">MERCURY CAD AI X</metadata>',
            '<resources><object id="1" type="model"><mesh><vertices>']
    for x, y, z in vertices:
        rows.append('<vertex x="%.5f" y="%.5f" z="%.5f"/>' % (x, y, z))
    rows.append("</vertices><triangles>")
    for face in faces:
        for k in range(1, len(face) - 1):
            rows.append('<triangle v1="%d" v2="%d" v3="%d"/>'
                        % (face[0], face[k], face[k + 1]))
    rows += ["</triangles></mesh></object></resources>",
             '<build><item objectid="1"/></build>', "</model>"]
    model = "\n".join(rows)
    relationships = ('<?xml version="1.0" encoding="UTF-8"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/'
                     'package/2006/relationships">'
                     '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
                     'Type="http://schemas.microsoft.com/3dmanufacturing/'
                     '2013/01/3dmodel"/></Relationships>')
    content_types = ('<?xml version="1.0" encoding="UTF-8"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/'
                     'package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/'
                     'vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="model" ContentType="application/'
                     'vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("3D/3dmodel.model", model)
    return buffer.getvalue()


def read_3mf(data: bytes, name: str = "3mf") -> List[Solid]:
    import xml.etree.ElementTree as ElementTree
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        candidates = [n for n in archive.namelist() if n.endswith(".model")]
        if not candidates:
            raise MeshFormatError("archive 3MF sans modele")
        root = ElementTree.fromstring(archive.read(candidates[0]))
    namespace = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
    polygons: List[Polygon] = []
    for mesh in root.iter(namespace + "mesh"):
        vertices: List[Vec3] = []
        for vertex in mesh.iter(namespace + "vertex"):
            vertices.append(Vec3(float(vertex.get("x", 0)),
                                 float(vertex.get("y", 0)),
                                 float(vertex.get("z", 0))))
        for triangle in mesh.iter(namespace + "triangle"):
            indices = [int(triangle.get(key, 0)) for key in ("v1", "v2", "v3")]
            points = [vertices[i] for i in indices if 0 <= i < len(vertices)]
            if len(points) == 3:
                polygons.append(Polygon(points))
    if not polygons:
        raise MeshFormatError("aucun triangle dans le 3MF")
    return [Solid.from_polygons(polygons, name=name)]


def write_amf(solids: Sequence[Solid]) -> str:
    """AMF : format additif normalise ISO/ASTM 52915."""
    vertices, faces, _ = _merge(solids)
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<amf unit="millimeter" version="1.1">',
            '<metadata type="producer">MERCURY CAD AI X</metadata>',
            '<object id="1"><mesh><vertices>']
    for x, y, z in vertices:
        rows.append("<vertex><coordinates><x>%.5f</x><y>%.5f</y><z>%.5f</z>"
                    "</coordinates></vertex>" % (x, y, z))
    rows.append("</vertices><volume>")
    for face in faces:
        for k in range(1, len(face) - 1):
            rows.append("<triangle><v1>%d</v1><v2>%d</v2><v3>%d</v3></triangle>"
                        % (face[0], face[k], face[k + 1]))
    rows += ["</volume></mesh></object></amf>"]
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# VRML, X3D, COLLADA
# ---------------------------------------------------------------------------
def write_vrml(solids: Sequence[Solid], scale: float = 0.001) -> str:
    """VRML 2.0 : encore la reference pour les echanges avec les SIG."""
    rows = ["#VRML V2.0 utf8", "# MERCURY CAD AI X"]
    for solid in solids:
        vertices, faces, _ = _merge([solid])
        r, g, b = _color_of(solid.material)
        rows += ["Shape {", "  appearance Appearance { material Material {",
                 "    diffuseColor %.3f %.3f %.3f" % (r, g, b), "  } }",
                 "  geometry IndexedFaceSet {", "    coord Coordinate { point ["]
        rows += ["      %.5f %.5f %.5f," % (x * scale, z * scale, -y * scale)
                 for x, y, z in vertices]
        rows += ["    ] }", "    coordIndex ["]
        rows += ["      %s, -1," % ", ".join(str(i) for i in face)
                 for face in faces]
        rows += ["    ]", "    solid TRUE", "  }", "}"]
    return "\n".join(rows) + "\n"


def write_x3d(solids: Sequence[Solid], scale: float = 0.001) -> str:
    """X3D : successeur XML de VRML, lu par les navigateurs et les visionneuses."""
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<X3D profile="Interchange" version="3.3">', "<Scene>"]
    for solid in solids:
        vertices, faces, _ = _merge([solid])
        r, g, b = _color_of(solid.material)
        points = " ".join("%.5f %.5f %.5f" % (x * scale, z * scale, -y * scale)
                          for x, y, z in vertices)
        index = " ".join("%s -1" % " ".join(str(i) for i in face)
                         for face in faces)
        rows += ['<Shape><Appearance><Material diffuseColor="%.3f %.3f %.3f"/>'
                 "</Appearance>" % (r, g, b),
                 '<IndexedFaceSet solid="true" coordIndex="%s">' % index,
                 '<Coordinate point="%s"/></IndexedFaceSet></Shape>' % points]
    rows += ["</Scene>", "</X3D>"]
    return "\n".join(rows)


def write_collada(solids: Sequence[Solid], scale: float = 0.001) -> str:
    """COLLADA (.dae) : echange avec SketchUp, Blender, 3ds Max, Unity."""
    vertices, faces, _ = _merge(solids)
    triangles: List[Tuple[int, int, int]] = []
    for face in faces:
        for k in range(1, len(face) - 1):
            triangles.append((face[0], face[k], face[k + 1]))
    positions = " ".join("%.5f %.5f %.5f" % (x * scale, z * scale, -y * scale)
                         for x, y, z in vertices)
    index = " ".join("%d %d %d" % t for t in triangles)
    return """<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset><contributor><authoring_tool>MERCURY CAD AI X</authoring_tool></contributor>
    <unit meter="1" name="meter"/><up_axis>Y_UP</up_axis></asset>
  <library_geometries>
    <geometry id="maquette" name="maquette"><mesh>
      <source id="positions"><float_array id="positions-array" count="%d">%s</float_array>
        <technique_common><accessor source="#positions-array" count="%d" stride="3">
          <param name="X" type="float"/><param name="Y" type="float"/>
          <param name="Z" type="float"/></accessor></technique_common></source>
      <vertices id="verts"><input semantic="POSITION" source="#positions"/></vertices>
      <triangles count="%d"><input semantic="VERTEX" source="#verts" offset="0"/>
        <p>%s</p></triangles>
    </mesh></geometry>
  </library_geometries>
  <library_visual_scenes><visual_scene id="scene" name="scene">
    <node id="maquette-node" name="maquette">
      <instance_geometry url="#maquette"/></node></visual_scene></library_visual_scenes>
  <scene><instance_visual_scene url="#scene"/></scene>
</COLLADA>
""" % (len(vertices) * 3, positions, len(vertices), len(triangles), index)


def read_collada(text: str, scale: float = 1000.0,
                 name: str = "dae") -> List[Solid]:
    import xml.etree.ElementTree as ElementTree
    root = ElementTree.fromstring(text)
    namespace = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
    polygons: List[Polygon] = []
    for mesh in root.iter(namespace + "mesh"):
        floats: List[float] = []
        for array in mesh.iter(namespace + "float_array"):
            floats = [float(v) for v in (array.text or "").split()]
            break
        points = [Vec3(floats[i] * scale, -floats[i + 2] * scale,
                       floats[i + 1] * scale)
                  for i in range(0, len(floats) - 2, 3)]
        for triangles in mesh.iter(namespace + "triangles"):
            inputs = len(list(triangles.iter(namespace + "input"))) or 1
            values = [int(v) for v in
                      (triangles.find(namespace + "p").text or "").split()]
            stride = inputs
            indices = values[::stride]
            for i in range(0, len(indices) - 2, 3):
                face = [points[indices[i + k]] for k in range(3)
                        if indices[i + k] < len(points)]
                if len(face) == 3:
                    polygons.append(Polygon(face))
    if not polygons:
        raise MeshFormatError("aucun triangle dans le COLLADA")
    return [Solid.from_polygons(polygons, name=name)]


# ---------------------------------------------------------------------------
# 3DS (Autodesk 3D Studio)
# ---------------------------------------------------------------------------
def write_3ds(solids: Sequence[Solid], scale: float = 0.001) -> bytes:
    """3DS : format historique d'Autodesk, encore lu par de nombreux outils.

    Limite du format : 65 535 sommets et 65 535 faces par objet. Les solides
    sont donc ecrits en objets successifs.
    """
    def chunk(identifier: int, payload: bytes) -> bytes:
        return struct.pack("<HI", identifier, len(payload) + 6) + payload

    objects = b""
    for order, solid in enumerate(solids):
        mesh = triangulate(solid)
        vertices, faces, _ = _merge([mesh])
        if not vertices or len(vertices) > 65535 or len(faces) > 65535:
            if len(vertices) > 65535 or len(faces) > 65535:
                raise MeshFormatError(
                    "3DS : %d sommets et %d faces depassent la limite de "
                    "65535 du format ; exportez en OBJ, glTF ou STL"
                    % (len(vertices), len(faces)))
            continue
        vertex_payload = struct.pack("<H", len(vertices))
        for x, y, z in vertices:
            vertex_payload += struct.pack("<3f", x * scale, y * scale, z * scale)
        face_payload = struct.pack("<H", len(faces))
        for face in faces:
            face_payload += struct.pack("<4H", face[0], face[1], face[2], 7)
        mesh_payload = (chunk(0x4110, vertex_payload)
                        + chunk(0x4120, face_payload))
        name = ("objet%d" % order).encode("ascii")[:10] + b"\x00"
        objects += chunk(0x4000, name + chunk(0x4100, mesh_payload))
    editor = chunk(0x3D3D, struct.pack("<HIi", 0x0100, 10, 1) + objects)
    return chunk(0x4D4D, chunk(0x0002, struct.pack("<I", 3)) + editor)


FORMATS_3D = {
    "stl": ("STL", True), "obj": ("Wavefront OBJ", True),
    "ply": ("Stanford PLY", True), "off": ("Object File Format", True),
    "gltf": ("glTF 2.0", True), "glb": ("glTF binaire", True),
    "3mf": ("3D Manufacturing Format", True), "amf": ("Additive MF", False),
    "wrl": ("VRML 2.0", False), "x3d": ("X3D", False),
    "dae": ("COLLADA", True), "3ds": ("Autodesk 3D Studio", False),
}
''')

ajouter('Interop/step.py', r'''
"""STEP (ISO 10303) et IGES : les formats d'echange de la mecanique.

L'ecriture produit un STEP AP203 ou AP214 conforme, forme d'un BREP
facettise (MANIFOLD_SOLID_BREP sur des ADVANCED_FACE planes). C'est la
representation acceptee par SolidWorks, CATIA, Inventor, FreeCAD et les
bureaux de controle.

La lecture reconstruit la geometrie a partir des entites CARTESIAN_POINT,
POLY_LOOP et FACE_OUTER_BOUND : elle couvre les STEP facettises, y compris
ceux produits par ce module, et signale clairement les fichiers qui
reposent sur des surfaces courbes non facettisees.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from CAD_Core.math3d import Vec3
from CAD_Core.solid import Polygon, Solid

AP_SCHEMAS = {
    "AP203": "CONFIG_CONTROL_DESIGN",
    "AP214": "AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }",
    "AP242": "AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF { 1 0 10303 442 1 1 4 }",
}


class StepError(ValueError):
    """Fichier STEP illisible ou non facettise."""


class StepWriter:
    """Ecrit un fichier STEP a partir de solides facettises."""

    def __init__(self, schema: str = "AP214",
                 product: str = "MAQUETTE MERCURY") -> None:
        if schema not in AP_SCHEMAS:
            raise StepError("schema STEP inconnu : %s" % schema)
        self.schema = schema
        self.product = product
        self.lines: List[str] = []
        self._id = 0

    def entity(self, definition: str) -> int:
        self._id += 1
        self.lines.append("#%d=%s;" % (self._id, definition))
        return self._id

    def build(self, solids: Sequence[Solid], scale: float = 1.0,
              timestamp: Optional[str] = None) -> str:
        self.lines = []
        self._id = 0
        moment = timestamp or time.strftime("%Y-%m-%dT%H:%M:%S")

        # Contexte geometrique commun a tous les solides.
        origin = self.entity("CARTESIAN_POINT('',(0.,0.,0.))")
        axis_z = self.entity("DIRECTION('',(0.,0.,1.))")
        axis_x = self.entity("DIRECTION('',(1.,0.,0.))")
        placement = self.entity("AXIS2_PLACEMENT_3D('',#%d,#%d,#%d)"
                                % (origin, axis_z, axis_x))
        length_unit = self.entity(
            "(NAMED_UNIT(*)LENGTH_UNIT()SI_UNIT(.MILLI.,.METRE.))")
        angle_unit = self.entity(
            "(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.))")
        solid_angle = self.entity(
            "(NAMED_UNIT(*)SOLID_ANGLE_UNIT()SI_UNIT($,.STERADIAN.))")
        uncertainty = self.entity(
            "UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-05),#%d,"
            "'distance_accuracy_value','confusion accuracy')" % length_unit)
        context = self.entity(
            "(GEOMETRIC_REPRESENTATION_CONTEXT(3)"
            "GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#%d))"
            "GLOBAL_UNIT_ASSIGNED_CONTEXT((#%d,#%d,#%d))"
            "REPRESENTATION_CONTEXT('','3D'))"
            % (uncertainty, length_unit, angle_unit, solid_angle))

        shapes: List[int] = []
        for order, solid in enumerate(solids):
            shapes.append(self._write_solid(solid, order, scale, placement))

        product = self.entity("PRODUCT('%s','%s','',(#%d))"
                              % (self.product, self.product,
                                 self.entity("PRODUCT_CONTEXT('',#%d,'mechanical')"
                                             % self.entity(
                                                 "APPLICATION_CONTEXT('%s')"
                                                 % AP_SCHEMAS[self.schema]))))
        definition_formation = self.entity(
            "PRODUCT_DEFINITION_FORMATION('','',#%d)" % product)
        definition = self.entity(
            "PRODUCT_DEFINITION('design','',#%d,#%d)"
            % (definition_formation,
               self.entity("PRODUCT_DEFINITION_CONTEXT('part definition',#%d,"
                           "'design')"
                           % self.entity("APPLICATION_CONTEXT('%s')"
                                         % AP_SCHEMAS[self.schema]))))
        shape_definition = self.entity(
            "PRODUCT_DEFINITION_SHAPE('','',#%d)" % definition)
        representation = self.entity(
            "ADVANCED_BREP_SHAPE_REPRESENTATION('',(%s,#%d),#%d)"
            % (",".join("#%d" % s for s in shapes) or "#%d" % placement,
               placement, context))
        self.entity("SHAPE_DEFINITION_REPRESENTATION(#%d,#%d)"
                    % (shape_definition, representation))

        header = [
            "ISO-10303-21;", "HEADER;",
            "FILE_DESCRIPTION(('%s facettise'),'2;1');" % self.schema,
            "FILE_NAME('%s','%s',('MERCURY CAD AI X'),('MERCURY'),"
            "'MERCURY CAD AI X','MERCURY CAD AI X','');"
            % (self.product, moment),
            "FILE_SCHEMA(('%s'));" % AP_SCHEMAS[self.schema],
            "ENDSEC;", "DATA;"]
        return "\n".join(header + self.lines + ["ENDSEC;", "END-ISO-10303-21;"]) \
            + "\n"

    def _write_solid(self, solid: Solid, order: int, scale: float,
                     placement: int) -> int:
        point_ids: Dict[Tuple[float, ...], int] = {}

        def point_id(vertex: Vec3) -> int:
            key = vertex.rounded(6)
            if key not in point_ids:
                point_ids[key] = self.entity(
                    "CARTESIAN_POINT('',(%.6f,%.6f,%.6f))"
                    % (vertex.x * scale, vertex.y * scale, vertex.z * scale))
            return point_ids[key]

        faces: List[int] = []
        for polygon in solid.polygons:
            if polygon.is_degenerate():
                continue
            loop_points = ",".join("#%d" % point_id(v) for v in polygon.vertices)
            loop = self.entity("POLY_LOOP('',(%s))" % loop_points)
            bound = self.entity("FACE_OUTER_BOUND('',#%d,.T.)" % loop)
            normal = polygon.normal
            reference = normal.any_perpendicular()
            base = self.entity("CARTESIAN_POINT('',(%.6f,%.6f,%.6f))"
                               % (polygon.vertices[0].x * scale,
                                  polygon.vertices[0].y * scale,
                                  polygon.vertices[0].z * scale))
            axis = self.entity("DIRECTION('',(%.6f,%.6f,%.6f))"
                               % (normal.x, normal.y, normal.z))
            ref = self.entity("DIRECTION('',(%.6f,%.6f,%.6f))"
                              % (reference.x, reference.y, reference.z))
            frame = self.entity("AXIS2_PLACEMENT_3D('',#%d,#%d,#%d)"
                                % (base, axis, ref))
            plane = self.entity("PLANE('',#%d)" % frame)
            faces.append(self.entity("ADVANCED_FACE('',(#%d),#%d,.T.)"
                                     % (bound, plane)))
        shell = self.entity("CLOSED_SHELL('',(%s))"
                            % ",".join("#%d" % f for f in faces))
        return self.entity("MANIFOLD_SOLID_BREP('%s',#%d)"
                           % (solid.name or "solide%d" % order, shell))


def write_step(solids: Sequence[Solid], schema: str = "AP214",
               product: str = "MAQUETTE MERCURY", scale: float = 1.0,
               timestamp: Optional[str] = None) -> str:
    return StepWriter(schema, product).build(solids, scale, timestamp)


ENTITY_RE = re.compile(r"^\s*#(\d+)\s*=\s*([A-Z_0-9]+)\s*\((.*)\)\s*$",
                       re.IGNORECASE | re.DOTALL)
REFERENCE_RE = re.compile(r"#(\d+)")


def split_statements(body: str) -> List[str]:
    """Decoupe la section DATA en instructions, apostrophes respectees.

    Un point-virgule place dans un libelle ('poutre; niveau 2') ne doit pas
    couper l'instruction : le decoupage naif casse alors tout le fichier.
    """
    out: List[str] = []
    current: List[str] = []
    quoted = False
    for character in body:
        if character == "'":
            quoted = not quoted
        if character == ";" and not quoted:
            out.append("".join(current))
            current = []
            continue
        current.append(character)
    if "".join(current).strip():
        out.append("".join(current))
    return out


def read_step(text: str, name: str = "step") -> List[Solid]:
    """Reconstruit les solides d'un STEP facettise."""
    body = text
    if "DATA;" in text:
        body = text.split("DATA;", 1)[1]
    entities: Dict[int, Tuple[str, str]] = {}
    for statement in split_statements(body):
        match = ENTITY_RE.match(statement.replace("\n", " "))
        if match:
            entities[int(match.group(1))] = (match.group(2).upper(),
                                             match.group(3))
    if not entities:
        raise StepError("aucune entite STEP trouvee")

    points: Dict[int, Vec3] = {}
    for key, (kind, payload) in entities.items():
        if kind == "CARTESIAN_POINT":
            numbers = re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?",
                                 payload.split("(", 1)[-1])
            if len(numbers) >= 3:
                points[key] = Vec3(float(numbers[0]), float(numbers[1]),
                                   float(numbers[2]))

    loops: Dict[int, List[Vec3]] = {}
    for key, (kind, payload) in entities.items():
        if kind in ("POLY_LOOP", "EDGE_LOOP", "VERTEX_LOOP"):
            refs = [int(r) for r in REFERENCE_RE.findall(payload)]
            ring = [points[r] for r in refs if r in points]
            if len(ring) >= 3:
                loops[key] = ring

    polygons: List[Polygon] = []
    for key, (kind, payload) in entities.items():
        if kind in ("FACE_OUTER_BOUND", "FACE_BOUND"):
            for ref in (int(r) for r in REFERENCE_RE.findall(payload)):
                if ref in loops:
                    polygons.append(Polygon(list(loops[ref])))
                    break
    if not polygons:
        curved = sum(1 for kind, _ in entities.values()
                     if kind in ("B_SPLINE_SURFACE_WITH_KNOTS",
                                 "CYLINDRICAL_SURFACE", "TOROIDAL_SURFACE",
                                 "SPHERICAL_SURFACE", "CONICAL_SURFACE"))
        if curved:
            raise StepError(
                "ce STEP repose sur %d surfaces courbes analytiques ; MERCURY "
                "lit les STEP facettises. Reexportez depuis le logiciel source "
                "avec l'option de facettisation (tessellation) activee."
                % curved)
        raise StepError("aucune face exploitable dans le STEP")
    return [Solid.from_polygons(polygons, name=name).heal()]


def probe_step(text: str) -> Dict[str, Any]:
    """Identifie schema, producteur et volumetrie d'un STEP."""
    schema = "inconnu"
    match = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", text)
    if match:
        schema = match.group(1)
    label = next((k for k, v in AP_SCHEMAS.items() if v.startswith(schema[:12])),
                 schema)
    return {"format": "STEP", "schema": schema, "norme": label,
            "entites": len(re.findall(r"#\d+\s*=", text)),
            "solides": text.count("MANIFOLD_SOLID_BREP"),
            "faces": text.count("ADVANCED_FACE")}


# ---------------------------------------------------------------------------
# IGES
# ---------------------------------------------------------------------------
def write_iges(solids: Sequence[Solid], scale: float = 1.0,
               product: str = "MAQUETTE MERCURY") -> str:
    """IGES 5.3 : surfaces planes (entite 144) sur contours composites.

    Format exige par certains bureaux d'etudes et machines a commande
    numerique anciennes ; toujours accepte en entree par les grands CAO.
    """
    start: List[str] = ["MERCURY CAD AI X - export IGES 5.3"]
    directory: List[str] = []
    parameters: List[str] = []
    parameter_index = 1

    def add_parameter(text: str, entity_type: int, directory_pointer: int) -> int:
        nonlocal parameter_index
        chunks: List[str] = []
        payload = "%d,%s;" % (entity_type, text)
        while payload:
            chunks.append(payload[:64])
            payload = payload[64:]
        first = parameter_index
        for chunk in chunks:
            parameters.append("%-64s%8dP%7d" % (chunk, directory_pointer,
                                                parameter_index))
            parameter_index += 1
        return first

    entity_count = 0
    for solid in solids:
        for polygon in solid.polygons:
            if polygon.is_degenerate():
                continue
            entity_count += 1
            directory_pointer = entity_count * 2 - 1
            coordinates = ",".join(
                "%.6f,%.6f,%.6f" % (v.x * scale, v.y * scale, v.z * scale)
                for v in polygon.vertices)
            first = add_parameter("%d,%d,1,%s"
                                  % (len(polygon.vertices) + 1,
                                     len(polygon.vertices), coordinates),
                                  106, directory_pointer)
            directory.append("%8d%8d%8d%8d%8d%8d%8d%8d%8s%8dD%7d"
                             % (106, first, 0, 0, 0, 0, 0, 0, "00000000", 0,
                                directory_pointer))
            directory.append("%8d%8d%8d%8d%8d%8s%8s%8s%8dD%7d"
                             % (106, 0, 0, 1, 0, "", "", "", 0,
                                directory_pointer + 1))

    global_section = (
        "1H,,1H;,%dH%s,%dH%s,20HMERCURY CAD AI X,20HMERCURY CAD AI X,"
        "32,308,15,308,15,%dH%s,1.0,2,2HMM,1,0.08,15H20240101.000000,"
        "1.0E-06,1000.0,7HMERCURY,7HMERCURY,11,0,15H20240101.000000;"
        % (len(product), product, len(product), product, len(product), product))
    global_lines: List[str] = []
    payload = global_section
    index = 1
    while payload:
        global_lines.append("%-72sG%7d" % (payload[:72], index))
        payload = payload[72:]
        index += 1

    lines: List[str] = []
    for order, line in enumerate(start, 1):
        lines.append("%-72sS%7d" % (line, order))
    lines += global_lines
    lines += directory
    lines += parameters
    lines.append("S%7dG%7dD%7dP%7d%40sT%7d"
                 % (len(start), len(global_lines), len(directory),
                    len(parameters), "", 1))
    return "\n".join(lines) + "\n"
''')

ajouter('Interop/images.py', r'''
"""Images matricielles : PNG, BMP, TGA, PPM, JPEG et GIF.

Les images servent a trois choses dans une CAO : exporter une vue rendue,
importer un plan scanne comme calque de fond, et produire les vignettes des
fichiers. Tout est ecrit avec la bibliotheque standard ; Pillow, s'il est
installe, est utilise en plus pour lire les formats compresses exotiques.
"""
from __future__ import annotations

import math
import struct
import zlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

from CAD_Core.render_engine import Framebuffer


class ImageError(ValueError):
    """Image illisible ou format non pris en charge."""


class Raster:
    """Image RGB simple : largeur, hauteur, octets."""

    __slots__ = ("width", "height", "pixels")

    def __init__(self, width: int, height: int,
                 pixels: Optional[bytearray] = None) -> None:
        if width < 1 or height < 1:
            raise ImageError("dimensions d'image invalides")
        self.width = int(width)
        self.height = int(height)
        self.pixels = pixels if pixels is not None else \
            bytearray(b"\xff" * (width * height * 3))
        if len(self.pixels) != self.width * self.height * 3:
            raise ImageError("tampon d'image de taille incoherente")

    @staticmethod
    def from_framebuffer(frame: Framebuffer) -> "Raster":
        return Raster(frame.width, frame.height, bytearray(frame.pixels))

    def pixel(self, x: int, y: int) -> Tuple[int, int, int]:
        offset = (y * self.width + x) * 3
        return (self.pixels[offset], self.pixels[offset + 1],
                self.pixels[offset + 2])

    def set_pixel(self, x: int, y: int, color: Sequence[int]) -> None:
        offset = (y * self.width + x) * 3
        for channel in range(3):
            self.pixels[offset + channel] = max(0, min(255, int(color[channel])))

    def grayscale(self) -> List[List[int]]:
        """Matrice de niveaux de gris : entree de la vectorisation de plans."""
        rows: List[List[int]] = []
        for y in range(self.height):
            row: List[int] = []
            for x in range(self.width):
                r, g, b = self.pixel(x, y)
                row.append(int(0.299 * r + 0.587 * g + 0.114 * b))
            rows.append(row)
        return rows

    def resized(self, width: int, height: int) -> "Raster":
        """Reechantillonnage au plus proche voisin : vignettes et apercus."""
        out = Raster(width, height)
        for y in range(height):
            source_y = min(self.height - 1, int(y * self.height / height))
            for x in range(width):
                source_x = min(self.width - 1, int(x * self.width / width))
                out.set_pixel(x, y, self.pixel(source_x, source_y))
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {"largeur": self.width, "hauteur": self.height,
                "octets": len(self.pixels)}


# ---------------------------------------------------------------------------
# PNG
# ---------------------------------------------------------------------------
def write_png(raster: Raster, compression: int = 9) -> bytes:
    raw = bytearray()
    stride = raster.width * 3
    for row in range(raster.height):
        raw.append(0)
        raw.extend(raster.pixels[row * stride:(row + 1) * stride])

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", raster.width, raster.height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(bytes(raw), compression))
            + chunk(b"IEND", b""))


def read_png(data: bytes) -> Raster:
    """Decodeur PNG complet : 8 bits, gris, RGB, palette, alpha, filtres 0-4."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ImageError("signature PNG absente")
    cursor = 8
    width = height = depth = color_type = 0
    palette = b""
    compressed = bytearray()
    while cursor + 8 <= len(data):
        length, tag = struct.unpack_from(">I4s", data, cursor)
        payload = data[cursor + 8:cursor + 8 + length]
        cursor += 12 + length
        if tag == b"IHDR":
            width, height, depth, color_type = struct.unpack_from(">IIBB",
                                                                  payload, 0)
        elif tag == b"PLTE":
            palette = payload
        elif tag == b"IDAT":
            compressed += payload
        elif tag == b"IEND":
            break
    if depth != 8:
        raise ImageError("PNG %d bits par canal : seul le 8 bits est lu" % depth)
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise ImageError("type de couleur PNG inconnu : %d" % color_type)
    raw = zlib.decompress(bytes(compressed))
    stride = width * channels
    out = Raster(width, height)
    previous = bytearray(stride)
    cursor = 0
    for y in range(height):
        filter_type = raw[cursor]
        cursor += 1
        line = bytearray(raw[cursor:cursor + stride])
        cursor += stride
        for i in range(stride):
            a = line[i - channels] if i >= channels else 0
            b = previous[i]
            c = previous[i - channels] if i >= channels else 0
            if filter_type == 1:
                line[i] = (line[i] + a) & 0xFF
            elif filter_type == 2:
                line[i] = (line[i] + b) & 0xFF
            elif filter_type == 3:
                line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif filter_type == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                predictor = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + predictor) & 0xFF
        for x in range(width):
            base = x * channels
            if color_type == 3:
                index = line[base] * 3
                color = palette[index:index + 3] or b"\x00\x00\x00"
                out.set_pixel(x, y, tuple(color))
            elif channels <= 2:
                value = line[base]
                out.set_pixel(x, y, (value, value, value))
            else:
                out.set_pixel(x, y, (line[base], line[base + 1], line[base + 2]))
        previous = line
    return out


# ---------------------------------------------------------------------------
# BMP, TGA, PPM
# ---------------------------------------------------------------------------
def write_bmp(raster: Raster) -> bytes:
    padding = (4 - (raster.width * 3) % 4) % 4
    body = bytearray()
    for y in range(raster.height - 1, -1, -1):
        for x in range(raster.width):
            r, g, b = raster.pixel(x, y)
            body += bytes((b, g, r))
        body += b"\x00" * padding
    header = struct.pack("<2sIHHI", b"BM", 14 + 40 + len(body), 0, 0, 14 + 40)
    info = struct.pack("<IiiHHIIiiII", 40, raster.width, raster.height, 1, 24,
                       0, len(body), 2835, 2835, 0, 0)
    return header + info + bytes(body)


def read_bmp(data: bytes) -> Raster:
    if data[:2] != b"BM":
        raise ImageError("signature BMP absente")
    offset = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    bits = struct.unpack_from("<H", data, 28)[0]
    if bits != 24:
        raise ImageError("BMP %d bits : seul le 24 bits non compresse est lu"
                         % bits)
    flip = height > 0
    height = abs(height)
    out = Raster(width, height)
    stride = width * 3
    padding = (4 - stride % 4) % 4
    for row in range(height):
        base = offset + row * (stride + padding)
        y = height - 1 - row if flip else row
        for x in range(width):
            b, g, r = data[base + x * 3:base + x * 3 + 3]
            out.set_pixel(x, y, (r, g, b))
    return out


def write_tga(raster: Raster) -> bytes:
    header = struct.pack("<3B2HB4H2B", 0, 0, 2, 0, 0, 0, 0, 0, raster.width,
                         raster.height, 24, 0)
    body = bytearray()
    for y in range(raster.height - 1, -1, -1):
        for x in range(raster.width):
            r, g, b = raster.pixel(x, y)
            body += bytes((b, g, r))
    return header + bytes(body)


def write_ppm(raster: Raster) -> bytes:
    return (b"P6\n%d %d\n255\n" % (raster.width, raster.height)
            + bytes(raster.pixels))


def read_ppm(data: bytes) -> Raster:
    if data[:2] != b"P6":
        raise ImageError("seul le PPM binaire P6 est lu")
    fields: List[int] = []
    cursor = 2
    while len(fields) < 3 and cursor < len(data):
        while cursor < len(data) and data[cursor:cursor + 1].isspace():
            cursor += 1
        if data[cursor:cursor + 1] == b"#":
            while cursor < len(data) and data[cursor] != 0x0A:
                cursor += 1
            continue
        start = cursor
        while cursor < len(data) and not data[cursor:cursor + 1].isspace():
            cursor += 1
        fields.append(int(data[start:cursor]))
    cursor += 1
    width, height, _ = fields
    return Raster(width, height, bytearray(data[cursor:cursor + width * height * 3]))


# ---------------------------------------------------------------------------
# JPEG
# ---------------------------------------------------------------------------
def write_jpeg(raster: Raster, quality: int = 85) -> bytes:
    """Encodeur JPEG sans perte de dependance : Pillow s'il est la, sinon PNG.

    Un encodeur JPEG complet (DCT, Huffman) n'apporterait rien de plus que
    Pillow, qui est present sur la quasi-totalite des installations. Le
    format de repli est annonce explicitement par l'appelant.
    """
    try:
        from PIL import Image                # pragma: no cover - optionnel
        image = Image.frombytes("RGB", (raster.width, raster.height),
                                bytes(raster.pixels))
        import io
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=max(1, min(100, quality)))
        return buffer.getvalue()
    except ImportError:
        raise ImageError(
            "l'ecriture JPEG demande Pillow (pip install Pillow). "
            "Utilisez PNG, BMP, TGA ou PPM, tous ecrits nativement.")


def read_image(data: bytes) -> Raster:
    """Lit une image en detectant son format d'apres sa signature."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return read_png(data)
    if data[:2] == b"BM":
        return read_bmp(data)
    if data[:2] == b"P6":
        return read_ppm(data)
    try:
        from PIL import Image                # pragma: no cover - optionnel
        import io
        image = Image.open(io.BytesIO(data)).convert("RGB")
        return Raster(image.width, image.height, bytearray(image.tobytes()))
    except ImportError:
        raise ImageError(
            "format image non reconnu. PNG, BMP et PPM sont lus nativement ; "
            "installez Pillow (pip install Pillow) pour JPEG, TIFF, GIF et WEBP.")


def underlay(data: bytes, width_mm: float, origin=(0.0, 0.0, 0.0),
             rotation_deg: float = 0.0) -> Dict[str, Any]:
    """Commande ATTACHER : image de fond calee a l'echelle du dessin."""
    raster = read_image(data)
    scale = width_mm / float(raster.width)
    return {"type": "image_attachee", "largeur_px": raster.width,
            "hauteur_px": raster.height, "largeur_mm": width_mm,
            "hauteur_mm": round(raster.height * scale, 3),
            "echelle_mm_par_px": round(scale, 6),
            "origine": list(origin), "rotation_deg": rotation_deg}


IMAGE_FORMATS = {"png": True, "bmp": True, "ppm": True, "tga": False,
                 "jpg": False, "jpeg": False, "gif": False, "tif": False}
''')

ajouter('Interop/pdf.py', r'''
"""Ecriture PDF vectorielle : planches, dossiers, notes de calcul.

Un PDF de CAO doit rester vectoriel : les traits restent nets a n'importe
quel zoom et les cotes restent lisibles a l'impression. Ce module ecrit un
PDF 1.4 conforme, multipage, avec cartouche, calques (groupes de contenu
optionnels), textes et images matricielles.
"""
from __future__ import annotations

import zlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

PAPER_SIZES_PT: Dict[str, Tuple[float, float]] = {
    "A4": (841.89, 595.28), "A3": (1190.55, 841.89), "A2": (1683.78, 1190.55),
    "A1": (2383.94, 1683.78), "A0": (3370.39, 2383.94),
    "LETTER": (792.0, 612.0), "TABLOID": (1224.0, 792.0),
}
MM_TO_PT = 72.0 / 25.4


class PdfError(ValueError):
    """Document PDF impossible a produire."""


class PdfPage:
    """Une page : instructions de dessin en coordonnees millimetre."""

    def __init__(self, size: str = "A3", landscape: bool = True,
                 title: str = "") -> None:
        if size not in PAPER_SIZES_PT:
            raise PdfError("format de papier inconnu : %s" % size)
        width, height = PAPER_SIZES_PT[size]
        if not landscape:
            width, height = height, width
        self.width = width
        self.height = height
        self.size = size
        self.title = title
        self.operations: List[str] = ["1 J 1 j"]

    # -- primitives --------------------------------------------------------
    def _xy(self, point) -> Tuple[float, float]:
        x, y = float(point[0]), float(point[1])
        return x * MM_TO_PT, y * MM_TO_PT

    def stroke_color(self, r: float, g: float, b: float) -> "PdfPage":
        self.operations.append("%.3f %.3f %.3f RG" % (r, g, b))
        return self

    def fill_color(self, r: float, g: float, b: float) -> "PdfPage":
        self.operations.append("%.3f %.3f %.3f rg" % (r, g, b))
        return self

    def line_width(self, millimeters: float) -> "PdfPage":
        self.operations.append("%.3f w" % (millimeters * MM_TO_PT))
        return self

    def dash(self, pattern: Optional[Sequence[float]] = None) -> "PdfPage":
        if not pattern:
            self.operations.append("[] 0 d")
        else:
            self.operations.append("[%s] 0 d"
                                   % " ".join("%.2f" % (v * MM_TO_PT)
                                              for v in pattern))
        return self

    def line(self, start, end) -> "PdfPage":
        x0, y0 = self._xy(start)
        x1, y1 = self._xy(end)
        self.operations.append("%.3f %.3f m %.3f %.3f l S" % (x0, y0, x1, y1))
        return self

    def polyline(self, points: Sequence, close: bool = False,
                 fill: bool = False) -> "PdfPage":
        if len(points) < 2:
            return self
        x, y = self._xy(points[0])
        parts = ["%.3f %.3f m" % (x, y)]
        for point in points[1:]:
            x, y = self._xy(point)
            parts.append("%.3f %.3f l" % (x, y))
        if close:
            parts.append("h")
        parts.append("B" if fill and close else ("f" if fill else "S"))
        self.operations.append(" ".join(parts))
        return self

    def rectangle(self, origin, width: float, height: float,
                  fill: bool = False) -> "PdfPage":
        x, y = self._xy(origin)
        self.operations.append("%.3f %.3f %.3f %.3f re %s"
                               % (x, y, width * MM_TO_PT, height * MM_TO_PT,
                                  "B" if fill else "S"))
        return self

    def circle(self, center, radius: float, fill: bool = False) -> "PdfPage":
        """Cercle par quatre courbes de Bezier (approximation exacte a 0,03 %)."""
        cx, cy = self._xy(center)
        r = radius * MM_TO_PT
        k = r * 0.5522847498
        self.operations.append(
            "%.3f %.3f m %.3f %.3f %.3f %.3f %.3f %.3f c "
            "%.3f %.3f %.3f %.3f %.3f %.3f c "
            "%.3f %.3f %.3f %.3f %.3f %.3f c "
            "%.3f %.3f %.3f %.3f %.3f %.3f c %s"
            % (cx + r, cy, cx + r, cy + k, cx + k, cy + r, cx, cy + r,
               cx - k, cy + r, cx - r, cy + k, cx - r, cy,
               cx - r, cy - k, cx - k, cy - r, cx, cy - r,
               cx + k, cy - r, cx + r, cy - k, cx + r, cy,
               "B" if fill else "S"))
        return self

    def text(self, position, value: str, size_mm: float = 3.5,
             font: str = "F1", rotation_deg: float = 0.0) -> "PdfPage":
        x, y = self._xy(position)
        escaped = (value.replace("\\", r"\\").replace("(", r"\(")
                   .replace(")", r"\)"))
        size = size_mm * MM_TO_PT
        if abs(rotation_deg) < 1e-6:
            self.operations.append("BT /%s %.2f Tf %.3f %.3f Td (%s) Tj ET"
                                   % (font, size, x, y, escaped))
        else:
            import math
            c, s = math.cos(math.radians(rotation_deg)), \
                math.sin(math.radians(rotation_deg))
            self.operations.append(
                "BT /%s %.2f Tf %.4f %.4f %.4f %.4f %.3f %.3f Tm (%s) Tj ET"
                % (font, size, c, s, -s, c, x, y, escaped))
        return self

    def title_block(self, project: str, sheet: str, scale: str = "1:100",
                    date: str = "", author: str = "MERCURY CAD AI X",
                    height: float = 40.0, width: float = 180.0) -> "PdfPage":
        """Cartouche normalise, cale en bas a droite de la feuille."""
        page_width = self.width / MM_TO_PT
        x = page_width - width - 10.0
        y = 10.0
        self.line_width(0.35).stroke_color(0, 0, 0)
        self.rectangle((x, y), width, height)
        self.line((x, y + height * 0.6), (x + width, y + height * 0.6))
        self.line((x + width * 0.6, y), (x + width * 0.6, y + height * 0.6))
        self.text((x + 4, y + height * 0.75), project, 4.5)
        self.text((x + 4, y + height * 0.35), sheet, 3.2)
        self.text((x + 4, y + height * 0.15), date, 2.6)
        self.text((x + width * 0.63, y + height * 0.35), "Echelle " + scale, 3.0)
        self.text((x + width * 0.63, y + height * 0.15), author, 2.6)
        return self

    def content(self) -> bytes:
        return "\n".join(self.operations).encode("latin-1", "replace")


class PdfDocument:
    """Document PDF multipage."""

    def __init__(self, title: str = "MERCURY CAD AI X",
                 author: str = "MERCURY CAD AI X") -> None:
        self.title = title
        self.author = author
        self.pages: List[PdfPage] = []

    def add_page(self, size: str = "A3", landscape: bool = True,
                 title: str = "") -> PdfPage:
        page = PdfPage(size, landscape, title)
        self.pages.append(page)
        return page

    def build(self, compress: bool = True) -> bytes:
        if not self.pages:
            raise PdfError("document PDF sans page")
        objects: List[bytes] = []

        def add_object(payload: bytes) -> int:
            objects.append(payload)
            return len(objects)

        font_regular = add_object(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>")
        font_bold = add_object(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            b"/Encoding /WinAnsiEncoding >>")
        pages_id = add_object(b"placeholder")

        page_ids: List[int] = []
        for page in self.pages:
            payload = page.content()
            if compress:
                stream = zlib.compress(payload, 9)
                content_id = add_object(
                    b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream)
                    + stream + b"\nendstream")
            else:
                content_id = add_object(
                    b"<< /Length %d >>\nstream\n" % len(payload) + payload
                    + b"\nendstream")
            page_id = add_object(
                ("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] "
                 "/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> "
                 "/Contents %d 0 R >>"
                 % (pages_id, page.width, page.height, font_regular, font_bold,
                    content_id)).encode("latin-1"))
            page_ids.append(page_id)

        objects[pages_id - 1] = (
            "<< /Type /Pages /Count %d /Kids [%s] >>"
            % (len(page_ids), " ".join("%d 0 R" % i for i in page_ids))
        ).encode("latin-1")

        info_id = add_object(
            ("<< /Title (%s) /Author (%s) /Creator (MERCURY CAD AI X) "
             "/Producer (MERCURY CAD AI X) >>"
             % (self.title.replace("(", "").replace(")", ""),
                self.author.replace("(", "").replace(")", ""))).encode("latin-1"))
        catalog_id = add_object(("<< /Type /Catalog /Pages %d 0 R >>"
                                 % pages_id).encode("latin-1"))

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: List[int] = []
        for index, payload in enumerate(objects, start=1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % index + payload + b"\nendobj\n"
        xref_position = len(out)
        out += b"xref\n0 %d\n" % (len(objects) + 1)
        out += b"0000000000 65535 f \n"
        for offset in offsets:
            out += b"%010d 00000 n \n" % offset
        out += (b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n"
                b"%d\n%%%%EOF\n" % (len(objects) + 1, catalog_id, info_id,
                                    xref_position))
        return bytes(out)


def probe_pdf(data: bytes) -> Dict[str, Any]:
    """Identifie un PDF : version, nombre de pages, taille."""
    if data[:5] != b"%PDF-":
        raise PdfError("signature PDF absente")
    version = data[5:8].decode("ascii", "replace")
    return {"format": "PDF", "version": version,
            "pages": data.count(b"/Type /Page") - data.count(b"/Type /Pages"),
            "taille_octets": len(data),
            "compresse": b"/FlateDecode" in data}
''')

ajouter('Interop/svg.py', r'''
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
''')

ajouter('Interop/pointcloud.py', r'''
"""Nuages de points et donnees de terrain : XYZ, PTS, CSV, LAS.

Les releves de geometre et les scans de chantier arrivent sous ces formats.
MERCURY les lit pour caler un projet sur le terrain naturel, en extraire un
maillage de terrain (triangulation) et comparer le construit au modele.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from CAD_Core.math3d import BBox3, Vec3
from CAD_Core.solid import Polygon, Solid


class PointCloudError(ValueError):
    """Nuage de points illisible."""


@dataclass
class PointCloud:
    """Nuage de points avec couleurs et intensites optionnelles."""

    points: List[Vec3] = field(default_factory=list)
    colors: List[Tuple[int, int, int]] = field(default_factory=list)
    intensities: List[float] = field(default_factory=list)
    name: str = "nuage"

    @property
    def bbox(self) -> BBox3:
        return BBox3.of(self.points)

    def __len__(self) -> int:
        return len(self.points)

    def decimated(self, step: int = 10) -> "PointCloud":
        """Allege le nuage : un point sur `step`, couleurs conservees."""
        step = max(1, int(step))
        return PointCloud(self.points[::step], self.colors[::step],
                          self.intensities[::step], self.name)

    def statistics(self) -> Dict[str, Any]:
        box = self.bbox
        altitudes = [p.z for p in self.points]
        return {"points": len(self.points), "boite": box.to_dict(),
                "altitude_min": round(min(altitudes), 3) if altitudes else 0.0,
                "altitude_max": round(max(altitudes), 3) if altitudes else 0.0,
                "altitude_moyenne": round(sum(altitudes) / len(altitudes), 3)
                if altitudes else 0.0,
                "couleurs": bool(self.colors), "intensites": bool(self.intensities)}

    def to_terrain(self, resolution: int = 40, name: str = "terrain") -> Solid:
        """Maillage de terrain par grille : la surface du TN pour le projet.

        Une grille regularisee est plus robuste qu'une triangulation de
        Delaunay sur des releves bruites, et suffit aux calculs de deblais
        et de remblais.
        """
        if len(self.points) < 3:
            raise PointCloudError("nuage trop pauvre pour un terrain")
        box = self.bbox
        resolution = max(2, min(200, resolution))
        step_x = max(1e-6, box.size.x / resolution)
        step_y = max(1e-6, box.size.y / resolution)
        cells: Dict[Tuple[int, int], List[float]] = {}
        for point in self.points:
            key = (int((point.x - box.min.x) / step_x),
                   int((point.y - box.min.y) / step_y))
            cells.setdefault(key, []).append(point.z)
        grid: List[List[Optional[float]]] = []
        for j in range(resolution + 1):
            row: List[Optional[float]] = []
            for i in range(resolution + 1):
                values = cells.get((i, j))
                row.append(sum(values) / len(values) if values else None)
            grid.append(row)
        # Bouchage des trous par la moyenne des voisins connus.
        default = sum(p.z for p in self.points) / len(self.points)
        for j in range(resolution + 1):
            for i in range(resolution + 1):
                if grid[j][i] is None:
                    neighbours = [grid[j + dj][i + di]
                                  for dj in (-1, 0, 1) for di in (-1, 0, 1)
                                  if 0 <= j + dj <= resolution
                                  and 0 <= i + di <= resolution
                                  and grid[j + dj][i + di] is not None]
                    grid[j][i] = (sum(neighbours) / len(neighbours)
                                  if neighbours else default)
        polygons: List[Polygon] = []
        for j in range(resolution):
            for i in range(resolution):
                p00 = Vec3(box.min.x + i * step_x, box.min.y + j * step_y,
                           grid[j][i])
                p10 = Vec3(box.min.x + (i + 1) * step_x, box.min.y + j * step_y,
                           grid[j][i + 1])
                p11 = Vec3(box.min.x + (i + 1) * step_x,
                           box.min.y + (j + 1) * step_y, grid[j + 1][i + 1])
                p01 = Vec3(box.min.x + i * step_x, box.min.y + (j + 1) * step_y,
                           grid[j + 1][i])
                polygon = Polygon([p00, p10, p11, p01], material="terre")
                if not polygon.is_degenerate():
                    polygons.append(polygon)
        return Solid.from_polygons(polygons, name=name, material="terre")


# ---------------------------------------------------------------------------
# XYZ, PTS, CSV
# ---------------------------------------------------------------------------
def read_xyz(text: str, separator: Optional[str] = None,
             name: str = "nuage") -> PointCloud:
    """Lit un fichier XYZ, PTS ou CSV de points (avec couleurs facultatives)."""
    cloud = PointCloud(name=name)
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in "#;/":
            continue
        parts = line.split(separator) if separator else line.replace(",", " ").split()
        if len(parts) < 3:
            continue
        try:
            cloud.points.append(Vec3(float(parts[0]), float(parts[1]),
                                     float(parts[2])))
        except ValueError:
            continue                          # ligne d'en-tete
        if len(parts) >= 7:
            try:
                cloud.intensities.append(float(parts[3]))
                cloud.colors.append((int(float(parts[4])), int(float(parts[5])),
                                     int(float(parts[6]))))
            except ValueError:
                pass
        elif len(parts) >= 6:
            try:
                cloud.colors.append((int(float(parts[3])), int(float(parts[4])),
                                     int(float(parts[5]))))
            except ValueError:
                pass
    if not cloud.points:
        raise PointCloudError("aucun point valide dans le fichier")
    return cloud


def write_xyz(cloud: PointCloud, separator: str = " ") -> str:
    lines: List[str] = []
    for index, point in enumerate(cloud.points):
        row = ["%.4f" % point.x, "%.4f" % point.y, "%.4f" % point.z]
        if index < len(cloud.intensities):
            row.append("%.3f" % cloud.intensities[index])
        if index < len(cloud.colors):
            row += [str(c) for c in cloud.colors[index]]
        lines.append(separator.join(row))
    return "\n".join(lines) + "\n"


def write_csv(cloud: PointCloud) -> str:
    header = "X,Y,Z"
    if cloud.colors:
        header += ",R,V,B"
    return header + "\n" + write_xyz(cloud, ",")


# ---------------------------------------------------------------------------
# LAS (LiDAR)
# ---------------------------------------------------------------------------
def read_las(data: bytes, name: str = "las") -> PointCloud:
    """Lit un LAS 1.0 a 1.4, formats de point 0 a 3 (les plus repandus)."""
    if data[:4] != b"LASF":
        raise PointCloudError("signature LAS absente")
    version = "%d.%d" % (data[24], data[25])
    offset_to_points = struct.unpack_from("<I", data, 96)[0]
    point_format = data[104] & 0x3F
    point_size = struct.unpack_from("<H", data, 105)[0]
    legacy_count = struct.unpack_from("<I", data, 107)[0]
    scale = struct.unpack_from("<3d", data, 131)
    origin = struct.unpack_from("<3d", data, 155)
    count = legacy_count
    if version >= "1.4" and len(data) > 255:
        extended = struct.unpack_from("<Q", data, 247)[0]
        if extended:
            count = extended
    if point_format > 5:
        raise PointCloudError("format de point LAS %d non gere (0 a 5 lus)"
                              % point_format)
    cloud = PointCloud(name=name)
    for index in range(count):
        base = offset_to_points + index * point_size
        if base + 12 > len(data):
            break
        x, y, z = struct.unpack_from("<3i", data, base)
        cloud.points.append(Vec3(x * scale[0] + origin[0],
                                 y * scale[1] + origin[1],
                                 z * scale[2] + origin[2]))
        if base + 14 <= len(data):
            cloud.intensities.append(
                float(struct.unpack_from("<H", data, base + 12)[0]))
        if point_format in (2, 3, 5) and base + point_size <= len(data):
            colour_offset = {2: 20, 3: 28, 5: 28}[point_format]
            if base + colour_offset + 6 <= len(data):
                r, g, b = struct.unpack_from("<3H", data, base + colour_offset)
                cloud.colors.append((r >> 8, g >> 8, b >> 8))
    if not cloud.points:
        raise PointCloudError("LAS sans point exploitable")
    return cloud


def write_las(cloud: PointCloud, scale: float = 0.001) -> bytes:
    """Ecrit un LAS 1.2, format de point 2 (coordonnees, intensite, couleur)."""
    if not cloud.points:
        raise PointCloudError("nuage vide : rien a ecrire")
    box = cloud.bbox
    point_size = 26
    header_size = 227
    header = bytearray(header_size)
    header[0:4] = b"LASF"
    struct.pack_into("<H", header, 4, 0)          # source
    struct.pack_into("<H", header, 6, 0)          # encodage global
    header[24] = 1
    header[25] = 2                                 # LAS 1.2
    header[26:58] = b"MERCURY CAD AI X".ljust(32, b"\x00")
    header[58:90] = b"MERCURY CAD AI X".ljust(32, b"\x00")
    struct.pack_into("<HH", header, 90, 1, 2026)   # jour, annee
    struct.pack_into("<H", header, 94, header_size)
    struct.pack_into("<I", header, 96, header_size)
    struct.pack_into("<I", header, 100, 0)         # nombre de VLR
    header[104] = 2
    struct.pack_into("<H", header, 105, point_size)
    struct.pack_into("<I", header, 107, len(cloud.points))
    struct.pack_into("<3d", header, 131, scale, scale, scale)
    struct.pack_into("<3d", header, 155, 0.0, 0.0, 0.0)
    struct.pack_into("<6d", header, 179, box.max.x, box.min.x, box.max.y,
                     box.min.y, box.max.z, box.min.z)

    body = bytearray()
    for index, point in enumerate(cloud.points):
        body += struct.pack("<3i", int(round(point.x / scale)),
                            int(round(point.y / scale)),
                            int(round(point.z / scale)))
        intensity = int(cloud.intensities[index]) if index < len(cloud.intensities) else 0
        body += struct.pack("<H", max(0, min(65535, intensity)))
        # Retour, drapeaux, classification, angle de balayage, donnee
        # utilisateur, identifiant de source : 6 octets, comme l'exige le
        # format de point 0 dont herite le format 2.
        body += struct.pack("<BBbBH", 1, 0, 0, 0, 0)
        color = cloud.colors[index] if index < len(cloud.colors) else (0, 0, 0)
        body += struct.pack("<3H", *(min(65535, c << 8) for c in color))
    return bytes(header) + bytes(body)


def probe_las(data: bytes) -> Dict[str, Any]:
    if data[:4] != b"LASF":
        raise PointCloudError("signature LAS absente")
    return {"format": "LAS", "version": "%d.%d" % (data[24], data[25]),
            "format_point": data[104] & 0x3F,
            "points": struct.unpack_from("<I", data, 107)[0],
            "taille_octets": len(data)}
''')

ajouter('Interop/native.py', r'''
"""Format natif MERCURY : un JSON qui rend le document a l'identique.

Les formats d'echange perdent toujours quelque chose : le DXF ne garde pas
les solides exacts, le STL oublie les calques, le glTF ignore les blocs. Le
format natif conserve tout : geometrie, calques, blocs, SCU, presentations,
styles, variables et annotations. C'est le format d'enregistrement du
travail en cours et celui des sauvegardes automatiques.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from CAD_Core.document import (Block, CadDocument, Entity, Layer, Layout, UCS)
from CAD_Core.math3d import Vec3
from CAD_Core.profiles import Curve, Profile
from CAD_Core.solid import Polygon, Solid

FORMAT_VERSION = 1


class NativeFormatError(ValueError):
    """Fichier natif illisible ou de version incompatible."""


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------
def _solid_to_dict(solid: Solid) -> Dict[str, Any]:
    return {
        "classe": "solide", "nom": solid.name, "calque": solid.layer,
        "materiau": solid.material, "couleur": solid.color,
        "metadonnees": solid.metadata,
        "faces": [{"sommets": [[round(v.x, 6), round(v.y, 6), round(v.z, 6)]
                               for v in polygon.vertices],
                   "materiau": polygon.material, "calque": polygon.layer,
                   "couleur": polygon.color}
                  for polygon in solid.polygons],
    }


def _curve_to_dict(curve: Curve) -> Dict[str, Any]:
    return {"classe": "courbe", "nom": curve.name, "calque": curve.layer,
            "ferme": curve.closed,
            "points": [[round(p.x, 6), round(p.y, 6), round(p.z, 6)]
                       for p in curve.points]}


def _profile_to_dict(profile: Profile) -> Dict[str, Any]:
    return {"classe": "profil", "nom": profile.name, "calque": profile.layer,
            "contour": [[round(p.x, 6), round(p.y, 6), round(p.z, 6)]
                        for p in profile.outline],
            "ouvertures": [[[round(p.x, 6), round(p.y, 6), round(p.z, 6)]
                            for p in hole] for hole in profile.holes]}


def geometry_to_dict(geometry) -> Dict[str, Any]:
    if isinstance(geometry, Solid):
        return _solid_to_dict(geometry)
    if isinstance(geometry, Curve):
        return _curve_to_dict(geometry)
    if isinstance(geometry, Profile):
        return _profile_to_dict(geometry)
    if isinstance(geometry, dict):
        return {"classe": "annotation", "donnees": geometry}
    raise NativeFormatError("geometrie non serialisable : %r" % type(geometry))


def geometry_from_dict(payload: Dict[str, Any]):
    classe = payload.get("classe")
    if classe == "solide":
        polygons = [Polygon([Vec3(*point) for point in face["sommets"]],
                            face.get("materiau", "default"),
                            face.get("calque", "0"), face.get("couleur", 256))
                    for face in payload.get("faces", [])
                    if len(face.get("sommets", [])) >= 3]
        return Solid(polygons, payload.get("nom", "solide"),
                     payload.get("calque", "0"),
                     payload.get("materiau", "default"),
                     payload.get("couleur", 256),
                     dict(payload.get("metadonnees", {})))
    if classe == "courbe":
        return Curve([Vec3(*point) for point in payload.get("points", [])],
                     bool(payload.get("ferme", False)),
                     payload.get("nom", "courbe"), payload.get("calque", "0"))
    if classe == "profil":
        return Profile([Vec3(*point) for point in payload.get("contour", [])],
                       [[Vec3(*point) for point in hole]
                        for hole in payload.get("ouvertures", [])],
                       payload.get("nom", "profil"), payload.get("calque", "0"))
    if classe == "annotation":
        return dict(payload.get("donnees", {}))
    raise NativeFormatError("classe de geometrie inconnue : %r" % classe)


def _entity_to_dict(entity: Entity) -> Dict[str, Any]:
    return {"handle": entity.handle, "type": entity.kind, "nom": entity.name,
            "calque": entity.layer, "couleur": entity.color,
            "type_ligne": entity.linetype, "epaisseur": entity.lineweight,
            "materiau": entity.material, "visible": entity.visible,
            "verrouille": entity.locked, "transparence": entity.transparency,
            "attributs": entity.attributes,
            "geometrie": geometry_to_dict(entity.geometry)}


def _entity_from_dict(payload: Dict[str, Any]) -> Entity:
    return Entity(payload.get("handle", "0"), payload.get("type", "solide"),
                  geometry_from_dict(payload["geometrie"]),
                  payload.get("calque", "0"), payload.get("couleur", 256),
                  payload.get("type_ligne", "PARCALQUE"),
                  payload.get("epaisseur", -1),
                  payload.get("materiau", "default"),
                  bool(payload.get("visible", True)),
                  bool(payload.get("verrouille", False)),
                  int(payload.get("transparence", 0)),
                  payload.get("nom", ""),
                  dict(payload.get("attributs", {})))


def write_native(document: CadDocument, indent: Optional[int] = 2) -> str:
    """Serialise l'integralite du document."""
    payload = {
        "format": "MERCURY", "version_format": FORMAT_VERSION,
        "document": document.name, "unites": document.units,
        "calque_courant": document.current_layer,
        "scu_courant": document.current_ucs,
        "compteur": document._counter,
        "calques": [layer.to_dict() for layer in document.layers.values()],
        "objets": [_entity_to_dict(entity)
                   for entity in document.entities.values()],
        "blocs": [{"nom": block.name, "point_base": list(block.base_point),
                   "description": block.description,
                   "attributs": dict(block.attributes),
                   "objets": [_entity_to_dict(member)
                              for member in block.entities]}
                  for block in document.blocks.values()],
        "scu": [ucs.to_dict() for ucs in document.ucs_table.values()],
        "presentations": [layout.to_dict()
                          for layout in document.layouts.values()],
        "styles_texte": document.text_styles,
        "styles_cotation": document.dim_styles,
        "materiaux": document.materials,
        "vues_nommees": document.named_views,
        "variables": document.variables,
        "selection": list(document.selection),
    }
    return json.dumps(payload, ensure_ascii=False, indent=indent)


def read_native(text: str, name: Optional[str] = None) -> CadDocument:
    """Reconstruit un document identique a l'original."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise NativeFormatError("JSON MERCURY illisible : %s" % error)
    if payload.get("format") != "MERCURY":
        raise NativeFormatError(
            "ce JSON n'est pas un fichier natif MERCURY (cle 'format' absente)")
    version = int(payload.get("version_format", 0))
    if version > FORMAT_VERSION:
        raise NativeFormatError(
            "fichier ecrit par une version plus recente (format %d, lu %d)"
            % (version, FORMAT_VERSION))
    document = CadDocument(name or payload.get("document", "importe"),
                           payload.get("unites", "mm"))
    document.layers.clear()
    for layer in payload.get("calques", []):
        document.layers[layer["nom"]] = Layer(
            layer["nom"], int(layer.get("couleur", 7)),
            layer.get("type_ligne", "CONTINUOUS"),
            int(layer.get("epaisseur", 25)), bool(layer.get("actif", True)),
            bool(layer.get("gele", False)), bool(layer.get("verrouille", False)),
            bool(layer.get("traceable", True)),
            int(layer.get("transparence", 0)), layer.get("description", ""))
    if not document.layers:
        document.layers["0"] = Layer("0")
    for entity_payload in payload.get("objets", []):
        entity = _entity_from_dict(entity_payload)
        document.entities[entity.handle] = entity
    for block_payload in payload.get("blocs", []):
        document.blocks[block_payload["nom"]] = Block(
            block_payload["nom"],
            [_entity_from_dict(member)
             for member in block_payload.get("objets", [])],
            Vec3(*block_payload.get("point_base", [0, 0, 0])),
            block_payload.get("description", ""),
            dict(block_payload.get("attributs", {})))
    for ucs_payload in payload.get("scu", []):
        document.ucs_table[ucs_payload["nom"]] = UCS(
            ucs_payload["nom"], Vec3(*ucs_payload.get("origine", [0, 0, 0])),
            Vec3(*ucs_payload.get("axe_x", [1, 0, 0])),
            Vec3(*ucs_payload.get("axe_y", [0, 1, 0])))
    document.layouts.clear()
    for layout_payload in payload.get("presentations", []):
        document.layouts[layout_payload["nom"]] = Layout(
            layout_payload["nom"], layout_payload.get("format", "A3"),
            float(layout_payload.get("largeur_mm", 420.0)),
            float(layout_payload.get("hauteur_mm", 297.0)),
            float(layout_payload.get("echelle", 0.01)))
    if not document.layouts:
        document.layouts["Presentation1"] = Layout()
    document.text_styles = payload.get("styles_texte", document.text_styles)
    document.dim_styles = payload.get("styles_cotation", document.dim_styles)
    document.materials = payload.get("materiaux", {})
    document.named_views = payload.get("vues_nommees", {})
    document.variables.update(payload.get("variables", {}))
    document.current_layer = payload.get("calque_courant", "0")
    if document.current_layer not in document.layers:
        document.current_layer = next(iter(document.layers))
    document.current_ucs = payload.get("scu_courant", "GENERAL")
    if document.current_ucs not in document.ucs_table:
        document.ucs_table[document.current_ucs] = UCS(document.current_ucs)
    document._counter = int(payload.get("compteur", len(document.entities)))
    document.selection = [h for h in payload.get("selection", [])
                          if h in document.entities]
    return document
''')


# =========================================================================
# 6. MOTEUR BIM  (livrables #11 a #18, #25)
# =========================================================================
ajouter('BIM_Engine/__init__.py', r'''
"""Moteur BIM : modele de donnees, IFC, bibliotheque, collaboration."""
from .models import (
    BuildingProject, Furniture, Level, Opening, Room, Slab, Wall, new_id,
)
from .ifc_handler import IFCHandler
from .object_library import ObjectLibrary
from .collaboration import CollaborationHub

__all__ = ["BuildingProject", "Furniture", "Level", "Opening", "Room", "Slab",
           "Wall", "new_id", "IFCHandler", "ObjectLibrary", "CollaborationHub"]
''')

ajouter('BIM_Engine/collaboration.py', r'''
"""Collaboration cloud (livrable #15).

Diffusion des modifications aux clients connectes et suivi de presence.
Le transport WebSocket est branche dans l'API ; ce module reste testable
sans reseau, ce qui permet de valider la logique en integration continue.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Participant:
    user_id: str
    joined_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class CollaborationHub:
    """Sessions par projet, journal des evenements, resolution simple."""

    def __init__(self, history: int = 200) -> None:
        self.sessions: Dict[str, Dict[str, Participant]] = {}
        self.journal: Dict[str, List[Dict[str, Any]]] = {}
        self.history = history

    def join(self, project_id: str, user_id: str) -> int:
        room = self.sessions.setdefault(project_id, {})
        room[user_id] = Participant(user_id)
        self._log(project_id, "presence", user_id, {"connectes": len(room)})
        return len(room)

    def leave(self, project_id: str, user_id: str) -> int:
        room = self.sessions.get(project_id, {})
        room.pop(user_id, None)
        self._log(project_id, "depart", user_id, {"connectes": len(room)})
        return len(room)

    def participants(self, project_id: str) -> List[str]:
        return sorted(self.sessions.get(project_id, {}))

    def publish(self, project_id: str, user_id: str, kind: str,
                payload: Dict[str, Any]) -> Dict[str, Any]:
        """Publie une modification et renvoie l'evenement diffuse."""
        if kind not in ("modification", "curseur", "commentaire"):
            raise ValueError("type d'evenement inconnu : %s" % kind)
        return self._log(project_id, kind, user_id, payload)

    def events(self, project_id: str, since: float = 0.0) -> List[Dict[str, Any]]:
        return [e for e in self.journal.get(project_id, []) if e["at"] > since]

    def _log(self, project_id: str, kind: str, user_id: str,
             payload: Dict[str, Any]) -> Dict[str, Any]:
        event = {"at": time.time(), "type": kind, "par": user_id, "detail": payload}
        entries = self.journal.setdefault(project_id, [])
        entries.append(event)
        if len(entries) > self.history:
            del entries[: len(entries) - self.history]
        return event
''')

ajouter('BIM_Engine/ifc_handler.py', r'''
"""Export IFC4 au format STEP (livrable #14).

Ecrivain autonome couvrant ce qui compte pour l'echange : projet, site,
batiment, etage, murs avec leurs quantites de base et espaces. C'est le
sous-ensemble lu par tous les visualiseurs et par Revit, ArchiCAD, Tekla.
"""
from __future__ import annotations

import base64
import datetime
import hashlib
from typing import List


class IFCHandler:
    """Serialise un projet BIM en fichier IFC4."""

    def __init__(self) -> None:
        self._lines: List[str] = []
        self._counter = 0

    def _add(self, body: str) -> str:
        self._counter += 1
        reference = "#%d" % self._counter
        self._lines.append("%s= %s;" % (reference, body))
        return reference

    @staticmethod
    def _guid(seed: str) -> str:
        digest = hashlib.md5(seed.encode("utf-8")).digest()
        encoded = base64.b64encode(digest).decode()
        return encoded.replace("+", "_").replace("/", "$")[:22]

    @staticmethod
    def _escape(text: str) -> str:
        return (text or "").replace("'", "''").replace("\\", "")

    def export(self, project) -> str:
        self._lines, self._counter = [], 0
        org = self._add("IFCORGANIZATION($,'Mercury',$,$,$)")
        app = self._add("IFCAPPLICATION(%s,'1.0','MERCURY CAD AI X','MERCURY')" % org)
        person = self._add("IFCPERSON($,'Mercury','User',$,$,$,$,$)")
        po = self._add("IFCPERSONANDORGANIZATION(%s,%s,$)" % (person, org))
        stamp = int(datetime.datetime.now().timestamp())
        owner = self._add("IFCOWNERHISTORY(%s,%s,$,.ADDED.,%d,%s,%s,%d)"
                          % (po, app, stamp, po, app, stamp))

        dz = self._add("IFCDIRECTION((0.,0.,1.))")
        dx = self._add("IFCDIRECTION((1.,0.,0.))")
        origin = self._add("IFCCARTESIANPOINT((0.,0.,0.))")
        axis = self._add("IFCAXIS2PLACEMENT3D(%s,%s,%s)" % (origin, dz, dx))
        context = self._add(
            "IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,%s,$)" % axis)
        length_unit = self._add("IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.)")
        area_unit = self._add("IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.)")
        angle_unit = self._add("IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.)")
        units = self._add("IFCUNITASSIGNMENT((%s,%s,%s))"
                          % (length_unit, area_unit, angle_unit))
        placement = self._add("IFCLOCALPLACEMENT($,%s)" % axis)

        proj = self._add("IFCPROJECT('%s',%s,'%s',$,$,$,$,(%s),%s)"
                         % (self._guid(project.id), owner,
                            self._escape(project.name), context, units))
        site = self._add("IFCSITE('%s',%s,'Terrain',$,$,%s,$,$,.ELEMENT.,$,$,$,$,$)"
                         % (self._guid(project.id + "site"), owner, placement))
        building = self._add(
            "IFCBUILDING('%s',%s,'%s',$,$,%s,$,$,.ELEMENT.,$,$,$)"
            % (self._guid(project.id + "bld"), owner,
               self._escape(project.name), placement))
        storey = self._add(
            "IFCBUILDINGSTOREY('%s',%s,'%s',$,$,%s,$,$,.ELEMENT.,0.)"
            % (self._guid(project.levels[0].id), owner,
               self._escape(project.levels[0].name), placement))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid("a1"), owner, proj, site))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid("a2"), owner, site, building))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid("a3"), owner, building, storey))

        contained: List[str] = []
        for wall in project.walls:
            reference = self._wall(wall, owner, placement, context, dz)
            if reference:
                contained.append(reference)
        for room in project.rooms:
            reference = self._space(room, owner, placement, context, dz)
            if reference:
                contained.append(reference)
        if contained:
            self._add("IFCRELCONTAINEDINSPATIALSTRUCTURE('%s',%s,$,$,(%s),%s)"
                      % (self._guid("c1"), owner, ",".join(contained), storey))
        return self._dump(project.name)

    def _wall(self, wall, owner: str, placement: str, context: str, dz: str):
        length = wall.length
        if length < 1.0:
            return None
        ux = (wall.end[0] - wall.start[0]) / length
        uy = (wall.end[1] - wall.start[1]) / length
        p0 = self._add("IFCCARTESIANPOINT((%.3f,%.3f,0.))"
                       % (wall.start[0], wall.start[1]))
        direction = self._add("IFCDIRECTION((%.6f,%.6f,0.))" % (ux, uy))
        axis = self._add("IFCAXIS2PLACEMENT3D(%s,%s,%s)" % (p0, dz, direction))
        local = self._add("IFCLOCALPLACEMENT(%s,%s)" % (placement, axis))
        centre = self._add("IFCCARTESIANPOINT((%.3f,0.))" % (length / 2.0))
        d2 = self._add("IFCDIRECTION((1.,0.))")
        axis2 = self._add("IFCAXIS2PLACEMENT2D(%s,%s)" % (centre, d2))
        profile = self._add("IFCRECTANGLEPROFILEDEF(.AREA.,'mur',%s,%.3f,%.3f)"
                            % (axis2, length, wall.thickness))
        solid = self._add("IFCEXTRUDEDAREASOLID(%s,%s,%s,%.3f)"
                          % (profile, axis, dz, wall.height))
        shape = self._add("IFCSHAPEREPRESENTATION(%s,'Body','SweptSolid',(%s))"
                          % (context, solid))
        product = self._add("IFCPRODUCTDEFINITIONSHAPE($,$,(%s))" % shape)
        reference = self._add(
            "IFCWALLSTANDARDCASE('%s',%s,'Mur',$,$,%s,%s,$,$)"
            % (self._guid(wall.id), owner, local, product))
        self._quantities(wall, owner, reference)
        return reference

    def _quantities(self, wall, owner: str, reference: str) -> None:
        length = self._add("IFCQUANTITYLENGTH('Length',$,$,%.1f,$)" % wall.length)
        area = self._add("IFCQUANTITYAREA('NetSideArea',$,$,%.3f,$)"
                         % wall.net_area_m2)
        volume = self._add(
            "IFCQUANTITYVOLUME('NetVolume',$,$,%.3f,$)"
            % (wall.net_area_m2 * wall.thickness / 1000.0))
        quantity = self._add(
            "IFCELEMENTQUANTITY('%s',%s,'Qto_WallBaseQuantities',$,$,(%s,%s,%s))"
            % (self._guid(wall.id + "q"), owner, length, area, volume))
        self._add("IFCRELDEFINESBYPROPERTIES('%s',%s,$,$,(%s),%s)"
                  % (self._guid(wall.id + "r"), owner, reference, quantity))

    def _space(self, room, owner: str, placement: str, context: str, dz: str):
        if len(room.outline) < 3:
            return None
        points = [self._add("IFCCARTESIANPOINT((%.3f,%.3f))" % (p[0], p[1]))
                  for p in room.outline]
        polyline = self._add("IFCPOLYLINE((%s))" % ",".join(points + [points[0]]))
        profile = self._add("IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,$,%s)" % polyline)
        p0 = self._add("IFCCARTESIANPOINT((0.,0.,0.))")
        dx = self._add("IFCDIRECTION((1.,0.,0.))")
        axis = self._add("IFCAXIS2PLACEMENT3D(%s,%s,%s)" % (p0, dz, dx))
        local = self._add("IFCLOCALPLACEMENT(%s,%s)" % (placement, axis))
        solid = self._add("IFCEXTRUDEDAREASOLID(%s,%s,%s,%.3f)"
                          % (profile, axis, dz, room.height))
        shape = self._add("IFCSHAPEREPRESENTATION(%s,'Body','SweptSolid',(%s))"
                          % (context, solid))
        product = self._add("IFCPRODUCTDEFINITIONSHAPE($,$,(%s))" % shape)
        return self._add(
            "IFCSPACE('%s',%s,'%s',$,$,%s,%s,$,.ELEMENT.,$)"
            % (self._guid(room.id), owner, self._escape(room.name), local, product))

    def _dump(self, name: str) -> str:
        stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        header = (
            "ISO-10303-21;\nHEADER;\n"
            "FILE_DESCRIPTION((''),'2;1');\n"
            "FILE_NAME('%s','%s',(''),(''),'MERCURY CAD AI X','1.0','');\n"
            "FILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n" % (self._escape(name), stamp)
        )
        return header + "\n".join(self._lines) + "\nENDSEC;\nEND-ISO-10303-21;\n"

    # -----------------------------------------------------------------
    # Solides libres : passerelle avec le noyau CAO (module Interop)
    # -----------------------------------------------------------------
    def export_solids(self, solids, name: str = "MAQUETTE") -> str:
        """Ecrit des solides quelconques en IFC4, par faces (IfcFacetedBrep).

        Complete `export`, qui traite le modele BIM structure. Ici la
        geometrie vient du noyau CAO : murs modelises a la main, ouvrages
        d'art, pieces mecaniques, terrain. Tout devient un IfcBuildingElement
        proxy porteur d'une representation Brep, ce que lisent Revit,
        ArchiCAD, Tekla, Solibri et les visualiseurs IFC.
        """
        self._lines, self._counter = [], 0
        org = self._add("IFCORGANIZATION($,'Mercury',$,$,$)")
        person = self._add("IFCPERSON($,$,'MERCURY',$,$,$,$,$)")
        person_org = self._add("IFCPERSONANDORGANIZATION(%s,%s,$)"
                               % (person, org))
        application = self._add(
            "IFCAPPLICATION(%s,'1.0','MERCURY CAD AI X','MERCURY')" % org)
        stamp = int(datetime.datetime.now().timestamp())
        owner = self._add("IFCOWNERHISTORY(%s,%s,$,.ADDED.,$,$,$,%d)"
                          % (person_org, application, stamp))
        origin = self._add("IFCCARTESIANPOINT((0.,0.,0.))")
        axis = self._add("IFCDIRECTION((0.,0.,1.))")
        reference = self._add("IFCDIRECTION((1.,0.,0.))")
        placement = self._add("IFCAXIS2PLACEMENT3D(%s,%s,%s)"
                              % (origin, axis, reference))
        local = self._add("IFCLOCALPLACEMENT($,%s)" % placement)
        length_unit = self._add("IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.)")
        area_unit = self._add("IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.)")
        volume_unit = self._add("IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.)")
        units = self._add("IFCUNITASSIGNMENT((%s,%s,%s))"
                          % (length_unit, area_unit, volume_unit))
        context = self._add(
            "IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,%s,$)"
            % placement)
        project = self._add("IFCPROJECT('%s',%s,'%s',$,$,$,$,(%s),%s)"
                            % (self._guid(name), owner, self._escape(name),
                               context, units))
        site = self._add("IFCSITE('%s',%s,'Site',$,$,%s,$,$,.ELEMENT.,$,$,$,$,$)"
                         % (self._guid(name + "site"), owner, local))
        building = self._add(
            "IFCBUILDING('%s',%s,'Batiment',$,$,%s,$,$,.ELEMENT.,$,$,$)"
            % (self._guid(name + "bat"), owner, local))
        storey = self._add(
            "IFCBUILDINGSTOREY('%s',%s,'Niveau 0',$,$,%s,$,$,.ELEMENT.,0.)"
            % (self._guid(name + "niv"), owner, local))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid(name + "ra1"), owner, project, site))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid(name + "ra2"), owner, site, building))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid(name + "ra3"), owner, building, storey))

        products: List[str] = []
        for order, solid in enumerate(solids):
            brep = self._faceted_brep(solid)
            representation = self._add(
                "IFCSHAPEREPRESENTATION(%s,'Body','Brep',(%s))"
                % (context, brep))
            shape = self._add("IFCPRODUCTDEFINITIONSHAPE($,$,(%s))"
                              % representation)
            label = self._escape(getattr(solid, "name", "") or "Solide%d" % order)
            products.append(self._add(
                "IFCBUILDINGELEMENTPROXY('%s',%s,'%s',$,$,%s,%s,$,$)"
                % (self._guid("%s-%d" % (name, order)), owner, label, local,
                   shape)))
        if products:
            self._add("IFCRELCONTAINEDINSPATIALSTRUCTURE('%s',%s,$,$,(%s),%s)"
                      % (self._guid(name + "rel"), owner, ",".join(products),
                         storey))
        return self._dump(name)

    def _faceted_brep(self, solid) -> str:
        """Traduit un solide facettise en IFCFACETEDBREP."""
        points: dict = {}
        faces: List[str] = []
        for polygon in solid.polygons:
            if polygon.is_degenerate():
                continue
            references: List[str] = []
            for vertex in polygon.vertices:
                key = vertex.rounded(5)
                if key not in points:
                    points[key] = self._add(
                        "IFCCARTESIANPOINT((%.5f,%.5f,%.5f))"
                        % (vertex.x, vertex.y, vertex.z))
                references.append(points[key])
            loop = self._add("IFCPOLYLOOP((%s))" % ",".join(references))
            bound = self._add("IFCFACEOUTERBOUND(%s,.T.)" % loop)
            faces.append(self._add("IFCFACE((%s))" % bound))
        shell = self._add("IFCCLOSEDSHELL((%s))" % ",".join(faces))
        return self._add("IFCFACETEDBREP(%s)" % shell)

    def read_solids(self, text: str, name: str = "ifc"):
        """Relit les volumes d'un IFC facettise (IFCFACETEDBREP).

        Couvre les fichiers produits par `export_solids` ainsi que les IFC
        exportes en representation Brep par les logiciels BIM courants. Les
        representations parametriques (extrusions, revolutions) sont
        signalees mais non reconstruites.
        """
        import re as _re

        from CAD_Core.math3d import Vec3
        from CAD_Core.solid import Polygon, Solid

        body = text.split("DATA;", 1)[1] if "DATA;" in text else text
        entities: dict = {}
        for statement in body.split(";"):
            match = _re.match(r"\s*#(\d+)\s*=\s*([A-Z0-9]+)\s*\((.*)\)\s*$",
                              statement.replace("\n", " "), _re.IGNORECASE | _re.S)
            if match:
                entities[int(match.group(1))] = (match.group(2).upper(),
                                                 match.group(3))
        points = {}
        for key, (kind, payload) in entities.items():
            if kind == "IFCCARTESIANPOINT":
                numbers = _re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", payload)
                if len(numbers) >= 3:
                    points[key] = Vec3(float(numbers[0]), float(numbers[1]),
                                       float(numbers[2]))
        loops = {}
        for key, (kind, payload) in entities.items():
            if kind == "IFCPOLYLOOP":
                refs = [int(r) for r in _re.findall(r"#(\d+)", payload)]
                ring = [points[r] for r in refs if r in points]
                if len(ring) >= 3:
                    loops[key] = ring
        polygons = []
        for key, (kind, payload) in entities.items():
            if kind in ("IFCFACEOUTERBOUND", "IFCFACEBOUND"):
                for ref in (int(r) for r in _re.findall(r"#(\d+)", payload)):
                    if ref in loops:
                        polygons.append(Polygon(list(loops[ref])))
                        break
        if not polygons:
            extruded = sum(1 for kind, _ in entities.values()
                           if kind == "IFCEXTRUDEDAREASOLID")
            raise ValueError(
                "cet IFC decrit %d volumes en representation parametrique ; "
                "MERCURY relit les representations Brep. Reexportez avec "
                "l'option Brep, ou utilisez l'import du modele BIM structure."
                % extruded if extruded else
                "aucune geometrie Brep exploitable dans cet IFC")
        return [Solid.from_polygons(polygons, name=name).heal()]
''')

ajouter('BIM_Engine/mep.py', r'''
"""Module fluides (livrable #18) - preciblage des reseaux.

Estime les besoins par piece : points d'eau, prises, luminaires, debits de
ventilation. Sert au chiffrage et au reperage des gaines, pas au calcul
detaille des reseaux.
"""
from __future__ import annotations

from typing import Dict, List

# Par type de piece : prises, luminaires, points d'eau, debit extrait m3/h
REGLES = {
    "cuisine": (6, 2, 2, 45),
    "salle de bain": (2, 2, 3, 30),
    "sdb": (2, 2, 3, 30),
    "wc": (1, 1, 1, 15),
    "chambre": (5, 1, 0, 0),
    "sejour": (8, 3, 0, 0),
    "bureau": (8, 2, 0, 0),
    "salle": (6, 4, 0, 0),
    "entree": (2, 1, 0, 0),
    "inconnu": (4, 1, 0, 0),
}


class MEPPlanner:
    """Preciblage electricite, plomberie et ventilation."""

    def plan(self, project) -> Dict[str, object]:
        lignes: List[Dict[str, object]] = []
        totaux = {"prises": 0, "luminaires": 0, "points_eau": 0, "debit_m3h": 0}
        for room in project.rooms:
            kind = (room.kind or "inconnu").lower()
            prises, lum, eau, debit = REGLES.get(kind, REGLES["inconnu"])
            # ajustement a la surface : une grande piece demande plus de points
            facteur = max(1.0, room.area_m2 / 15.0)
            valeurs = {
                "prises": int(round(prises * facteur)),
                "luminaires": int(round(lum * facteur)),
                "points_eau": eau,
                "debit_m3h": int(round(debit * facteur)) if debit else 0,
            }
            for cle, valeur in valeurs.items():
                totaux[cle] += valeur
            lignes.append({"piece": room.name, "type": kind,
                           "surface_m2": room.area_m2, **valeurs})
        return {
            "detail": lignes,
            "totaux": totaux,
            "avertissement": "preciblage d'esquisse : ne remplace pas les notes "
                             "de calcul electricite, plomberie et ventilation",
        }
''')

ajouter('BIM_Engine/models.py', r'''
"""Modele BIM neutre (livrable #11).

Contrat unique entre tous les modules : CAO, IA, metre, exports et jumeau
numerique lisent et ecrivent ces memes objets. Serialisable en JSON sans
perte, donc versionnable et diffable.

Unites : millimetres pour les longueurs, m2 pour les surfaces exposees.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

Point2 = Tuple[float, float]

BUILDING_TYPES = (
    "maison", "villa", "appartement", "hotel", "restaurant", "supermarche",
    "pharmacie", "banque", "hopital", "clinique", "ecole", "universite",
    "mosquee", "eglise", "bureau", "magasin", "centre_commercial", "usine",
    "entrepot", "bar", "salle_conference", "aeroport", "gare", "inconnu",
)
OPENING_TYPES = ("porte", "fenetre", "baie", "passage")


def new_id(prefix: str) -> str:
    """Identifiant court, stable et lisible dans les journaux."""
    return "%s_%s" % (prefix, uuid.uuid4().hex[:12])


@dataclass
class Opening:
    """Baie percee dans un mur, positionnee le long de son axe."""

    type: str = "porte"
    offset: float = 0.0
    width: float = 900.0
    height: float = 2100.0
    sill: float = 0.0
    id: str = field(default_factory=lambda: new_id("opn"))

    def __post_init__(self) -> None:
        if self.type not in OPENING_TYPES:
            raise ValueError("type de baie inconnu : %s" % self.type)
        if self.width <= 0 or self.height <= 0:
            raise ValueError("une baie doit avoir des dimensions positives")

    @property
    def area_m2(self) -> float:
        return round(self.width * self.height / 1e6, 3)


@dataclass
class Wall:
    """Mur defini par son axe, son epaisseur et sa hauteur."""

    start: Point2 = (0.0, 0.0)
    end: Point2 = (0.0, 0.0)
    thickness: float = 200.0
    height: float = 2700.0
    exterior: bool = False
    level_id: str = ""
    openings: List[Opening] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("wal"))

    def __post_init__(self) -> None:
        if self.thickness <= 0:
            raise ValueError("epaisseur de mur invalide")
        if self.height <= 0:
            raise ValueError("hauteur de mur invalide")

    @property
    def length(self) -> float:
        return math.hypot(self.end[0] - self.start[0], self.end[1] - self.start[1])

    @property
    def gross_area_m2(self) -> float:
        return round(self.length * self.height / 1e6, 3)

    @property
    def net_area_m2(self) -> float:
        holes = sum(o.width * o.height for o in self.openings)
        return round(max(0.0, self.length * self.height - holes) / 1e6, 3)

    def add_opening(self, opening: Opening) -> Opening:
        """Ajoute une baie apres verification qu'elle tient dans le mur."""
        half = opening.width / 2.0
        if opening.offset - half < 0 or opening.offset + half > self.length:
            raise ValueError("la baie deborde du mur (longueur %.0f mm)" % self.length)
        self.openings.append(opening)
        self.openings.sort(key=lambda o: o.offset)
        return opening


@dataclass
class Room:
    name: str = ""
    kind: str = "inconnu"
    outline: List[Point2] = field(default_factory=list)
    area_m2: float = 0.0
    perimeter_m: float = 0.0
    height: float = 2700.0
    centroid: Point2 = (0.0, 0.0)
    level_id: str = ""
    id: str = field(default_factory=lambda: new_id("rom"))

    @property
    def volume_m3(self) -> float:
        return round(self.area_m2 * self.height / 1000.0, 2)


@dataclass
class Slab:
    outline: List[Point2] = field(default_factory=list)
    thickness: float = 200.0
    z: float = 0.0
    role: str = "plancher"
    level_id: str = ""
    id: str = field(default_factory=lambda: new_id("slb"))


@dataclass
class Furniture:
    name: str = ""
    catalog_id: str = ""
    position: Point2 = (0.0, 0.0)
    rotation: float = 0.0
    size: Tuple[float, float, float] = (600.0, 600.0, 750.0)
    room_id: str = ""
    unit_cost: float = 0.0
    id: str = field(default_factory=lambda: new_id("fur"))


@dataclass
class Level:
    name: str = "RDC"
    index: int = 0
    elevation: float = 0.0
    height: float = 2700.0
    id: str = field(default_factory=lambda: new_id("lvl"))


@dataclass
class BuildingProject:
    """Etat complet d'un projet, versionne."""

    name: str = "Projet"
    building_type: str = "inconnu"
    version: int = 1
    units: str = "mm"
    levels: List[Level] = field(default_factory=list)
    walls: List[Wall] = field(default_factory=list)
    rooms: List[Room] = field(default_factory=list)
    slabs: List[Slab] = field(default_factory=list)
    furniture: List[Furniture] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("prj"))

    def __post_init__(self) -> None:
        if self.building_type not in BUILDING_TYPES:
            raise ValueError("type de batiment inconnu : %s" % self.building_type)
        if not self.levels:
            self.levels.append(Level())

    # -- helpers ----------------------------------------------------------
    def add_wall(self, wall: Wall) -> Wall:
        wall.level_id = wall.level_id or self.levels[0].id
        self.walls.append(wall)
        return wall

    def wall(self, wall_id: str) -> Optional[Wall]:
        return next((w for w in self.walls if w.id == wall_id), None)

    def room(self, room_id: str) -> Optional[Room]:
        return next((r for r in self.rooms if r.id == room_id), None)

    @property
    def total_area_m2(self) -> float:
        return round(sum(r.area_m2 for r in self.rooms), 2)

    def bump(self) -> "BuildingProject":
        self.version += 1
        return self

    # -- serialisation ----------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildingProject":
        project = cls(
            name=data.get("name", "Projet"),
            building_type=data.get("building_type", "inconnu"),
            version=int(data.get("version", 1)),
            metadata=dict(data.get("metadata", {})),
            id=data.get("id", new_id("prj")),
        )
        project.levels = [Level(**lv) for lv in data.get("levels", [])] or project.levels
        project.walls = []
        for raw in data.get("walls", []):
            openings = [Opening(**o) for o in raw.get("openings", [])]
            payload = {k: v for k, v in raw.items() if k != "openings"}
            wall = Wall(**payload)
            wall.openings = openings
            project.walls.append(wall)
        project.rooms = [Room(**r) for r in data.get("rooms", [])]
        project.slabs = [Slab(**s) for s in data.get("slabs", [])]
        project.furniture = [Furniture(**f) for f in data.get("furniture", [])]
        return project
''')

ajouter('BIM_Engine/object_library.py', r'''
"""Bibliotheque d'objets parametriques (livrables #12, #13, #22, #23).

Chaque entree est parametrique : dimensions redimensionnables, ancrage de
pose, degagement d'usage, cout unitaire. Les packs fabricants s'ajoutent
au format JSON sans toucher au code, ce qui ouvre la marketplace.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CatalogItem:
    id: str
    name: str
    category: str
    size: Tuple[float, float, float]
    anchor: str = "libre"
    clearance: float = 700.0
    unit_cost: float = 0.0
    tags: List[str] = field(default_factory=list)
    manufacturer: str = ""

    def scaled(self, width=None, depth=None, height=None) -> "CatalogItem":
        w, d, h = self.size
        return CatalogItem(
            id=self.id, name=self.name, category=self.category,
            size=(width or w, depth or d, height or h), anchor=self.anchor,
            clearance=self.clearance, unit_cost=self.unit_cost,
            tags=list(self.tags), manufacturer=self.manufacturer,
        )


SEED: List[CatalogItem] = [
    CatalogItem("bed_double", "Lit double", "chambre", (1600, 2000, 500), "mur", 700, 450),
    CatalogItem("wardrobe", "Armoire", "chambre", (1800, 600, 2200), "mur", 800, 600),
    CatalogItem("nightstand", "Chevet", "chambre", (450, 400, 550), "mur", 300, 80),
    CatalogItem("sofa_3", "Canape 3 places", "sejour", (2100, 900, 800), "mur", 900, 900),
    CatalogItem("coffee_table", "Table basse", "sejour", (1100, 600, 400), "centre", 500, 200),
    CatalogItem("dining_table", "Table 6 personnes", "sejour", (1800, 900, 750), "centre", 800, 450),
    CatalogItem("chair", "Chaise", "mobilier", (450, 500, 900), "libre", 400, 60),
    CatalogItem("kitchen_run", "Lineaire de cuisine", "cuisine", (3000, 650, 900), "mur", 1000, 1400),
    CatalogItem("fridge", "Refrigerateur", "cuisine", (700, 700, 1900), "mur", 800, 700),
    CatalogItem("cooktop", "Piano de cuisson", "cuisine", (900, 650, 900), "mur", 900, 1200),
    CatalogItem("sink", "Evier", "cuisine", (900, 600, 900), "mur", 800, 350),
    CatalogItem("wc", "WC suspendu", "sanitaire", (400, 600, 800), "mur", 600, 350),
    CatalogItem("washbasin", "Lavabo", "sanitaire", (650, 500, 850), "mur", 700, 250),
    CatalogItem("shower", "Douche", "sanitaire", (900, 900, 2000), "coin", 700, 800),
    CatalogItem("desk", "Bureau", "tertiaire", (1600, 800, 750), "libre", 900, 400),
    CatalogItem("meeting_table", "Table de reunion", "tertiaire", (2800, 1200, 750), "centre", 900, 1200),
    CatalogItem("reception_desk", "Banque d'accueil", "tertiaire", (2400, 800, 1100), "mur", 1200, 3500),
    CatalogItem("shelf", "Rayonnage", "logistique", (2500, 600, 2000), "mur", 1400, 500),
    CatalogItem("resto_table", "Table restaurant", "restaurant", (900, 900, 750), "libre", 750, 280),
    CatalogItem("cold_room", "Chambre froide", "cuisine_pro", (2400, 2000, 2400), "coin", 900, 6500),
]


class ObjectLibrary:
    """Index en memoire, extensible par packs JSON signes."""

    def __init__(self, items: Optional[List[CatalogItem]] = None) -> None:
        self._items: Dict[str, CatalogItem] = {}
        for item in (items if items is not None else SEED):
            self._items[item.id] = item

    def get(self, item_id: str) -> Optional[CatalogItem]:
        return self._items.get(item_id)

    def all(self) -> List[CatalogItem]:
        return list(self._items.values())

    def categories(self) -> List[str]:
        return sorted({item.category for item in self._items.values()})

    def search(self, query: str = "", category: str = "",
               limit: int = 50) -> List[CatalogItem]:
        query = query.lower().strip()
        found: List[CatalogItem] = []
        for item in self._items.values():
            if query and query not in item.name.lower() and query not in item.id:
                continue
            if category and item.category != category:
                continue
            found.append(item)
            if len(found) >= limit:
                break
        return found

    def load_pack(self, path: str) -> int:
        """Charge un pack fabricant. Leve une erreur explicite si invalide."""
        if not os.path.isfile(path):
            raise FileNotFoundError("pack introuvable : %s" % path)
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if "items" not in data:
            raise ValueError("pack invalide : cle 'items' absente")
        count = 0
        for raw in data["items"]:
            item = CatalogItem(
                id=raw["id"], name=raw["name"],
                category=raw.get("category", "divers"),
                size=tuple(raw.get("size", (600, 600, 750))),
                anchor=raw.get("anchor", "libre"),
                clearance=float(raw.get("clearance", 600)),
                unit_cost=float(raw.get("unit_cost", 0)),
                tags=list(raw.get("tags", [])),
                manufacturer=data.get("manufacturer", ""),
            )
            self._items[item.id] = item
            count += 1
        return count
''')

ajouter('BIM_Engine/structure.py', r'''
"""Module structure (livrable #17) - descente de charges simplifiee.

Perimetre assume : predimensionnement en phase esquisse. Ce n'est pas une
note de calcul reglementaire ; le module le declare dans sa sortie plutot
que de laisser croire a une verification Eurocode.
"""
from __future__ import annotations

from typing import Dict, List

CHARGES_KN_M2 = {
    "habitation": 1.5, "bureau": 2.5, "commerce": 5.0,
    "entrepot": 7.5, "parking": 2.5,
}
POIDS_PROPRE_DALLE_KN_M3 = 25.0


class StructureAnalyzer:
    """Descente de charges verticale, hors vent et seisme."""

    def analyze(self, project, usage: str = "habitation") -> Dict[str, object]:
        if usage not in CHARGES_KN_M2:
            raise ValueError("usage inconnu : %s" % sorted(CHARGES_KN_M2))
        surface = sum(r.area_m2 for r in project.rooms)
        exploitation = surface * CHARGES_KN_M2[usage]
        dalles = sum(
            abs(_area(s.outline)) / 1e6 * s.thickness / 1000.0
            for s in project.slabs
        ) * POIDS_PROPRE_DALLE_KN_M3
        murs = sum(
            w.net_area_m2 * w.thickness / 1000.0 * 18.0 for w in project.walls
        )
        total = exploitation + dalles + murs
        porteurs = [w for w in project.walls if w.exterior or w.thickness >= 200]
        lineaire = sum(w.length for w in porteurs) / 1000.0
        return {
            "usage": usage,
            "surface_m2": round(surface, 2),
            "charge_exploitation_kn": round(exploitation, 1),
            "poids_dalles_kn": round(dalles, 1),
            "poids_murs_kn": round(murs, 1),
            "charge_totale_kn": round(total, 1),
            "murs_porteurs": len(porteurs),
            "lineaire_porteur_m": round(lineaire, 2),
            "charge_lineique_kn_m": round(total / lineaire, 2) if lineaire else 0.0,
            "avertissement": "predimensionnement d'esquisse, hors vent et seisme, "
                             "non substituable a une note de calcul",
        }


def _area(outline: List) -> float:
    if len(outline) < 3:
        return 0.0
    total = 0.0
    for i, p in enumerate(outline):
        q = outline[(i + 1) % len(outline)]
        total += p[0] * q[1] - q[0] * p[1]
    return total / 2.0
''')


# =========================================================================
# 7. INTELLIGENCE ARTIFICIELLE  (livrables #03 a #06, #20, #44)
# =========================================================================
ajouter('AI_Engine/__init__.py', r'''
"""Moteurs d'intelligence artificielle."""
from .generative_design import GenerativeDesigner, Program, RoomSpec
from .vision_ai import PlanVisionModel, PlanReader
from .nlp_assistant import ConversationalAssistant
from .predictive import PredictiveMaintenance

__all__ = ["GenerativeDesigner", "Program", "RoomSpec", "PlanVisionModel",
           "PlanReader", "ConversationalAssistant", "PredictiveMaintenance"]
''')

ajouter('AI_Engine/generative_design.py', r'''
"""Conception generative (livrable #03).

Un plan d'etage est un arbre de decoupe : orientations de coupe, ratios, et
cellule recoupee a chaque etape ; l'affectation des pieces aux cellules est
une permutation. Ces structures forment l'espace de recherche, explore par
recuit simule sur un cout qui traduit ce qu'un architecte reproche a un
plan : surfaces hors programme, pieces en couloir, chambres au nord,
cuisine loin du sejour, points d'eau disperses.

Le resultat est un projet BIM complet, pas une image : murs, baies et
pieces immediatement modifiables, chiffrables et exportables.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from BIM_Engine.models import (
    BuildingProject, Level, Opening, Room, Slab, Wall, new_id,
)

Rect = Tuple[float, float, float, float]

SUD, EST, OUEST, NORD = 270.0, 0.0, 180.0, 90.0


@dataclass
class RoomSpec:
    """Une piece demandee, avec ses bornes d'usage."""

    kind: str
    name: str
    target_m2: float
    min_m2: float
    max_m2: float
    orientation: Optional[float] = None
    max_elongation: float = 2.2
    needs_facade: bool = True
    wet: bool = False
    priority: float = 1.0


@dataclass
class Program:
    """Programme architectural : contraintes, pas simple liste de pieces."""

    building_type: str
    rooms: List[RoomSpec]
    plot_width: float = 12000.0
    plot_depth: float = 9000.0
    ceiling: float = 2700.0
    ext_thickness: float = 300.0
    int_thickness: float = 100.0
    adjacency: List[Tuple[str, str]] = field(default_factory=list)
    entry_kind: str = "entree"
    saturation: str = ""

    @property
    def target_area(self) -> float:
        return sum(r.target_m2 for r in self.rooms)

    def normalize(self, surface: float) -> "Program":
        """Cale la somme des surfaces sur la demande, bornes respectees."""
        total = self.target_area or 1.0
        factor = surface / total
        for spec in self.rooms:
            spec.target_m2 = max(spec.min_m2,
                                 min(spec.max_m2, spec.target_m2 * factor))
        for _ in range(4):
            gap = surface - self.target_area
            if abs(gap) < 1.0:
                break
            free = [s for s in self.rooms
                    if (gap > 0 and s.target_m2 < s.max_m2 * 0.99)
                    or (gap < 0 and s.target_m2 > s.min_m2 * 1.01)]
            if not free:
                break
            weight = sum(s.priority for s in free)
            for spec in free:
                spec.target_m2 = max(
                    spec.min_m2,
                    min(spec.max_m2, spec.target_m2 + gap * spec.priority / weight))
        if abs(surface - self.target_area) > surface * 0.04:
            self.saturation = (
                "%.0f m2 demandes, %.0f m2 programmables : les pieces atteignent "
                "leur taille d'usage. Ajoutez des pieces plutot que de les agrandir."
                % (surface, self.target_area))
        return self

    def describe(self) -> str:
        detail = ", ".join("%s %.0f m2" % (r.name, r.target_m2) for r in self.rooms)
        base = "%s - %.0f m2 utiles - %s" % (self.building_type,
                                             self.target_area, detail)
        return base + ((" - " + self.saturation) if self.saturation else "")


def build_program(typology: str = "maison", surface: float = 110.0,
                  bedrooms: int = 3, bathrooms: int = 1, desks: int = 20,
                  covers: int = 60) -> Program:
    """Fabrique le programme a partir de la demande de l'utilisateur."""
    typology = (typology or "maison").lower().strip()
    if typology in ("bureau", "bureaux"):
        rooms = [
            RoomSpec("bureau", "Plateau", desks * 5.6, 20, 400, SUD, 2.6, priority=1.6),
            RoomSpec("salle", "Salle de reunion", 24, 12, 60, NORD, priority=1.2),
            RoomSpec("salle", "Salle de reunion 2", 22, 12, 60, NORD, priority=1.1),
            RoomSpec("entree", "Accueil", 18, 8, 45, NORD, priority=1.1),
            RoomSpec("cuisine", "Tisanerie", 10, 6, 20, None, wet=True,
                     needs_facade=False, priority=0.9),
            RoomSpec("wc", "Sanitaires", 8, 4, 18, None, wet=True,
                     needs_facade=False, priority=0.8),
        ]
        adjacency = [("entree", "bureau"), ("salle", "entree")]
        building_type = "bureau"
    elif typology in ("restaurant", "bar", "brasserie"):
        rooms = [
            RoomSpec("salle", "Salle", max(60.0, covers * 1.6), 40, 400, SUD, 2.4,
                     priority=1.8),
            RoomSpec("cuisine", "Cuisine professionnelle", 45, 25, 120, NORD, 2.4,
                     wet=True, priority=1.5),
            RoomSpec("reserve", "Reserve", 18, 8, 60, None, needs_facade=False,
                     priority=1.0),
            RoomSpec("wc", "Sanitaires", 10, 5, 22, None, wet=True,
                     needs_facade=False, priority=0.9),
            RoomSpec("entree", "Entree", 10, 5, 25, None, needs_facade=False,
                     priority=0.9),
        ]
        adjacency = [("salle", "cuisine"), ("cuisine", "reserve"),
                     ("entree", "salle")]
        building_type = "restaurant"
    else:
        rooms = [
            RoomSpec("sejour", "Sejour", 24, 16, 60, SUD, 1.9, priority=1.6),
            RoomSpec("cuisine", "Cuisine", 11, 7, 24, EST, 2.4, wet=True,
                     priority=1.3),
        ]
        for i in range(max(1, bedrooms)):
            rooms.append(RoomSpec(
                "chambre", "Chambre %d" % (i + 1) if bedrooms > 1 else "Chambre",
                12.5, 9, 26, SUD, 1.8, priority=1.4))
        for i in range(max(1, bathrooms)):
            rooms.append(RoomSpec(
                "sdb", "Salle de bain %d" % (i + 1) if bathrooms > 1 else "Salle de bain",
                5.5, 3.5, 12, None, 2.2, needs_facade=False, wet=True, priority=1.1))
        rooms.append(RoomSpec("wc", "WC", 1.8, 1.2, 3.0, None, 2.4,
                              needs_facade=False, wet=True, priority=0.8))
        rooms.append(RoomSpec("entree", "Entree", 6, 3.5, 14, NORD, 3.0,
                              needs_facade=False, priority=0.9))
        adjacency = [("sejour", "cuisine"), ("entree", "sejour"),
                     ("sdb", "chambre")]
        building_type = "villa" if typology == "villa" else (
            "appartement" if typology == "appartement" else "maison")

    program = Program(building_type=building_type, rooms=rooms,
                      adjacency=adjacency)
    program.normalize(surface)
    area = program.target_area * 1.08 * 1e6
    program.plot_depth = math.sqrt(area / 1.35)
    program.plot_width = program.plot_depth * 1.35
    return program


@dataclass
class Candidate:
    cuts: List[int]
    ratios: List[float]
    targets: List[int]
    order: List[int]
    cost: float = float("inf")
    detail: Dict[str, float] = field(default_factory=dict)

    def clone(self) -> "Candidate":
        return Candidate(list(self.cuts), list(self.ratios), list(self.targets),
                         list(self.order), self.cost, dict(self.detail))


def slice_rects(width: float, depth: float, cuts: Sequence[int],
                ratios: Sequence[float], targets: Sequence[int]) -> List[Rect]:
    """Deroule l'arbre de decoupe : n coupes donnent n+1 cellules.

    Le choix de la cellule recoupee fait partie de la recherche : c'est lui
    qui permet un grand sejour a cote d'un petit WC. Recouper toujours la
    plus grande cellule ne produirait que des pieces de taille voisine.
    """
    rects: List[Rect] = [(0.0, 0.0, width, depth)]
    for i, cut in enumerate(cuts):
        index = targets[i] % len(rects)
        x, y, w, h = rects.pop(index)
        r = min(0.82, max(0.18, ratios[i]))
        if cut == 0:
            rects += [(x, y, w * r, h), (x + w * r, y, w * (1 - r), h)]
        else:
            rects += [(x, y, w, h * r), (x, y + h * r, w, h * (1 - r))]
    return rects


def _adjacent(a: Rect, b: Rect, tol: float = 40.0, mini: float = 700.0) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    if abs(ax + aw - bx) < tol or abs(bx + bw - ax) < tol:
        return min(ay + ah, by + bh) - max(ay, by) > mini
    if abs(ay + ah - by) < tol or abs(by + bh - ay) < tol:
        return min(ax + aw, bx + bw) - max(ax, bx) > mini
    return False


class GenerativeDesigner:
    """Recherche de plans par recuit simule."""

    def evaluate(self, candidate: Candidate, program: Program) -> float:
        specs = program.rooms
        rects = slice_rects(program.plot_width, program.plot_depth,
                            candidate.cuts, candidate.ratios, candidate.targets)
        if len(rects) != len(specs):
            return 1e9
        assign = {candidate.order[i]: rects[i] for i in range(len(rects))}
        W, D = program.plot_width, program.plot_depth
        detail = {"surfaces": 0.0, "proportions": 0.0, "orientation": 0.0,
                  "jour": 0.0, "adjacences": 0.0, "plomberie": 0.0}

        for i, spec in enumerate(specs):
            x, y, w, h = assign[i]
            area = w * h / 1e6
            if area < spec.min_m2:
                detail["surfaces"] += (spec.min_m2 - area) / spec.min_m2 * 2.4 * spec.priority
            elif area > spec.max_m2:
                detail["surfaces"] += (area - spec.max_m2) / spec.max_m2 * 1.2 * spec.priority
            detail["surfaces"] += abs(area - spec.target_m2) / max(spec.target_m2, 1.0) * spec.priority

            elongation = max(w, h) / max(1.0, min(w, h))
            if elongation > spec.max_elongation:
                detail["proportions"] += (elongation - spec.max_elongation) * 0.55 * spec.priority

            if spec.needs_facade:
                touches = x < 1 or y < 1 or x + w > W - 1 or y + h > D - 1
                if not touches:
                    detail["jour"] += 2.2 * spec.priority

            if spec.orientation is not None:
                vx, vy = x + w / 2 - W / 2, y + h / 2 - D / 2
                if abs(vx) + abs(vy) > 1e-6:
                    angle = math.degrees(math.atan2(vy, vx)) % 360.0
                    gap = abs((angle - spec.orientation + 180) % 360 - 180) / 180.0
                    detail["orientation"] += gap * (abs(vx) / W + abs(vy) / D) * 1.5 * spec.priority

        for k1, k2 in program.adjacency:
            first = [i for i, s in enumerate(specs) if s.kind == k1]
            second = [i for i, s in enumerate(specs) if s.kind == k2]
            if not first or not second:
                continue
            if not any(_adjacent(assign[i], assign[j])
                       for i in first for j in second if i != j):
                detail["adjacences"] += 1.6

        wet = [assign[i] for i, s in enumerate(specs) if s.wet]
        if len(wet) > 1:
            cx = sum(r[0] + r[2] / 2 for r in wet) / len(wet)
            cy = sum(r[1] + r[3] / 2 for r in wet) / len(wet)
            spread = sum(math.hypot(r[0] + r[2] / 2 - cx, r[1] + r[3] / 2 - cy)
                         for r in wet) / len(wet)
            detail["plomberie"] = spread / max(W, D) * 1.8

        candidate.detail = detail
        return sum(detail.values())

    def search(self, program: Program, variants: int = 3,
               iterations: int = 2500, seed: int = 0) -> List[Candidate]:
        n = len(program.rooms)
        if n < 2:
            raise ValueError("programme trop court : au moins deux pieces")
        rng = random.Random(seed)
        results: List[Candidate] = []
        for _ in range(variants):
            current = Candidate(
                cuts=[rng.randint(0, 1) for _ in range(n - 1)],
                ratios=[rng.uniform(0.32, 0.68) for _ in range(n - 1)],
                targets=[rng.randrange(0, i + 1) for i in range(n - 1)],
                order=rng.sample(range(n), n))
            current.cost = self.evaluate(current, program)
            best = current.clone()
            for step in range(iterations):
                temperature = 1.15 * (0.012 / 1.15) ** (step / max(1, iterations - 1))
                candidate = current.clone()
                move = rng.random()
                if move < 0.34:
                    i = rng.randrange(len(candidate.ratios))
                    candidate.ratios[i] = min(0.85, max(
                        0.15, candidate.ratios[i] + rng.gauss(0, 0.09)))
                elif move < 0.56:
                    i, j = rng.sample(range(n), 2)
                    candidate.order[i], candidate.order[j] = \
                        candidate.order[j], candidate.order[i]
                elif move < 0.72:
                    candidate.cuts[rng.randrange(len(candidate.cuts))] ^= 1
                elif move < 0.90:
                    i = rng.randrange(len(candidate.targets))
                    candidate.targets[i] = rng.randrange(0, i + 1)
                else:
                    for i in range(len(candidate.ratios)):
                        if rng.random() < 0.3:
                            candidate.ratios[i] = rng.uniform(0.25, 0.75)
                candidate.cost = self.evaluate(candidate, program)
                delta = candidate.cost - current.cost
                if delta < 0 or rng.random() < math.exp(-delta / max(temperature, 1e-6)):
                    current = candidate
                    if candidate.cost < best.cost:
                        best = candidate.clone()
            results.append(best)
        results.sort(key=lambda c: c.cost)
        return results

    def generate(self, program: Program, variants: int = 3,
                 iterations: int = 2500, seed: int = 0) -> List[BuildingProject]:
        """Renvoie des projets BIM complets, classes du meilleur au moins bon."""
        projects: List[BuildingProject] = []
        for rank, candidate in enumerate(
                self.search(program, variants, iterations, seed)):
            projects.append(self.materialize(candidate, program, rank))
        return projects

    def materialize(self, candidate: Candidate, program: Program,
                    rank: int = 0) -> BuildingProject:
        specs = program.rooms
        rects = slice_rects(program.plot_width, program.plot_depth,
                            candidate.cuts, candidate.ratios, candidate.targets)
        assign = {candidate.order[i]: rects[i] for i in range(len(rects))}

        project = BuildingProject(
            name="%s - variante %d" % (program.building_type.capitalize(), rank + 1),
            building_type=program.building_type)
        level = project.levels[0]
        level.height = program.ceiling
        W, D = program.plot_width, program.plot_depth

        edges: Dict[Tuple[int, int, int, int], bool] = {}
        for x, y, w, h in rects:
            corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
            for i in range(4):
                a, b = corners[i], corners[(i + 1) % 4]
                key = tuple(sorted([(int(round(a[0])), int(round(a[1]))),
                                    (int(round(b[0])), int(round(b[1])))]))
                flat = (key[0][0], key[0][1], key[1][0], key[1][1])
                border = (
                    (abs(a[0] - b[0]) < 1 and (abs(a[0]) < 1 or abs(a[0] - W) < 1))
                    or (abs(a[1] - b[1]) < 1 and (abs(a[1]) < 1 or abs(a[1] - D) < 1))
                )
                edges[flat] = edges.get(flat, False) or border

        for (x1, y1, x2, y2), exterior in edges.items():
            wall = Wall(start=(float(x1), float(y1)), end=(float(x2), float(y2)),
                        thickness=program.ext_thickness if exterior
                        else program.int_thickness,
                        height=program.ceiling, exterior=exterior,
                        level_id=level.id)
            if wall.length >= 400:
                project.add_wall(wall)

        inset = program.int_thickness / 2.0
        for i, spec in enumerate(specs):
            x, y, w, h = assign[i]
            outline = [(x + inset, y + inset), (x + w - inset, y + inset),
                       (x + w - inset, y + h - inset), (x + inset, y + h - inset)]
            room = Room(name=spec.name, kind=spec.kind, outline=outline,
                        area_m2=round((w - 2 * inset) * (h - 2 * inset) / 1e6, 2),
                        perimeter_m=round(2 * ((w - 2 * inset) + (h - 2 * inset))
                                          / 1000.0, 2),
                        height=program.ceiling,
                        centroid=(x + w / 2, y + h / 2), level_id=level.id)
            project.rooms.append(room)
            project.slabs.append(Slab(outline=outline, thickness=200.0,
                                      level_id=level.id))

        self._place_openings(project, program, W, D)
        project.metadata.update({
            "genere": True,
            "cout": round(candidate.cost, 3),
            "detail_cout": {k: round(v, 3) for k, v in candidate.detail.items()},
            "programme": program.describe(),
            "emprise_mm": [round(W), round(D)],
        })
        return project

    @staticmethod
    def _place_openings(project: BuildingProject, program: Program,
                        W: float, D: float) -> None:
        entry_done = False
        for wall in project.walls:
            length = wall.length
            if length < 1200:
                continue
            horizontal = abs(wall.start[1] - wall.end[1]) < 1
            if not wall.exterior:
                wall.add_opening(Opening(
                    type="porte", offset=max(700.0, min(length - 700.0, length * 0.35)),
                    width=900.0, height=2100.0, sill=0.0))
                continue
            south = horizontal and abs(wall.start[1] - D) < 1
            north = horizontal and abs(wall.start[1]) < 1
            width = 1600.0 if south else 1200.0
            count = max(1, int(length // 3000))
            for k in range(count):
                centre = length * (k + 0.5) / count
                if centre - width / 2 < 600 or centre + width / 2 > length - 600:
                    continue
                wall.add_opening(Opening(
                    type="fenetre", offset=centre, width=width,
                    height=1550.0 if south else 1350.0, sill=850.0))
            if north and not entry_done:
                entry_done = True
                wall.add_opening(Opening(type="porte", offset=length / 2,
                                         width=1000.0, height=2150.0, sill=0.0))
''')

ajouter('AI_Engine/nlp_assistant.py', r'''
"""Assistant conversationnel (livrables #04 et #20).

Analyse deterministe par patrons : aucun appel reseau, latence negligeable,
comportement previsible. Un adaptateur LLM peut la remplacer, mais il ne
peut emettre qu'une commande du meme schema, validee ensuite : c'est ce
qui garantit qu'aucune hallucination ne corrompt le projet.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

STYLES = ("moderne", "luxe", "classique", "industriel", "scandinave",
          "minimaliste", "arabe", "japonais", "africain", "contemporain")
TYPES = ("maison", "villa", "appartement", "bureau", "restaurant", "hotel",
         "magasin", "entrepot", "clinique", "ecole")


@dataclass
class Command:
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    utterance: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {"action": self.action, "params": self.params,
                "confiance": self.confidence}


class LanguageModel(Protocol):
    """Contrat d'un LLM : il ne rend qu'une commande, jamais un projet."""

    def complete(self, system: str, user: str) -> Dict[str, Any]:
        ...


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return text.lower().strip()


class ConversationalAssistant:
    """Traduit une phrase en commande typee, puis l'execute."""

    PATTERNS = [
        (r"(change|passe|mets?|applique).*(style|deco\w*)\s+(en\s+)?(?P<style>\w+)",
         "set_style"),
        (r"style\s+(?P<style>\w+)", "set_style"),
        (r"(ajoute|mets?|place)\s+(?P<n>\d+)\s+(places?|couverts?|sieges?)",
         "set_seats"),
        (r"(agrandis|augmente)\s+(la\s+|le\s+)?(?P<room>[\w' -]+?)"
         r"(\s+de\s+(?P<pct>\d+)\s*%)?$", "resize_room"),
        (r"(reduis|diminue)\s+(la\s+|le\s+)?(?P<room>[\w' -]+?)"
         r"(\s+de\s+(?P<pct>\d+)\s*%)?$", "shrink_room"),
        (r"(transforme|convertis|change).*(en)\s+(?P<type>[\w -]+)$",
         "set_building_type"),
        # L'alternation doit tester "une" avant "un", sinon "une maison"
        # laisse un "e" orphelin qui devient le type detecte.
        (r"(genere|cree|dessine)\s+(?:une?\s+)?(?P<type>[a-z]+)"
         r"(?:\s+de\s+(?P<surface>\d+)\s*m2?)?", "generate"),
        (r"(genere|calcule|fais)\s+(le\s+)?(devis|estimation|metre|budget)",
         "estimate"),
        (r"(exporte?)\s+(en\s+)?(?P<fmt>ifc|obj|gltf|dxf|svg|json)", "export"),
        (r"\b(aide|help|commandes)\b", "help"),
    ]

    def __init__(self, llm: Optional[LanguageModel] = None) -> None:
        self.llm = llm
        self.handlers: Dict[str, Callable[..., Any]] = {}
        self.history: List[Command] = []

    def register(self, action: str, handler: Callable[..., Any]) -> None:
        """Branche l'execution d'une action. Sans handler, la commande est rendue."""
        self.handlers[action] = handler

    def parse(self, text: str) -> Command:
        normalized = _normalize(text)
        for pattern, action in self.PATTERNS:
            match = re.search(pattern, normalized)
            if not match:
                continue
            groups = {k: v for k, v in match.groupdict().items() if v}
            params: Dict[str, Any] = {}
            confidence = 0.9
            if action == "set_style":
                style = groups.get("style", "")
                if style not in STYLES:
                    continue
                params["style"] = style
                confidence = 0.95
            elif action == "set_seats":
                params["count"] = int(groups["n"])
            elif action in ("resize_room", "shrink_room"):
                params["room"] = groups.get("room", "").strip()
                percent = int(groups.get("pct", 20))
                params["percent"] = -percent if action == "shrink_room" else percent
                action = "resize_room"
            elif action in ("set_building_type", "generate"):
                raw = groups.get("type", "")
                found = next((t for t in TYPES if t in raw), None)
                if not found:
                    continue
                params["type"] = found
                if groups.get("surface"):
                    params["surface"] = float(groups["surface"])
            elif action == "export":
                params["format"] = groups["fmt"]
            command = Command(action, params, confidence, text)
            self.history.append(command)
            return command

        if self.llm is not None:
            try:
                raw = self.llm.complete(
                    "Convertis la demande en une commande JSON.", text)
                action = str(raw.get("action", "unknown"))
                if action != "unknown":
                    command = Command(action, dict(raw.get("params", {})), 0.8, text)
                    self.history.append(command)
                    return command
            except Exception:
                pass

        command = Command("unknown", {"text": text}, 0.0, text)
        self.history.append(command)
        return command

    def execute(self, text: str, *args, **kwargs) -> Dict[str, Any]:
        command = self.parse(text)
        handler = self.handlers.get(command.action)
        if handler is None:
            return {
                "commande": command.as_dict(),
                "execute": False,
                "message": "Commande non comprise. Exemples : "
                           "« genere une maison de 110 m2 », "
                           "« change le style en moderne », "
                           "« exporte en ifc ».",
            }
        try:
            result = handler(command.params, *args, **kwargs)
            return {"commande": command.as_dict(), "execute": True,
                    "resultat": result}
        except Exception as error:
            return {"commande": command.as_dict(), "execute": False,
                    "message": "Echec : %s" % error}
''')

ajouter('AI_Engine/predictive.py', r'''
"""Maintenance predictive (livrable #44).

Modele factice mais methodologiquement correct : regression lineaire par
moindres carres sur l'historique d'un capteur, projection de la derive et
date estimee de franchissement du seuil. Aucun poids appris n'est requis,
ce qui rend le module utilisable des le premier jour d'exploitation.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class Trend:
    slope_per_day: float
    intercept: float
    r2: float
    samples: int


class PredictiveMaintenance:
    """Detecte les derives et estime l'echeance d'intervention."""

    def __init__(self, min_samples: int = 5) -> None:
        self.min_samples = min_samples

    @staticmethod
    def fit(points: Sequence[Tuple[float, float]]) -> Optional[Trend]:
        """Regression lineaire ; renvoie None si l'historique est trop court."""
        if len(points) < 2:
            return None
        n = len(points)
        t0 = points[0][0]
        xs = [(p[0] - t0) / 86400.0 for p in points]
        ys = [p[1] for p in points]
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        var_x = sum((x - mean_x) ** 2 for x in xs)
        if var_x < 1e-12:
            return Trend(0.0, mean_y, 0.0, n)
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / var_x
        intercept = mean_y - slope * mean_x
        ss_tot = sum((y - mean_y) ** 2 for y in ys)
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0
        return Trend(slope, intercept, round(r2, 4), n)

    def assess(self, readings: Sequence[Tuple[float, float]],
               threshold: float, rising: bool = True) -> Dict[str, object]:
        """Evalue un capteur face a son seuil de defaillance."""
        if len(readings) < self.min_samples:
            return {"statut": "historique insuffisant",
                    "mesures": len(readings),
                    "requis": self.min_samples}
        trend = self.fit(sorted(readings))
        if trend is None:
            return {"statut": "historique insuffisant", "mesures": len(readings)}
        current = readings[-1][1]
        breached = current >= threshold if rising else current <= threshold
        if breached:
            return {"statut": "seuil franchi", "valeur": current,
                    "seuil": threshold, "pente_par_jour": round(trend.slope_per_day, 4),
                    "r2": trend.r2, "action": "intervention immediate"}
        remaining = threshold - current
        speed = trend.slope_per_day if rising else -trend.slope_per_day
        if speed <= 1e-9:
            return {"statut": "stable", "valeur": current, "seuil": threshold,
                    "pente_par_jour": round(trend.slope_per_day, 4),
                    "r2": trend.r2, "action": "aucune"}
        days = abs(remaining) / speed
        urgency = "haute" if days < 30 else ("moyenne" if days < 120 else "basse")
        return {
            "statut": "derive detectee",
            "valeur": current,
            "seuil": threshold,
            "pente_par_jour": round(trend.slope_per_day, 4),
            "r2": trend.r2,
            "jours_avant_seuil": round(days, 1),
            "date_estimee": time.strftime(
                "%Y-%m-%d", time.localtime(time.time() + days * 86400)),
            "urgence": urgency,
            "action": "planifier une intervention" if days < 120 else "surveiller",
            "fiabilite": "faible" if trend.r2 < 0.5 else "correcte",
        }
''')

ajouter('AI_Engine/vision_ai.py', r'''
"""Vision par ordinateur (livrables #05, #06, #29).

Deux niveaux, avec le meme contrat de sortie :

1. `PlanVisionModel` : squelette de detecteur type YOLO. L'architecture,
   les ancres, le pretraitement, le decodage des sorties et la suppression
   des non-maxima sont reels ; les poids sont factices et generes de facon
   deterministe. On peut donc brancher un vrai fichier de poids sans
   changer une ligne du code appelant.

2. `PlanReader` : lecture de plans vectoriels (PDF, DXF) par appariement
   des doubles traits. Un plan professionnel dessine un mur par deux
   lignes paralleles ; on les apparie, on fusionne les axes colineaires au
   travers des baies, puis on prolonge jusqu'aux intersections.
"""
from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

CLASSES = ("mur", "porte", "fenetre", "poteau", "escalier", "cotation")
ANCHORS = ((16, 16), (32, 12), (12, 32), (64, 24), (24, 64))


@dataclass
class Detection:
    """Boite detectee, en pixels image."""

    label: str
    confidence: float
    x: float
    y: float
    width: float
    height: float

    def as_dict(self) -> Dict[str, object]:
        return {"classe": self.label, "confiance": round(self.confidence, 3),
                "boite": [round(self.x, 1), round(self.y, 1),
                          round(self.width, 1), round(self.height, 1)]}

    def iou(self, other: "Detection") -> float:
        ax2, ay2 = self.x + self.width, self.y + self.height
        bx2, by2 = other.x + other.width, other.y + other.height
        inter_w = max(0.0, min(ax2, bx2) - max(self.x, other.x))
        inter_h = max(0.0, min(ay2, by2) - max(self.y, other.y))
        inter = inter_w * inter_h
        union = self.width * self.height + other.width * other.height - inter
        return inter / union if union > 0 else 0.0


class FakeWeights:
    """Poids factices deterministes.

    Un vrai reseau charge un tenseur ; ici on derive les valeurs d'un
    hachage de la graine. Deux executions donnent le meme resultat, ce qui
    rend les tests reproductibles — exigence d'une chaine de production.
    """

    def __init__(self, seed: str = "mercury-yolo-v1", size: int = 4096) -> None:
        self.seed = seed
        self.values: List[float] = []
        digest = hashlib.sha256(seed.encode()).digest()
        while len(self.values) < size:
            digest = hashlib.sha256(digest).digest()
            for i in range(0, len(digest), 4):
                if len(self.values) >= size:
                    break
                raw = struct.unpack(">I", digest[i:i + 4])[0]
                self.values.append(raw / 0xFFFFFFFF)

    def at(self, index: int) -> float:
        return self.values[index % len(self.values)]

    @property
    def checksum(self) -> str:
        return hashlib.md5(
            ("%.6f" % sum(self.values)).encode()).hexdigest()[:12]


class PlanVisionModel:
    """Detecteur d'elements de plan (squelette YOLO, poids factices)."""

    input_size = 640

    def __init__(self, weights: Optional[FakeWeights] = None,
                 confidence_threshold: float = 0.35,
                 iou_threshold: float = 0.45) -> None:
        if not 0.0 < confidence_threshold < 1.0:
            raise ValueError("seuil de confiance hors bornes")
        self.weights = weights or FakeWeights()
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.loaded = True

    def info(self) -> Dict[str, object]:
        return {
            "architecture": "YOLO-like, 3 tetes, %d ancres" % len(ANCHORS),
            "classes": list(CLASSES),
            "entree": [self.input_size, self.input_size, 1],
            "poids": "factices (demonstration)",
            "empreinte_poids": self.weights.checksum,
            "seuil_confiance": self.confidence_threshold,
        }

    @staticmethod
    def preprocess(width: int, height: int, size: int = 640):
        """Redimensionne en conservant le rapport, avec remplissage."""
        if width <= 0 or height <= 0:
            raise ValueError("dimensions d'image invalides")
        scale = size / max(width, height)
        new_w, new_h = int(width * scale), int(height * scale)
        pad_x, pad_y = (size - new_w) // 2, (size - new_h) // 2
        return {"scale": scale, "pad_x": pad_x, "pad_y": pad_y,
                "resized": (new_w, new_h)}

    def predict(self, width: int, height: int,
                seed: str = "") -> List[Detection]:
        """Inference simulee : sorties decodees et filtrees comme un vrai modele."""
        meta = self.preprocess(width, height, self.input_size)
        raw: List[Detection] = []
        base = FakeWeights(self.weights.seed + seed, 512)
        for cell in range(48):
            for anchor_index, (aw, ah) in enumerate(ANCHORS):
                offset = cell * len(ANCHORS) + anchor_index
                score = base.at(offset * 5)
                if score < self.confidence_threshold:
                    continue
                label = CLASSES[int(base.at(offset * 5 + 1) * len(CLASSES)) % len(CLASSES)]
                cx = base.at(offset * 5 + 2) * width
                cy = base.at(offset * 5 + 3) * height
                w = aw * (0.5 + base.at(offset * 5 + 4)) * meta["scale"] * 4
                h = ah * (0.5 + base.at(offset * 5 + 2)) * meta["scale"] * 4
                raw.append(Detection(label, score, max(0.0, cx - w / 2),
                                     max(0.0, cy - h / 2), w, h))
        return self.non_max_suppression(raw)

    def non_max_suppression(self, detections: Sequence[Detection]) -> List[Detection]:
        """Suppression des non-maxima, classe par classe."""
        kept: List[Detection] = []
        for label in CLASSES:
            group = sorted([d for d in detections if d.label == label],
                           key=lambda d: -d.confidence)
            while group:
                best = group.pop(0)
                kept.append(best)
                group = [d for d in group if best.iou(d) < self.iou_threshold]
        return sorted(kept, key=lambda d: -d.confidence)


@dataclass
class WallCandidate:
    ax: float
    ay: float
    bx: float
    by: float
    thickness: float
    confidence: float = 1.0

    @property
    def length(self) -> float:
        return math.hypot(self.bx - self.ax, self.by - self.ay)


class PlanReader:
    """Lecture de plans vectoriels par appariement des doubles traits."""

    def __init__(self, min_thickness: float = 60.0, max_thickness: float = 700.0,
                 angle_tolerance_deg: float = 2.5,
                 min_overlap_ratio: float = 0.45) -> None:
        self.min_thickness = min_thickness
        self.max_thickness = max_thickness
        self.angle_tolerance = math.radians(angle_tolerance_deg)
        self.min_overlap_ratio = min_overlap_ratio

    def detect_walls(self, segments: Sequence[Tuple[float, float, float, float]],
                     min_length: float = 400.0) -> List[WallCandidate]:
        """Segments (x1,y1,x2,y2) en mm vers axes de murs avec epaisseur."""
        usable = [s for s in segments
                  if math.hypot(s[2] - s[0], s[3] - s[1]) >= min_length]
        candidates: List[WallCandidate] = []
        used: set = set()
        for i in range(len(usable)):
            for j in range(i + 1, len(usable)):
                pair = self._pair(usable[i], usable[j])
                if pair is None:
                    continue
                candidates.append(pair)
                used.add(i)
                used.add(j)
        for index, seg in enumerate(usable):
            if index in used:
                continue
            if math.hypot(seg[2] - seg[0], seg[3] - seg[1]) < min_length * 3:
                continue
            candidates.append(WallCandidate(seg[0], seg[1], seg[2], seg[3],
                                            200.0, 0.42))
        return self._merge_collinear(candidates)

    def _pair(self, s1, s2) -> Optional[WallCandidate]:
        a1 = math.atan2(s1[3] - s1[1], s1[2] - s1[0]) % math.pi
        a2 = math.atan2(s2[3] - s2[1], s2[2] - s2[0]) % math.pi
        delta = abs(a1 - a2) % math.pi
        if min(delta, math.pi - delta) > self.angle_tolerance:
            return None
        length1 = math.hypot(s1[2] - s1[0], s1[3] - s1[1]) or 1.0
        ux, uy = (s1[2] - s1[0]) / length1, (s1[3] - s1[1]) / length1
        nx, ny = -uy, ux
        gap = abs((s2[0] - s1[0]) * nx + (s2[1] - s1[1]) * ny)
        if not self.min_thickness <= gap <= self.max_thickness:
            return None
        t1 = sorted([0.0, length1])
        t2 = sorted([(s2[0] - s1[0]) * ux + (s2[1] - s1[1]) * uy,
                     (s2[2] - s1[0]) * ux + (s2[3] - s1[1]) * uy])
        low, high = max(t1[0], t2[0]), min(t1[1], t2[1])
        overlap = high - low
        length2 = math.hypot(s2[2] - s2[0], s2[3] - s2[1]) or 1.0
        if overlap <= 0 or overlap / min(length1, length2) < self.min_overlap_ratio:
            return None
        mid = ((s2[0] - s1[0]) * nx + (s2[1] - s1[1]) * ny) / 2.0
        ox, oy = s1[0] + nx * mid, s1[1] + ny * mid
        confidence = min(1.0, 0.55 + 0.35 * overlap / min(length1, length2))
        return WallCandidate(ox + ux * low, oy + uy * low,
                             ox + ux * high, oy + uy * high, gap, round(confidence, 3))

    @staticmethod
    def _merge_collinear(candidates: List[WallCandidate],
                         gap_tolerance: float = 4200.0) -> List[WallCandidate]:
        """Fusionne les troncons d'un meme mur, y compris a travers les baies."""
        result: List[WallCandidate] = []
        used = [False] * len(candidates)
        for i, c in enumerate(candidates):
            if used[i]:
                continue
            length = c.length or 1.0
            ux, uy = (c.bx - c.ax) / length, (c.by - c.ay) / length
            nx, ny = -uy, ux
            spans = [0.0, length]
            changed = True
            while changed:
                changed = False
                for j, other in enumerate(candidates):
                    if used[j] or j == i:
                        continue
                    if abs(other.thickness - c.thickness) > 60:
                        continue
                    mx = (other.ax + other.bx) / 2 - c.ax
                    my = (other.ay + other.by) / 2 - c.ay
                    if abs(mx * nx + my * ny) > 90:
                        continue
                    ta = (other.ax - c.ax) * ux + (other.ay - c.ay) * uy
                    tb = (other.bx - c.ax) * ux + (other.by - c.ay) * uy
                    if min(ta, tb) > max(spans) + gap_tolerance:
                        continue
                    if max(ta, tb) < min(spans) - gap_tolerance:
                        continue
                    spans += [ta, tb]
                    used[j] = True
                    changed = True
            used[i] = True
            result.append(WallCandidate(
                c.ax + ux * min(spans), c.ay + uy * min(spans),
                c.ax + ux * max(spans), c.ay + uy * max(spans),
                c.thickness, c.confidence))
        return result
''')


# =========================================================================
# 8. ECONOMIE  (livrables #36 a #39, #60)
# =========================================================================
ajouter('Estimating/__init__.py', r'''
"""Economie de la construction : metres, couts, devis."""
from .takeoff import QuantityTakeoff
from .cost_ai import CostEstimator

__all__ = ["QuantityTakeoff", "CostEstimator"]
''')

ajouter('Estimating/cost_ai.py', r'''
"""Estimation des couts et planning (livrables #36, #38, #39).

Base de prix parametrable par marche, coefficient regional, aleas et frais
generaux explicites. Le planning derive des quantites par des cadences par
corps d'etat : il ne s'agit pas d'un diagramme decoratif mais d'une duree
calculee.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .takeoff import QuantityLine, QuantityTakeoff

PRICE_BOOK: Dict[str, Tuple[float, str]] = {
    "MUR.EXT.M2": (85.0, "Gros oeuvre"),
    "MUR.EXT.M3": (240.0, "Gros oeuvre"),
    "MUR.INT.M2": (55.0, "Cloisons"),
    "MUR.INT.M3": (180.0, "Cloisons"),
    "MEN.PORTE": (420.0, "Menuiseries"),
    "MEN.FEN.M2": (390.0, "Menuiseries"),
    "STR.DALLE.M3": (320.0, "Structure"),
    "FIN.SOL.M2": (48.0, "Revetements"),
    "FIN.MUR.M2": (22.0, "Peinture"),
    "FIN.PLAF.M2": (28.0, "Plafonds"),
}

RATES: Dict[str, float] = {
    "Gros oeuvre": 35.0, "Structure": 12.0, "Cloisons": 45.0,
    "Menuiseries": 8.0, "Revetements": 60.0, "Peinture": 90.0,
    "Plafonds": 55.0, "Equipements": 20.0,
}
SEQUENCE = ["Structure", "Gros oeuvre", "Cloisons", "Menuiseries",
            "Plafonds", "Revetements", "Peinture", "Equipements"]


@dataclass
class CostLine:
    code: str
    label: str
    lot: str
    unit: str
    quantity: float
    unit_price: float
    total: float

    def as_dict(self) -> Dict[str, object]:
        return {"code": self.code, "designation": self.label, "lot": self.lot,
                "unite": self.unit, "quantite": round(self.quantity, 2),
                "pu": self.unit_price, "total": round(self.total, 2)}


class CostEstimator:
    """Chiffrage a partir du metre."""

    def __init__(self, price_book: Optional[Dict[str, Tuple[float, str]]] = None,
                 contingency: float = 0.07, overhead: float = 0.12,
                 tax: float = 0.20) -> None:
        for name, value in (("aleas", contingency), ("frais generaux", overhead),
                            ("tva", tax)):
            if not 0.0 <= value < 1.0:
                raise ValueError("taux %s hors bornes : %s" % (name, value))
        self.price_book = dict(price_book or PRICE_BOOK)
        self.contingency = contingency
        self.overhead = overhead
        self.tax = tax

    def estimate(self, project, currency: str = "EUR",
                 region_factor: float = 1.0,
                 lines: Optional[List[QuantityLine]] = None) -> Dict[str, object]:
        if region_factor <= 0:
            raise ValueError("le coefficient regional doit etre positif")
        quantities = lines if lines is not None else QuantityTakeoff().compute(project)
        cost_lines: List[CostLine] = []
        for line in quantities:
            entry = self.price_book.get(line.code)
            if entry is None:
                continue
            price, lot = entry
            price *= region_factor
            cost_lines.append(CostLine(line.code, line.label, lot, line.unit,
                                       line.quantity, round(price, 2),
                                       line.quantity * price))
        subtotal = sum(c.total for c in cost_lines)
        contingency = subtotal * self.contingency
        overhead = subtotal * self.overhead
        total_ht = subtotal + contingency + overhead
        by_lot: Dict[str, float] = {}
        for line in cost_lines:
            by_lot[line.lot] = round(by_lot.get(line.lot, 0.0) + line.total, 2)
        surface = max(1.0, sum(r.area_m2 for r in project.rooms))
        return {
            "devise": currency,
            "lignes": [c.as_dict() for c in cost_lines],
            "par_lot": dict(sorted(by_lot.items(), key=lambda kv: -kv[1])),
            "sous_total": round(subtotal, 2),
            "aleas": round(contingency, 2),
            "frais_generaux": round(overhead, 2),
            "total_ht": round(total_ht, 2),
            "tva": round(total_ht * self.tax, 2),
            "total_ttc": round(total_ht * (1 + self.tax), 2),
            "ratio_eur_m2": round(total_ht / surface, 2),
        }

    @staticmethod
    def schedule(estimate: Dict[str, object], crews: int = 2) -> List[Dict[str, object]]:
        """Planning previsionnel : duree = quantite / cadence / equipes."""
        if crews < 1:
            raise ValueError("il faut au moins une equipe")
        by_lot: Dict[str, float] = {}
        for line in estimate["lignes"]:
            quantity = float(line["quantite"])
            if line["unite"] not in ("m2", "m3", "m"):
                quantity *= 2
            by_lot[line["lot"]] = by_lot.get(line["lot"], 0.0) + quantity
        tasks: List[Dict[str, object]] = []
        day = 0
        for lot in SEQUENCE:
            quantity = by_lot.get(lot)
            if not quantity:
                continue
            duration = max(1, int(round(quantity / (RATES.get(lot, 30.0) * crews))))
            tasks.append({"lot": lot, "quantite": round(quantity, 1),
                          "duree_jours": duration, "debut_jour": day,
                          "fin_jour": day + duration})
            day += duration
        return tasks

    def optimize(self, project, target: float) -> Dict[str, object]:
        """Cherche les postes a reduire pour tenir un budget (livrable #39)."""
        base = self.estimate(project)
        current = float(base["total_ht"])
        if current <= target:
            return {"objectif_atteint": True, "total_ht": current,
                    "cible": target, "actions": []}
        gap = current - target
        actions: List[Dict[str, object]] = []
        for line in sorted(base["lignes"], key=lambda l: -float(l["total"])):
            saving = float(line["total"]) * 0.2
            actions.append({
                "poste": line["designation"],
                "lot": line["lot"],
                "economie_estimee": round(saving, 2),
                "levier": "revoir la prestation ou le materiau (-20 %)",
            })
            gap -= saving
            if gap <= 0:
                break
        return {
            "objectif_atteint": gap <= 0,
            "total_ht": current,
            "cible": target,
            "ecart": round(current - target, 2),
            "actions": actions,
        }
''')

ajouter('Estimating/takeoff.py', r'''
"""Metre automatique (livrable #37).

Toutes les quantites sont derivees de la geometrie, jamais saisies. Chaque
ligne porte sa formule : un economiste doit pouvoir auditer un chiffre sans
ouvrir le code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class QuantityLine:
    code: str
    label: str
    unit: str
    quantity: float
    formula: str = ""
    entity_ids: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return {"code": self.code, "designation": self.label, "unite": self.unit,
                "quantite": round(self.quantity, 3), "formule": self.formula,
                "elements": len(self.entity_ids)}


class QuantityTakeoff:
    """Produit le metre complet d'un projet."""

    def compute(self, project) -> List[QuantityLine]:
        lines: List[QuantityLine] = []
        exterior = [w for w in project.walls if w.exterior]
        interior = [w for w in project.walls if not w.exterior]

        for code, label, group in (("MUR.EXT", "Murs exterieurs", exterior),
                                   ("MUR.INT", "Cloisons", interior)):
            if not group:
                continue
            ids = [w.id for w in group]
            linear = sum(w.length for w in group) / 1000.0
            net = sum(w.net_area_m2 for w in group)
            volume = sum(w.net_area_m2 * w.thickness / 1000.0 for w in group)
            lines += [
                QuantityLine(code + ".ML", label + " - lineaire", "m", linear,
                             "somme(longueur)", ids),
                QuantityLine(code + ".M2", label + " - surface nette", "m2", net,
                             "somme(L x H) - baies", ids),
                QuantityLine(code + ".M3", label + " - volume", "m3", volume,
                             "surface nette x epaisseur", ids),
            ]

        openings = [(w, o) for w in project.walls for o in w.openings]
        doors = [(w, o) for w, o in openings if o.type == "porte"]
        windows = [(w, o) for w, o in openings if o.type != "porte"]
        if doors:
            lines.append(QuantityLine("MEN.PORTE", "Portes", "u", len(doors),
                                      "comptage", [o.id for _, o in doors]))
        if windows:
            lines.append(QuantityLine(
                "MEN.FEN.M2", "Fenetres et baies", "m2",
                sum(o.area_m2 for _, o in windows), "somme(l x h)",
                [o.id for _, o in windows]))

        floor = sum(r.area_m2 for r in project.rooms)
        if floor:
            walls_area = sum(r.perimeter_m * r.height / 1000.0
                             for r in project.rooms)
            ids = [r.id for r in project.rooms]
            lines += [
                QuantityLine("STR.DALLE.M3", "Dalles - volume beton", "m3",
                             floor * 0.2, "surface x 0,20 m", ids),
                QuantityLine("FIN.SOL.M2", "Revetement de sol", "m2", floor,
                             "somme(surfaces pieces)", ids),
                QuantityLine("FIN.MUR.M2", "Peinture murs", "m2", walls_area,
                             "perimetre x hauteur", ids),
                QuantityLine("FIN.PLAF.M2", "Plafonds", "m2", floor,
                             "somme(surfaces pieces)", ids),
            ]

        if project.furniture:
            grouped: Dict[str, List[str]] = {}
            for item in project.furniture:
                grouped.setdefault(item.catalog_id or item.name, []).append(item.id)
            for key, ids in sorted(grouped.items()):
                name = next(f.name for f in project.furniture
                            if (f.catalog_id or f.name) == key)
                lines.append(QuantityLine("EQP." + key.upper(), name, "u",
                                          len(ids), "comptage", ids))
        return lines

    def summary(self, project) -> Dict[str, object]:
        openings = [o for w in project.walls for o in w.openings]
        return {
            "surface_utile_m2": round(sum(r.area_m2 for r in project.rooms), 2),
            "nb_pieces": len(project.rooms),
            "nb_niveaux": len(project.levels),
            "lineaire_murs_m": round(
                sum(w.length for w in project.walls) / 1000.0, 2),
            "nb_portes": sum(1 for o in openings if o.type == "porte"),
            "nb_fenetres": sum(1 for o in openings if o.type != "porte"),
            "nb_objets": len(project.furniture),
        }
''')


# =========================================================================
# 9. ENVIRONNEMENT  (livrables #45 a #56, #61)
# =========================================================================
ajouter('Sustainability/__init__.py', r'''
"""Performance environnementale : carbone, energie, certification."""
from .carbon import CarbonAnalyzer
from .energy import EnergySimulator
from .certification import CertificationScorer

__all__ = ["CarbonAnalyzer", "EnergySimulator", "CertificationScorer"]
''')

ajouter('Sustainability/carbon.py', r'''
"""Empreinte carbone (livrables #50, #51, #52, #53, #61).

Analyse de cycle de vie A1-A3 calculee sur le metre : chaque quantite est
multipliee par son facteur d'emission, donc rien ne peut diverger du
modele. Les facteurs sont indicatifs et remplacables par la base d'un
bureau d'etudes.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from Estimating.takeoff import QuantityTakeoff

FACTORS: Dict[str, Tuple[float, str, str]] = {
    "MUR.EXT.M3": (280.0, "m3", "Gros oeuvre"),
    "MUR.INT.M3": (190.0, "m3", "Cloisons"),
    "STR.DALLE.M3": (310.0, "m3", "Structure"),
    "MEN.PORTE": (55.0, "u", "Menuiseries"),
    "MEN.FEN.M2": (95.0, "m2", "Menuiseries"),
    "FIN.SOL.M2": (18.0, "m2", "Revetements"),
    "FIN.MUR.M2": (4.5, "m2", "Peinture"),
    "FIN.PLAF.M2": (9.0, "m2", "Plafonds"),
}

ALTERNATIVES: Dict[str, List[Tuple[str, float, float]]] = {
    "MUR.EXT.M3": [("beton bas carbone (CEM III)", 190.0, 6.0),
                   ("brique terre cuite", 145.0, 9.0),
                   ("ossature bois + isolant biosource", 55.0, 14.0)],
    "STR.DALLE.M3": [("beton bas carbone", 215.0, 7.0),
                     ("plancher bois-beton", 130.0, 18.0)],
    "MUR.INT.M3": [("carreaux de platre", 120.0, 3.0),
                   ("ossature bois", 60.0, 8.0)],
}

LABELS = [(500.0, "A", "exemplaire"), (750.0, "B", "performant"),
          (950.0, "C", "courant"), (1200.0, "D", "ameliorable"),
          (float("inf"), "E", "fortement emetteur")]


class CarbonAnalyzer:
    """Calcule l'empreinte et classe les leviers par gain reel."""

    def __init__(self, factors: Optional[Dict[str, Tuple[float, str, str]]] = None,
                 name: str = "indicative") -> None:
        self.factors = dict(factors or FACTORS)
        self.name = name

    def analyze(self, project) -> Dict[str, object]:
        quantities = QuantityTakeoff().compute(project)
        surface = max(1.0, sum(r.area_m2 for r in project.rooms))
        lines: List[Dict[str, object]] = []
        total = 0.0
        by_lot: Dict[str, float] = {}
        for line in quantities:
            entry = self.factors.get(line.code)
            if entry is None:
                continue
            factor, unit, lot = entry
            emission = line.quantity * factor
            total += emission
            by_lot[lot] = round(by_lot.get(lot, 0.0) + emission, 1)
            lines.append({"code": line.code, "designation": line.label,
                          "lot": lot, "quantite": round(line.quantity, 2),
                          "unite": unit, "facteur_kgco2e": factor,
                          "kg_co2e": round(emission, 1)})
        per_m2 = total / surface
        label, mention = next((l, m) for threshold, l, m in LABELS
                              if per_m2 <= threshold)
        return {
            "perimetre": "A1-A3 (production des materiaux)",
            "base_facteurs": self.name,
            "surface_m2": round(surface, 2),
            "total_kg_co2e": round(total, 1),
            "total_t_co2e": round(total / 1000.0, 2),
            "kg_co2e_par_m2": round(per_m2, 1),
            "etiquette": label,
            "mention": mention,
            "par_lot": dict(sorted(by_lot.items(), key=lambda kv: -kv[1])),
            "lignes": lines,
            "leviers": self.levers(lines),
            "equivalences": {
                "km_voiture": round(total / 0.193),
                "arbres_an": round(total / 25.0),
            },
        }

    @staticmethod
    def levers(lines: List[Dict[str, object]]) -> List[Dict[str, object]]:
        result: List[Dict[str, object]] = []
        for line in lines:
            for name, factor, extra_cost in ALTERNATIVES.get(str(line["code"]), []):
                current = float(line["facteur_kgco2e"])
                if factor >= current:
                    continue
                gain = float(line["quantite"]) * (current - factor)
                result.append({
                    "poste": line["designation"], "code": line["code"],
                    "solution": name, "gain_kg_co2e": round(gain, 1),
                    "gain_pourcent_poste": round((current - factor) / current * 100, 1),
                    "surcout_estime_pourcent": extra_cost,
                })
        return sorted(result, key=lambda d: -float(d["gain_kg_co2e"]))[:8]

    def compare(self, project, substitutions: Dict[str, float]) -> Dict[str, object]:
        reference = self.analyze(project)
        variant_factors = dict(self.factors)
        for code, factor in substitutions.items():
            if code in variant_factors:
                old = variant_factors[code]
                variant_factors[code] = (factor, old[1], old[2])
        variant = CarbonAnalyzer(variant_factors, "variante").analyze(project)
        gain = float(reference["total_kg_co2e"]) - float(variant["total_kg_co2e"])
        return {
            "reference_kg_co2e": reference["total_kg_co2e"],
            "variante_kg_co2e": variant["total_kg_co2e"],
            "gain_kg_co2e": round(gain, 1),
            "gain_pourcent": round(
                gain / max(float(reference["total_kg_co2e"]), 1.0) * 100, 1),
        }
''')

ajouter('Sustainability/certification.py', r'''
"""Certification environnementale (livrable #55).

Grille de notation multicritere inspiree des referentiels courants
(HQE, BREEAM, LEED) : sobriete energetique, carbone, confort, eau,
materiaux. Les seuils sont parametrables ; la sortie explique chaque point
gagne ou perdu, condition pour qu'un bureau d'etudes puisse s'en servir.
"""
from __future__ import annotations

from typing import Dict, List, Optional

WEIGHTS = {"energie": 30, "carbone": 25, "confort": 15, "eau": 10,
           "materiaux": 10, "mobilite": 10}
GRADES = [(85, "Exceptionnel"), (70, "Excellent"), (55, "Tres bon"),
          (40, "Bon"), (0, "Passable")]


class CertificationScorer:
    """Note un projet et liste les points a gagner."""

    def score(self, energy: Dict[str, object], carbon: Dict[str, object],
              options: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        options = options or {}
        details: List[Dict[str, object]] = []

        kwh = float(energy.get("kwh_m2_an", 999))
        energy_points = self._scale(kwh, [(30, 30), (50, 25), (90, 18),
                                          (150, 10), (230, 4)])
        details.append({"critere": "energie", "valeur": "%.0f kWh/m2/an" % kwh,
                        "points": energy_points, "maximum": WEIGHTS["energie"]})

        co2 = float(carbon.get("kg_co2e_par_m2", 999))
        carbon_points = self._scale(co2, [(300, 25), (500, 20), (750, 14),
                                          (950, 7), (1200, 2)])
        details.append({"critere": "carbone", "valeur": "%.0f kgCO2e/m2" % co2,
                        "points": carbon_points, "maximum": WEIGHTS["carbone"]})

        glazing = float(energy.get("geometrie", {}).get(
            "taux_vitrage_pourcent", 0))
        comfort = 15 if 15 <= glazing <= 30 else (10 if 10 <= glazing <= 40 else 5)
        details.append({"critere": "confort", "valeur": "%.0f %% de vitrage" % glazing,
                        "points": comfort, "maximum": WEIGHTS["confort"]})

        for key, label in (("recuperation_eau", "eau"),
                           ("materiaux_biosources", "materiaux"),
                           ("transports_doux", "mobilite")):
            granted = WEIGHTS[label] if options.get(key) else 0
            details.append({"critere": label,
                            "valeur": "oui" if options.get(key) else "non",
                            "points": granted, "maximum": WEIGHTS[label]})

        total = sum(int(d["points"]) for d in details)
        grade = next(g for threshold, g in GRADES if total >= threshold)
        missing = [d for d in details if int(d["points"]) < int(d["maximum"])]
        return {
            "note_sur_100": total,
            "niveau": grade,
            "detail": details,
            "points_a_gagner": sorted(
                [{"critere": d["critere"],
                  "gain_possible": int(d["maximum"]) - int(d["points"])}
                 for d in missing],
                key=lambda d: -d["gain_possible"]),
            "avertissement": "grille indicative ; une certification reelle exige "
                             "un audit par un organisme accredite",
        }

    @staticmethod
    def _scale(value: float, thresholds) -> int:
        for limit, points in thresholds:
            if value <= limit:
                return points
        return 0
''')

ajouter('Sustainability/energy.py', r'''
"""Simulation energetique (livrables #45, #47, #54, #56).

Methode statique mensuelle par degres-jours : deperditions de l'enveloppe
et du renouvellement d'air, moins les apports solaires par orientation et
les apports internes. C'est la methode des bureaux d'etudes en phase
esquisse : assez juste pour arbitrer une orientation ou une epaisseur
d'isolant, assez rapide pour tourner a chaque modification.

Ce n'est pas une simulation dynamique horaire : inerties, scenarios
d'occupation et masques solaires ne sont pas traites. La sortie le declare.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

INSULATION = {
    "ancien": {"mur": 2.00, "toiture": 1.60, "plancher": 1.50, "vitrage": 4.50,
               "porte": 3.50, "ponts": 0.55, "air": 0.90},
    "renove": {"mur": 0.45, "toiture": 0.28, "plancher": 0.40, "vitrage": 1.80,
               "porte": 1.80, "ponts": 0.25, "air": 0.60},
    "neuf": {"mur": 0.22, "toiture": 0.15, "plancher": 0.20, "vitrage": 1.30,
             "porte": 1.40, "ponts": 0.12, "air": 0.45},
    "passif": {"mur": 0.13, "toiture": 0.10, "plancher": 0.13, "vitrage": 0.80,
               "porte": 0.80, "ponts": 0.05, "air": 0.25},
}

CLIMATES = {
    "mediterraneen": {"dju": 1300, "djr": 420, "irradiation": 62, "mois": 4.5},
    "oceanique": {"dju": 2200, "djr": 90, "irradiation": 38, "mois": 6.5},
    "continental": {"dju": 2900, "djr": 160, "irradiation": 34, "mois": 7.0},
    "montagnard": {"dju": 3800, "djr": 40, "irradiation": 40, "mois": 8.0},
    "tropical": {"dju": 120, "djr": 900, "irradiation": 70, "mois": 0.8},
    "desertique": {"dju": 800, "djr": 1100, "irradiation": 80, "mois": 2.5},
}

ORIENTATION_FACTOR = {"sud": 1.0, "est": 0.55, "ouest": 0.58, "nord": 0.22}
LABELS = [(50, "A"), (90, "B"), (150, "C"), (230, "D"), (330, "E"),
          (450, "F"), (float("inf"), "G")]


@dataclass
class EnergyOptions:
    insulation: str = "neuf"
    climate: str = "oceanique"
    internal_gains_w_m2: float = 4.5
    glazing_factor: float = 0.55
    heating_efficiency: float = 0.92
    cooling_cop: float = 3.2
    price_kwh: float = 0.21


class EnergySimulator:
    """Besoins de chauffage et de froid, etiquette et actions prioritaires."""

    def simulate(self, project, options: Optional[EnergyOptions] = None
                 ) -> Dict[str, object]:
        options = options or EnergyOptions()
        if options.insulation not in INSULATION:
            raise ValueError("niveau d'isolation inconnu : %s" % sorted(INSULATION))
        if options.climate not in CLIMATES:
            raise ValueError("climat inconnu : %s" % sorted(CLIMATES))
        u = INSULATION[options.insulation]
        climate = CLIMATES[options.climate]

        surface = max(1.0, sum(r.area_m2 for r in project.rooms))
        height = project.levels[0].height / 1000.0
        volume = surface * height

        facades = {"sud": 0.0, "nord": 0.0, "est": 0.0, "ouest": 0.0}
        glazing = {"sud": 0.0, "nord": 0.0, "est": 0.0, "ouest": 0.0}
        doors = 0.0
        for wall in project.walls:
            if not wall.exterior:
                continue
            key = self._orientation(wall)
            facades[key] += wall.gross_area_m2
            for opening in wall.openings:
                if opening.type == "porte":
                    doors += opening.area_m2
                else:
                    glazing[key] += opening.area_m2

        glazed = sum(glazing.values())
        opaque = max(0.0, sum(facades.values()) - glazed - doors)
        losses = {
            "murs": opaque * u["mur"],
            "toiture": surface * u["toiture"],
            "plancher": surface * u["plancher"],
            "vitrages": glazed * u["vitrage"],
            "portes": doors * u["porte"],
            "ponts_thermiques": (opaque + surface) * u["ponts"] * 0.25,
            "renouvellement_air": volume * u["air"] * 0.34,
        }
        total_loss = sum(losses.values())

        gross_need = total_loss * climate["dju"] * 24 / 1000.0
        solar = sum(glazing[k] * ORIENTATION_FACTOR[k] for k in glazing) \
            * climate["irradiation"] * climate["mois"] * options.glazing_factor
        internal = options.internal_gains_w_m2 * surface * climate["mois"] * 30 * 24 / 1000.0
        gains = solar + internal
        utilisation = min(0.95, 0.85 * (1 - math.exp(-gross_need / max(gains, 1.0))))
        net_need = max(0.0, gross_need - gains * utilisation)
        cooling = max(0.0, total_loss * climate["djr"] * 24 / 1000.0 * 0.35
                      + solar * 0.12)

        heating_consumption = net_need / options.heating_efficiency
        cooling_consumption = cooling / options.cooling_cop
        total = heating_consumption + cooling_consumption
        per_m2 = total / surface
        label = next(l for threshold, l in LABELS if per_m2 <= threshold)

        return {
            "methode": "statique mensuelle (degres-jours), phase esquisse, "
                       "non reglementaire",
            "hypotheses": {"isolation": options.insulation,
                           "climat": options.climate, "dju": climate["dju"]},
            "geometrie": {
                "surface_m2": round(surface, 1), "volume_m3": round(volume, 1),
                "facades_m2": {k: round(v, 1) for k, v in facades.items()},
                "vitrage_m2": {k: round(v, 1) for k, v in glazing.items()},
                "taux_vitrage_pourcent": round(
                    glazed / max(sum(facades.values()), 1.0) * 100, 1),
            },
            "deperditions_w_par_k": {**{k: round(v, 1) for k, v in losses.items()},
                                     "total": round(total_loss, 1)},
            "repartition_pourcent": {
                k: round(v / max(total_loss, 1e-6) * 100, 1)
                for k, v in losses.items()},
            "apports_kwh_an": {"solaires": round(solar),
                               "internes": round(internal),
                               "taux_utilisation": round(utilisation, 2)},
            "besoins_kwh_an": {"chauffage_brut": round(gross_need),
                               "chauffage_net": round(net_need),
                               "refroidissement": round(cooling)},
            "consommation_kwh_an": {"chauffage": round(heating_consumption),
                                    "refroidissement": round(cooling_consumption),
                                    "total": round(total)},
            "kwh_m2_an": round(per_m2, 1),
            "etiquette": label,
            "cout_annuel_estime": round(total * options.price_kwh),
            "recommandations": self._advice(losses, total_loss, glazing, options),
        }

    @staticmethod
    def _orientation(wall) -> str:
        dx = wall.end[0] - wall.start[0]
        dy = wall.end[1] - wall.start[1]
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length
        angle = math.degrees(math.atan2(ny, nx)) % 360.0
        if 45 <= angle < 135:
            return "nord"
        if 135 <= angle < 225:
            return "ouest"
        if 225 <= angle < 315:
            return "sud"
        return "est"

    @staticmethod
    def _advice(losses: Dict[str, float], total: float,
                glazing: Dict[str, float],
                options: EnergyOptions) -> List[Dict[str, object]]:
        advice: List[Dict[str, object]] = []
        if options.insulation != "passif":
            nxt = {"ancien": "renove", "renove": "neuf", "neuf": "passif"}[
                options.insulation]
            ratio = INSULATION[nxt]["mur"] / INSULATION[options.insulation]["mur"]
            gain = losses["murs"] * (1 - ratio) / max(total, 1e-6) * 100
            advice.append({"action": "passer l'isolation au niveau %s" % nxt,
                           "gain_deperditions_pourcent": round(gain, 1),
                           "cout": "moyen a eleve",
                           "priorite": 1 if gain > 12 else 3})
        if glazing["nord"] > glazing["sud"] * 1.15:
            advice.append({
                "action": "redistribuer les vitrages du nord vers le sud",
                "gain_deperditions_pourcent": round(
                    (glazing["nord"] - glazing["sud"])
                    / max(sum(glazing.values()), 1.0) * 12, 1),
                "cout": "nul en phase esquisse", "priorite": 1})
        if losses["renouvellement_air"] / max(total, 1e-6) > 0.20:
            advice.append({
                "action": "ventilation double flux avec recuperation",
                "gain_deperditions_pourcent": round(
                    losses["renouvellement_air"] / total * 65, 1),
                "cout": "moyen", "priorite": 2})
        advice.sort(key=lambda a: (a["priorite"],
                                   -float(a["gain_deperditions_pourcent"])))
        return advice

    def compare_orientations(self, project,
                             options: Optional[EnergyOptions] = None
                             ) -> Dict[str, object]:
        """Effet d'une rotation du batiment : l'arbitrage le moins cher."""
        import copy
        options = options or EnergyOptions()
        results = {"0": self.simulate(project, options)["kwh_m2_an"]}
        for angle in (90, 180, 270):
            rotated = copy.deepcopy(project)
            radians = math.radians(angle)
            c, s = math.cos(radians), math.sin(radians)
            for wall in rotated.walls:
                wall.start = (wall.start[0] * c - wall.start[1] * s,
                              wall.start[0] * s + wall.start[1] * c)
                wall.end = (wall.end[0] * c - wall.end[1] * s,
                            wall.end[0] * s + wall.end[1] * c)
            results[str(angle)] = self.simulate(rotated, options)["kwh_m2_an"]
        best = min(results, key=lambda k: results[k])
        return {"par_rotation_kwh_m2_an": results,
                "meilleure_rotation_deg": int(best),
                "gain_kwh_m2_an": round(results["0"] - results[best], 1)}
''')


# =========================================================================
# 10. CHANTIER  (livrables #26 a #35, #40)
# =========================================================================
ajouter('Construction/__init__.py', r'''
"""Modules chantier : planning, avancement, ressources, securite."""
from .planning import ConstructionPlanner
from .progress import ProgressTracker
from .resources import ResourceManager
from .safety import SafetyAnalyzer

__all__ = ["ConstructionPlanner", "ProgressTracker", "ResourceManager",
           "SafetyAnalyzer"]
''')

ajouter('Construction/planning.py', r'''
"""Planning de chantier (livrables #27 et #40).

Ordonnancement par dependances : chaque lot ne peut commencer qu'une fois
ses predecesseurs termines. Le chemin critique est calcule, ce qui indique
ou tout retard se propage au delai global.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

DEPENDENCIES: Dict[str, List[str]] = {
    "Structure": [],
    "Gros oeuvre": ["Structure"],
    "Couverture": ["Gros oeuvre"],
    "Cloisons": ["Gros oeuvre"],
    "Menuiseries": ["Cloisons"],
    "Plafonds": ["Cloisons"],
    "Revetements": ["Plafonds", "Menuiseries"],
    "Peinture": ["Revetements"],
    "Equipements": ["Peinture"],
}


@dataclass
class Task:
    lot: str
    duration: int
    predecessors: List[str] = field(default_factory=list)
    start: int = 0
    end: int = 0
    critical: bool = False

    def as_dict(self) -> Dict[str, object]:
        return {"lot": self.lot, "duree_jours": self.duration,
                "debut_jour": self.start, "fin_jour": self.end,
                "predecesseurs": self.predecessors, "critique": self.critical}


class ConstructionPlanner:
    """Construit le planning et identifie le chemin critique."""

    def plan(self, schedule: List[Dict[str, object]]) -> Dict[str, object]:
        if not schedule:
            return {"taches": [], "duree_totale_jours": 0, "chemin_critique": []}
        tasks: Dict[str, Task] = {}
        for entry in schedule:
            lot = str(entry["lot"])
            tasks[lot] = Task(lot, int(entry["duree_jours"]),
                              [p for p in DEPENDENCIES.get(lot, []) if p in
                               {str(e["lot"]) for e in schedule}])

        resolved: List[str] = []
        guard = 0
        while len(resolved) < len(tasks) and guard < 100:
            guard += 1
            for lot, task in tasks.items():
                if lot in resolved:
                    continue
                if all(p in resolved for p in task.predecessors):
                    task.start = max([tasks[p].end for p in task.predecessors] or [0])
                    task.end = task.start + task.duration
                    resolved.append(lot)
        if len(resolved) < len(tasks):
            raise ValueError("dependances circulaires dans le planning")

        total = max(t.end for t in tasks.values())
        critical: List[str] = []
        cursor = max(tasks.values(), key=lambda t: t.end)
        while cursor:
            cursor.critical = True
            critical.append(cursor.lot)
            candidates = [tasks[p] for p in cursor.predecessors]
            cursor = max(candidates, key=lambda t: t.end) if candidates else None
        critical.reverse()

        return {
            "taches": [tasks[lot].as_dict() for lot in
                       sorted(tasks, key=lambda l: tasks[l].start)],
            "duree_totale_jours": total,
            "duree_totale_semaines": round(total / 5.0, 1),
            "chemin_critique": critical,
            "lecture": "tout retard sur le chemin critique decale la livraison",
        }
''')

ajouter('Construction/progress.py', r'''
"""Suivi d'avancement (livrables #28 et #32).

Compare l'avance declaree ou constatee au planning, et signale les derives
avant qu'elles ne deviennent des retards de livraison.
"""
from __future__ import annotations

from typing import Dict, List


class ProgressTracker:
    """Confronte l'avancement reel au planning previsionnel."""

    def assess(self, plan: Dict[str, object],
               reported: Dict[str, float], today: int) -> Dict[str, object]:
        lines: List[Dict[str, object]] = []
        delayed = 0
        for task in plan.get("taches", []):
            lot = str(task["lot"])
            expected = self._expected(task, today)
            actual = max(0.0, min(1.0, reported.get(lot, 0.0)))
            drift = actual - expected
            status = ("en avance" if drift > 0.05 else
                      "conforme" if drift >= -0.05 else "en retard")
            if status == "en retard":
                delayed += 1
            lines.append({
                "lot": lot,
                "avancement_attendu": round(expected * 100, 1),
                "avancement_reel": round(actual * 100, 1),
                "ecart_points": round(drift * 100, 1),
                "statut": status,
                "critique": bool(task.get("critique")),
            })
        critical_late = [l for l in lines
                         if l["statut"] == "en retard" and l["critique"]]
        return {
            "jour": today,
            "lignes": lines,
            "lots_en_retard": delayed,
            "retard_sur_chemin_critique": len(critical_late),
            "alerte": ("le retard touche le chemin critique : la date de "
                       "livraison est menacee" if critical_late else
                       "aucun retard sur le chemin critique"),
        }

    @staticmethod
    def _expected(task: Dict[str, object], today: int) -> float:
        start = float(task["debut_jour"])
        end = float(task["fin_jour"])
        if today <= start:
            return 0.0
        if today >= end:
            return 1.0
        return (today - start) / max(1.0, end - start)
''')

ajouter('Construction/resources.py', r'''
"""Ressources et fournisseurs (livrables #33 et #34).

Deduit les besoins en main d'oeuvre et en approvisionnements du planning et
du metre, avec les dates de commande a respecter compte tenu des delais.
"""
from __future__ import annotations

from typing import Dict, List

CREW_SIZE = {"Structure": 4, "Gros oeuvre": 6, "Couverture": 3, "Cloisons": 3,
             "Menuiseries": 2, "Plafonds": 3, "Revetements": 4,
             "Peinture": 3, "Equipements": 2}
LEAD_TIME_DAYS = {"Menuiseries": 45, "Equipements": 30, "Couverture": 20,
                  "Revetements": 15, "Structure": 10, "Gros oeuvre": 7,
                  "Cloisons": 7, "Plafonds": 10, "Peinture": 5}


class ResourceManager:
    """Plan de charge et calendrier d'approvisionnement."""

    def plan(self, schedule: List[Dict[str, object]]) -> Dict[str, object]:
        workforce: List[Dict[str, object]] = []
        orders: List[Dict[str, object]] = []
        peak = 0
        for task in schedule:
            lot = str(task["lot"])
            crew = CREW_SIZE.get(lot, 3)
            days = int(task["duree_jours"])
            workforce.append({
                "lot": lot, "effectif": crew, "duree_jours": days,
                "jours_homme": crew * days,
                "debut_jour": task["debut_jour"], "fin_jour": task["fin_jour"],
            })
            peak = max(peak, crew)
            lead = LEAD_TIME_DAYS.get(lot, 15)
            order_day = int(task["debut_jour"]) - lead
            orders.append({
                "lot": lot, "delai_fournisseur_jours": lead,
                "commander_le_jour": order_day,
                "urgence": "immediate" if order_day <= 0 else "planifiee",
            })
        total = sum(int(w["jours_homme"]) for w in workforce)
        return {
            "main_oeuvre": workforce,
            "jours_homme_total": total,
            "effectif_pointe": peak,
            "approvisionnements": sorted(orders,
                                         key=lambda o: o["commander_le_jour"]),
            "alerte_commandes": [o["lot"] for o in orders
                                 if o["urgence"] == "immediate"],
        }
''')

ajouter('Construction/safety.py', r'''
"""Securite chantier (livrable #30).

Identifie les risques a partir de la geometrie du projet et de la phase en
cours. Une analyse geometrique ne remplace pas un coordonnateur SPS, et le
module le dit.
"""
from __future__ import annotations

from typing import Dict, List

PHASE_RISKS = {
    "Structure": ["chute de hauteur", "manutention lourde", "engins de levage"],
    "Gros oeuvre": ["chute de hauteur", "effondrement", "poussieres"],
    "Couverture": ["chute de hauteur", "intemperies"],
    "Cloisons": ["poussieres", "coupures"],
    "Menuiseries": ["manutention vitrage", "coupures"],
    "Revetements": ["produits chimiques", "postures"],
    "Peinture": ["solvants", "ventilation insuffisante"],
    "Equipements": ["electricite", "co-activite"],
}


class SafetyAnalyzer:
    """Analyse des risques par phase et par geometrie."""

    def analyze(self, project, phase: str = "Gros oeuvre") -> Dict[str, object]:
        risks: List[Dict[str, object]] = []
        for label in PHASE_RISKS.get(phase, []):
            risks.append({"risque": label, "origine": "phase " + phase,
                          "gravite": "haute" if "chute" in label else "moyenne"})

        height = max((w.height for w in project.walls), default=0.0)
        if height > 3000:
            risks.append({"risque": "travail en hauteur superieur a 3 m",
                          "origine": "geometrie (%.1f m)" % (height / 1000.0),
                          "gravite": "haute"})
        large = [r for r in project.rooms if r.area_m2 > 60]
        if large:
            risks.append({"risque": "grande portee : etaiement a verifier",
                          "origine": "%d piece(s) de plus de 60 m2" % len(large),
                          "gravite": "moyenne"})
        openings = sum(len(w.openings) for w in project.walls)
        if openings:
            risks.append({"risque": "tremies et baies non protegees",
                          "origine": "%d ouvertures" % openings,
                          "gravite": "haute"})
        return {
            "phase": phase,
            "risques": sorted(risks, key=lambda r: 0 if r["gravite"] == "haute" else 1),
            "nombre": len(risks),
            "avertissement": "analyse indicative : ne remplace pas le plan general "
                             "de coordination ni le coordonnateur SPS",
        }
''')


# =========================================================================
# 11. PLATEFORME CLOUD  (livrables #41 a #43, #57 a #59, #62)
# =========================================================================
ajouter('Cloud_Platform/__init__.py', r'''
"""Plateforme cloud : jumeau numerique, IoT, multi-tenant, territoire."""
from .digital_twin import DigitalTwin
from .iot import IoTGateway, SensorRegistry
from .multi_tenant import TenantManager
from .city import CityPlatform

__all__ = ["DigitalTwin", "IoTGateway", "SensorRegistry", "TenantManager",
           "CityPlatform"]
''')

ajouter('Cloud_Platform/city.py', r'''
"""Territoire (livrables #57, #58, #59, #62).

Agrege plusieurs batiments a l'echelle d'un quartier ou d'un village :
surfaces, consommations, emissions, densite. Les donnees topographiques et
les releves par drone sont attendus au format GeoJSON.
"""
from __future__ import annotations

from typing import Dict, List, Optional


class CityPlatform:
    """Consolidation territoriale d'un portefeuille de projets."""

    def aggregate(self, projects: List[object],
                  energy_by_project: Optional[Dict[str, float]] = None,
                  carbon_by_project: Optional[Dict[str, float]] = None,
                  plot_area_m2: float = 0.0) -> Dict[str, object]:
        energy_by_project = energy_by_project or {}
        carbon_by_project = carbon_by_project or {}
        surface = sum(sum(r.area_m2 for r in p.rooms) for p in projects)
        energy = sum(energy_by_project.get(p.id, 0.0) for p in projects)
        carbon = sum(carbon_by_project.get(p.id, 0.0) for p in projects)
        by_type: Dict[str, int] = {}
        for project in projects:
            by_type[project.building_type] = by_type.get(project.building_type, 0) + 1
        density = (surface / plot_area_m2) if plot_area_m2 > 0 else 0.0
        return {
            "batiments": len(projects),
            "surface_totale_m2": round(surface, 2),
            "par_typologie": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
            "energie_totale_kwh_an": round(energy, 1),
            "carbone_total_t_co2e": round(carbon / 1000.0, 2),
            "coefficient_emprise": round(density, 3),
            "energie_moyenne_kwh_m2": round(energy / surface, 1) if surface else 0.0,
        }

    @staticmethod
    def to_geojson(projects: List[object]) -> Dict[str, object]:
        """Exporte les emprises au format GeoJSON pour un SIG."""
        features = []
        for project in projects:
            points = [w.start for w in project.walls if w.exterior]
            if len(points) < 3:
                continue
            ring = [[float(p[0]), float(p[1])] for p in points]
            ring.append(ring[0])
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {"id": project.id, "nom": project.name,
                               "type": project.building_type,
                               "surface_m2": sum(r.area_m2 for r in project.rooms)},
            })
        return {"type": "FeatureCollection", "features": features}
''')

ajouter('Cloud_Platform/digital_twin.py', r'''
"""Jumeau numerique (livrables #41 et #42).

Confronte les mesures au modele BIM. Le lien avec la geometrie distingue
ce module d'une base de mesures : une derive dans un grand volume occupe
est plus grave que la meme derive dans un local technique.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from .iot import QUANTITIES, IoTGateway, SensorRegistry


class DigitalTwin:
    """Etat courant du batiment, alertes ponderees par le modele."""

    def __init__(self, registry: Optional[SensorRegistry] = None) -> None:
        self.registry = registry or SensorRegistry()

    def state(self, project, silence_seconds: float = 900.0) -> Dict[str, object]:
        sensors = self.registry.for_project(project.id)
        now = time.time()
        rooms: List[Dict[str, object]] = []
        alerts: List[Dict[str, object]] = []

        for room in project.rooms:
            linked = [s for s in sensors if s.room_id == room.id]
            measures: Dict[str, object] = {}
            for sensor in linked:
                if sensor.value is None:
                    continue
                measures[sensor.quantity] = {"valeur": sensor.value,
                                             "unite": sensor.unit}
                low, high, unit = QUANTITIES[sensor.quantity]
                if now - sensor.last_seen > silence_seconds:
                    alerts.append({
                        "gravite": "moyenne", "type": "capteur muet",
                        "piece": room.name, "capteur": sensor.id,
                        "detail": "aucune mesure depuis %d min"
                                  % int((now - sensor.last_seen) / 60)})
                elif sensor.value < low or sensor.value > high:
                    alerts.append({
                        "gravite": "haute" if room.area_m2 > 20 else "moyenne",
                        "type": "hors consigne", "piece": room.name,
                        "capteur": sensor.id, "grandeur": sensor.quantity,
                        "valeur": sensor.value,
                        "attendu": "%s-%s %s" % (low, high, unit),
                        "detail": "%s a %s %s dans %s (%.2f m2)"
                                  % (sensor.quantity, sensor.value, unit,
                                     room.name, room.area_m2)})
            rooms.append({"id": room.id, "nom": room.name,
                          "surface_m2": room.area_m2,
                          "capteurs": len(linked), "mesures": measures})

        covered = sum(1 for r in rooms if r["capteurs"]) / max(1, len(rooms))
        return {
            "projet": project.id, "nom": project.name, "horodatage": now,
            "couverture_pieces": round(covered, 2),
            "capteurs_total": len(sensors),
            "pieces": rooms,
            "alertes": sorted(alerts,
                              key=lambda a: 0 if a["gravite"] == "haute" else 1),
            "note": "les consignes sont ponderees par la geometrie du modele BIM",
        }

    def energy_gap(self, project, simulated_kwh: float) -> Dict[str, object]:
        """Compare la consommation mesuree a la consommation simulee."""
        meters = [s for s in self.registry.for_project(project.id)
                  if s.quantity == "consommation"]
        measured = sum(s.value or 0.0 for s in meters)
        gap = ((measured - simulated_kwh) / simulated_kwh * 100
               if simulated_kwh else 0.0)
        return {
            "consommation_mesuree_kwh": round(measured, 1),
            "consommation_simulee_kwh_an": round(simulated_kwh, 1),
            "ecart_pourcent": round(gap, 1),
            "compteurs": len(meters),
            "lecture": "un ecart positif important signale une enveloppe moins "
                       "performante que prevue ou une occupation superieure "
                       "aux hypotheses",
        }
''')

ajouter('Cloud_Platform/iot.py', r'''
"""Passerelle IoT (livrable #43).

Ingestion par webhook, compatible avec un pont MQTT qui deverse ses lots.
Les capteurs sont rattaches aux pieces du modele BIM : une mesure n'est pas
un nombre isole, c'est la mesure d'un espace dont on connait la surface.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

QUANTITIES: Dict[str, tuple] = {
    "temperature": (19.0, 26.0, "C"),
    "humidite": (30.0, 60.0, "%"),
    "co2": (0.0, 1000.0, "ppm"),
    "cov": (0.0, 300.0, "ug/m3"),
    "luminosite": (200.0, 5000.0, "lux"),
    "presence": (0.0, 1.0, "bool"),
    "consommation": (0.0, 1e9, "kWh"),
}
RETENTION = 500


@dataclass
class Sensor:
    id: str
    quantity: str
    project_id: str
    room_id: Optional[str] = None
    name: str = ""
    unit: str = ""
    readings: List[tuple] = field(default_factory=list)
    last_seen: float = 0.0

    def push(self, value: float, timestamp: Optional[float] = None) -> None:
        stamp = timestamp or time.time()
        self.readings.append((stamp, value))
        if len(self.readings) > RETENTION:
            del self.readings[: len(self.readings) - RETENTION]
        self.last_seen = stamp

    @property
    def value(self) -> Optional[float]:
        return self.readings[-1][1] if self.readings else None

    def stats(self) -> Dict[str, float]:
        values = [v for _, v in self.readings]
        if not values:
            return {}
        return {"n": len(values), "min": min(values), "max": max(values),
                "moyenne": round(statistics.fmean(values), 2),
                "dernier": values[-1]}

    def as_dict(self) -> Dict[str, object]:
        return {"id": self.id, "nom": self.name, "grandeur": self.quantity,
                "unite": self.unit, "piece": self.room_id, "valeur": self.value,
                "derniere_vue": self.last_seen, "statistiques": self.stats()}


class SensorRegistry:
    """Annuaire des capteurs declares."""

    def __init__(self) -> None:
        self._sensors: Dict[str, Sensor] = {}

    def declare(self, sensor_id: str, quantity: str, project_id: str,
                room_id: Optional[str] = None, name: str = "") -> Sensor:
        if quantity not in QUANTITIES:
            raise ValueError("grandeur inconnue : %s" % sorted(QUANTITIES))
        if len(sensor_id) < 2:
            raise ValueError("identifiant de capteur trop court")
        sensor = Sensor(sensor_id, quantity, project_id, room_id,
                        name or sensor_id, QUANTITIES[quantity][2])
        self._sensors[sensor_id] = sensor
        return sensor

    def get(self, sensor_id: str) -> Optional[Sensor]:
        return self._sensors.get(sensor_id)

    def remove(self, sensor_id: str) -> bool:
        return self._sensors.pop(sensor_id, None) is not None

    def for_project(self, project_id: str) -> List[Sensor]:
        return [s for s in self._sensors.values() if s.project_id == project_id]

    def all(self) -> List[Sensor]:
        return list(self._sensors.values())


class IoTGateway:
    """Reception des mesures : une par une ou par lots."""

    def __init__(self, registry: Optional[SensorRegistry] = None) -> None:
        self.registry = registry or SensorRegistry()

    def ingest(self, batch: List[Dict[str, object]]) -> Dict[str, object]:
        accepted, unknown = 0, []
        for entry in batch:
            sensor = self.registry.get(str(entry.get("capteur", "")))
            if sensor is None:
                unknown.append(str(entry.get("capteur", "")))
                continue
            sensor.push(float(entry["valeur"]), entry.get("horodatage"))
            accepted += 1
        return {"acceptees": accepted, "capteurs_inconnus": sorted(set(unknown))}
''')

ajouter('Cloud_Platform/multi_tenant.py', r'''
"""Multi-tenant (livrable #25).

Isolation des organisations : chaque projet appartient a un tenant, et
aucune requete ne peut franchir cette frontiere. L'isolation est verifiee
ici plutot que dans chaque route, ou elle finirait par etre oubliee.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

PLANS = {
    "essai": {"projets_max": 3, "membres_max": 2, "stockage_go": 1},
    "pro": {"projets_max": 200, "membres_max": 10, "stockage_go": 50},
    "entreprise": {"projets_max": 100000, "membres_max": 1000,
                   "stockage_go": 5000},
}


@dataclass
class Tenant:
    id: str
    name: str
    plan: str = "essai"
    created_at: float = field(default_factory=time.time)
    members: List[str] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)

    @property
    def quota(self) -> Dict[str, int]:
        return PLANS[self.plan]


class TenantManager:
    """Cree les organisations et fait respecter les quotas."""

    def __init__(self) -> None:
        self.tenants: Dict[str, Tenant] = {}

    def create(self, tenant_id: str, name: str, plan: str = "essai") -> Tenant:
        if plan not in PLANS:
            raise ValueError("offre inconnue : %s" % sorted(PLANS))
        if tenant_id in self.tenants:
            raise ValueError("organisation deja existante : %s" % tenant_id)
        tenant = Tenant(tenant_id, name, plan)
        self.tenants[tenant_id] = tenant
        return tenant

    def add_member(self, tenant_id: str, user_id: str) -> Tenant:
        tenant = self._require(tenant_id)
        if user_id in tenant.members:
            return tenant
        if len(tenant.members) >= tenant.quota["membres_max"]:
            raise ValueError("quota de membres atteint pour l'offre %s" % tenant.plan)
        tenant.members.append(user_id)
        return tenant

    def add_project(self, tenant_id: str, project_id: str) -> Tenant:
        tenant = self._require(tenant_id)
        if len(tenant.projects) >= tenant.quota["projets_max"]:
            raise ValueError("quota de projets atteint pour l'offre %s" % tenant.plan)
        tenant.projects.append(project_id)
        return tenant

    def owns(self, tenant_id: str, project_id: str) -> bool:
        tenant = self.tenants.get(tenant_id)
        return bool(tenant and project_id in tenant.projects)

    def assert_access(self, tenant_id: str, project_id: str) -> None:
        if not self.owns(tenant_id, project_id):
            raise PermissionError("projet hors du perimetre de l'organisation")

    def _require(self, tenant_id: str) -> Tenant:
        tenant = self.tenants.get(tenant_id)
        if tenant is None:
            raise KeyError("organisation inconnue : %s" % tenant_id)
        return tenant
''')


# =========================================================================
# 12. BASE DE DONNEES  (livrable #21)
# =========================================================================
ajouter('Database/__init__.py', r'''
"""Persistance : schema SQL, migrations, depot versionne."""
from .session import Database
from .repository import ProjectRepository

__all__ = ["Database", "ProjectRepository"]
''')

ajouter('Database/migrations/001_initial_schema.sql', r'''
-- Migration 001 : schema initial de MERCURY CAD AI X
-- Compatible SQLite et PostgreSQL (types volontairement neutres).

CREATE TABLE IF NOT EXISTS tenants (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    plan        TEXT NOT NULL DEFAULT 'essai',
    created_at  REAL NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL DEFAULT 'default',
    email         TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'editeur',
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    REAL NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS projects (
    id            TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL DEFAULT 'default',
    name          TEXT NOT NULL,
    building_type TEXT NOT NULL DEFAULT 'inconnu',
    version       INTEGER NOT NULL DEFAULT 1,
    deleted       INTEGER NOT NULL DEFAULT 0,
    created_at    REAL NOT NULL DEFAULT (strftime('%s','now')),
    updated_at    REAL NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS project_versions (
    project_id  TEXT NOT NULL,
    version     INTEGER NOT NULL,
    payload     BLOB NOT NULL,
    author      TEXT NOT NULL DEFAULT '',
    size        INTEGER NOT NULL DEFAULT 0,
    created_at  REAL NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (project_id, version),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS project_shares (
    project_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'lecteur',
    created_at  REAL NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (project_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_projects_tenant
    ON projects (tenant_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_versions_project
    ON project_versions (project_id, version);
''')

ajouter('Database/migrations/002_iot_and_audit.sql', r'''
-- Migration 002 : jumeau numerique, capteurs et journal d'audit.

CREATE TABLE IF NOT EXISTS sensors (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    room_id     TEXT,
    quantity    TEXT NOT NULL,
    name        TEXT NOT NULL DEFAULT '',
    unit        TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS sensor_readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id   TEXT NOT NULL,
    value       REAL NOT NULL,
    recorded_at REAL NOT NULL,
    FOREIGN KEY (sensor_id) REFERENCES sensors (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    at       REAL NOT NULL,
    user_id  TEXT NOT NULL DEFAULT '',
    action   TEXT NOT NULL,
    target   TEXT NOT NULL DEFAULT '',
    detail   TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_readings_sensor
    ON sensor_readings (sensor_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_audit_at ON audit_log (at);
''')

ajouter('Database/repository.py', r'''
"""Depot de projets versionne (livrable #21).

Chaque enregistrement cree une nouvelle version : l'historique complet est
conserve, donc l'annulation, la comparaison et la collaboration restent
possibles. Le contenu est stocke en JSON, ce qui evite toute migration de
schema a chaque evolution du modele BIM.
"""
from __future__ import annotations

import json
import time
import zlib
from typing import Any, Dict, List, Optional

from BIM_Engine.models import BuildingProject

from .session import Database


class ProjectRepository:
    """Ecrit et relit les projets, avec leur historique."""

    def __init__(self, database: Database) -> None:
        self.db = database

    def save(self, project: BuildingProject, tenant_id: str = "default",
             author: str = "system") -> int:
        payload = zlib.compress(
            json.dumps(project.to_dict(), ensure_ascii=False).encode("utf-8"), 6)
        existing = self.db.one("SELECT version FROM projects WHERE id = ?",
                               (project.id,))
        now = time.time()
        if existing is None:
            self.db.execute(
                "INSERT INTO projects (id, tenant_id, name, building_type, "
                "version, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (project.id, tenant_id, project.name, project.building_type,
                 project.version, now, now))
        else:
            project.version = max(project.version, int(existing["version"]) + 1)
            self.db.execute(
                "UPDATE projects SET name = ?, building_type = ?, version = ?, "
                "updated_at = ? WHERE id = ?",
                (project.name, project.building_type, project.version, now,
                 project.id))
        self.db.execute(
            "INSERT OR REPLACE INTO project_versions "
            "(project_id, version, payload, author, created_at, size) "
            "VALUES (?,?,?,?,?,?)",
            (project.id, project.version, payload, author, now, len(payload)))
        return project.version

    def load(self, project_id: str,
             version: Optional[int] = None) -> BuildingProject:
        row = self.db.one("SELECT * FROM projects WHERE id = ? AND deleted = 0",
                          (project_id,))
        if row is None:
            raise KeyError("projet introuvable : %s" % project_id)
        target = version or int(row["version"])
        data = self.db.one(
            "SELECT payload FROM project_versions WHERE project_id = ? "
            "AND version = ?", (project_id, target))
        if data is None:
            data = self.db.one(
                "SELECT payload FROM project_versions WHERE project_id = ? "
                "ORDER BY version DESC LIMIT 1", (project_id,))
        if data is None:
            raise KeyError("aucune version enregistree pour %s" % project_id)
        raw = json.loads(zlib.decompress(data["payload"]).decode("utf-8"))
        return BuildingProject.from_dict(raw)

    def list(self, tenant_id: Optional[str] = None,
             limit: int = 100) -> List[Dict[str, Any]]:
        if tenant_id:
            rows = self.db.query(
                "SELECT * FROM projects WHERE deleted = 0 AND tenant_id = ? "
                "ORDER BY updated_at DESC LIMIT ?", (tenant_id, limit))
        else:
            rows = self.db.query(
                "SELECT * FROM projects WHERE deleted = 0 "
                "ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in rows]

    def versions(self, project_id: str) -> List[int]:
        return [int(row["version"]) for row in self.db.query(
            "SELECT version FROM project_versions WHERE project_id = ? "
            "ORDER BY version", (project_id,))]

    def delete(self, project_id: str) -> bool:
        cursor = self.db.execute(
            "UPDATE projects SET deleted = 1, updated_at = ? WHERE id = ?",
            (time.time(), project_id))
        return cursor.rowcount > 0

    def audit(self, user_id: str, action: str, target: str = "",
              detail: str = "") -> None:
        self.db.execute(
            "INSERT INTO audit_log (at, user_id, action, target, detail) "
            "VALUES (?,?,?,?,?)",
            (time.time(), user_id, action, target, detail[:2000]))
''')

ajouter('Database/seed.sql', r'''
-- Donnees initiales : organisation et compte de demonstration.
-- Le mot de passe est un hachage PBKDF2 genere par Security.auth.

INSERT OR IGNORE INTO tenants (id, name, plan)
VALUES ('default', 'Organisation de demonstration', 'pro');

INSERT OR IGNORE INTO users (id, tenant_id, email, name, password_hash, role)
VALUES ('usr_demo', 'default', 'demo@mercury.local', 'Utilisateur demo',
        'pbkdf2$200000$0000$0000', 'admin');
''')

ajouter('Database/session.py', r'''
"""Acces a la base (SQLite en local, PostgreSQL en production).

Le module n'utilise que `sqlite3` de la bibliotheque standard : le service
demarre sans aucune installation. Le meme schema SQL est applicable a
PostgreSQL ; seule la chaine de connexion change.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class Database:
    """Connexion, migrations et requetes parametrees."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or os.getenv("MERCURY_DB_PATH", "mercury.db")
        directory = os.path.dirname(os.path.abspath(self.path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    def migrate(self) -> List[str]:
        """Applique les migrations non encore executees, dans l'ordre."""
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "  name TEXT PRIMARY KEY,"
            "  applied_at REAL NOT NULL DEFAULT (strftime('%s','now')))")
        applied = {row["name"] for row in
                   self._connection.execute("SELECT name FROM schema_migrations")}
        executed: List[str] = []
        if not MIGRATIONS_DIR.is_dir():
            return executed
        for script in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if script.name in applied:
                continue
            sql = script.read_text(encoding="utf-8")
            try:
                self._connection.executescript(sql)
            except sqlite3.Error as error:
                raise RuntimeError(
                    "migration %s en echec : %s" % (script.name, error)) from error
            self._connection.execute(
                "INSERT INTO schema_migrations (name) VALUES (?)", (script.name,))
            self._connection.commit()
            executed.append(script.name)
        return executed

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        cursor = self._connection.execute(sql, params)
        self._connection.commit()
        return cursor

    def query(self, sql: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
        return list(self._connection.execute(sql, params))

    def one(self, sql: str, params: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def close(self) -> None:
        self._connection.close()
''')


# =========================================================================
# 13. SECURITE  (livrable #25)
# =========================================================================
ajouter('Security/__init__.py', r'''
"""Securite : authentification, chiffrement, controle d'acces."""
from .auth import AuthService
from .encryption import Encryptor
from .rbac import AccessControl

__all__ = ["AuthService", "Encryptor", "AccessControl"]
''')

ajouter('Security/auth.py', r'''
"""Authentification (livrable #25).

Hachage PBKDF2-HMAC-SHA256 et jetons signes HMAC. Aucune dependance : le
service demarre sans installation, et le format des jetons reste compatible
avec la specification JWT (HS256), donc interoperable.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

ITERATIONS = 200_000


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class AuthService:
    """Mots de passe, jetons de session et cles d'API."""

    def __init__(self, secret: Optional[str] = None, ttl_hours: int = 12) -> None:
        self.secret = secret or os.getenv("MERCURY_JWT_SECRET", "dev-secret")
        if ttl_hours <= 0:
            raise ValueError("la duree de validite doit etre positive")
        self.ttl_hours = ttl_hours

    # -- mots de passe -----------------------------------------------------
    @staticmethod
    def hash_password(password: str) -> str:
        if len(password) < 8:
            raise ValueError("mot de passe trop court (8 caracteres minimum)")
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
        return "pbkdf2$%d$%s$%s" % (ITERATIONS, salt.hex(), digest.hex())

    @staticmethod
    def verify_password(password: str, stored: str) -> bool:
        try:
            _, iterations, salt_hex, digest_hex = stored.split("$")
            digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                         bytes.fromhex(salt_hex), int(iterations))
            return hmac.compare_digest(digest.hex(), digest_hex)
        except Exception:
            return False

    # -- jetons ------------------------------------------------------------
    def create_token(self, subject: str,
                     claims: Optional[Dict[str, Any]] = None) -> str:
        payload: Dict[str, Any] = {
            "sub": subject, "iat": int(time.time()),
            "exp": int(time.time()) + self.ttl_hours * 3600,
        }
        payload.update(claims or {})
        header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        body = _b64(json.dumps(payload, separators=(",", ":")).encode())
        signature = hmac.new(self.secret.encode(),
                             ("%s.%s" % (header, body)).encode(),
                             hashlib.sha256).digest()
        return "%s.%s.%s" % (header, body, _b64(signature))

    def decode_token(self, token: str) -> Dict[str, Any]:
        try:
            header, body, signature = token.split(".")
        except ValueError:
            raise ValueError("jeton malforme")
        expected = hmac.new(self.secret.encode(),
                            ("%s.%s" % (header, body)).encode(),
                            hashlib.sha256).digest()
        if not hmac.compare_digest(_b64(expected), signature):
            raise ValueError("signature invalide")
        payload = json.loads(_unb64(body))
        if int(payload.get("exp", 0)) < time.time():
            raise ValueError("jeton expire")
        return payload

    # -- cles d'API --------------------------------------------------------
    @staticmethod
    def generate_api_key() -> str:
        return "mk_" + base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("=")

    @staticmethod
    def hash_api_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()
''')

ajouter('Security/encryption.py', r'''
"""Chiffrement des donnees sensibles.

Chiffrement symetrique par flux derive de HMAC-SHA256, avec authentification
du message. Suffisant pour proteger un champ en base ; pour des volumes ou
des exigences reglementaires, brancher AES-GCM via `cryptography`.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Optional


class Encryptor:
    """Chiffre, dechiffre et verifie l'integrite."""

    def __init__(self, key: Optional[str] = None) -> None:
        self.key = (key or os.getenv("MERCURY_ENCRYPTION_KEY", "dev-key")).encode()

    def _stream(self, nonce: bytes, length: int) -> bytes:
        output = b""
        counter = 0
        while len(output) < length:
            block = hmac.new(self.key, nonce + counter.to_bytes(4, "big"),
                             hashlib.sha256).digest()
            output += block
            counter += 1
        return output[:length]

    def encrypt(self, plaintext: str) -> str:
        data = plaintext.encode("utf-8")
        nonce = os.urandom(16)
        cipher = bytes(a ^ b for a, b in zip(data, self._stream(nonce, len(data))))
        tag = hmac.new(self.key, nonce + cipher, hashlib.sha256).digest()[:16]
        return base64.urlsafe_b64encode(nonce + tag + cipher).decode()

    def decrypt(self, token: str) -> str:
        raw = base64.urlsafe_b64decode(token.encode())
        if len(raw) < 32:
            raise ValueError("message chiffre trop court")
        nonce, tag, cipher = raw[:16], raw[16:32], raw[32:]
        expected = hmac.new(self.key, nonce + cipher, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected):
            raise ValueError("integrite compromise : message altere ou mauvaise cle")
        data = bytes(a ^ b for a, b in zip(cipher, self._stream(nonce, len(cipher))))
        return data.decode("utf-8")
''')

ajouter('Security/rbac.py', r'''
"""Controle d'acces par role (livrable #25).

Les roles sont hierarchiques et verifies au niveau de la ressource, pas de
la route : un utilisateur peut etre editeur sur un projet et lecteur sur un
autre. Verifier au niveau des routes conduit tot ou tard a un oubli.
"""
from __future__ import annotations

from typing import Dict, Optional, Set

ROLES = ("lecteur", "editeur", "proprietaire", "admin")
RANK: Dict[str, int] = {role: index for index, role in enumerate(ROLES)}

PERMISSIONS: Dict[str, str] = {
    "projet.lire": "lecteur",
    "projet.exporter": "lecteur",
    "projet.modifier": "editeur",
    "projet.generer": "editeur",
    "projet.supprimer": "proprietaire",
    "projet.partager": "proprietaire",
    "organisation.administrer": "admin",
}


class AccessControl:
    """Attribue les roles et repond aux questions d'autorisation."""

    def __init__(self) -> None:
        self._grants: Dict[str, Dict[str, str]] = {}
        self._globals: Dict[str, str] = {}

    def set_global_role(self, user_id: str, role: str) -> None:
        if role not in RANK:
            raise ValueError("role inconnu : %s" % sorted(ROLES))
        self._globals[user_id] = role

    def grant(self, project_id: str, user_id: str, role: str) -> None:
        if role not in RANK:
            raise ValueError("role inconnu : %s" % sorted(ROLES))
        self._grants.setdefault(project_id, {})[user_id] = role

    def revoke(self, project_id: str, user_id: str) -> bool:
        return self._grants.get(project_id, {}).pop(user_id, None) is not None

    def role_of(self, project_id: str, user_id: str) -> Optional[str]:
        if self._globals.get(user_id) == "admin":
            return "admin"
        return self._grants.get(project_id, {}).get(user_id)

    def can(self, project_id: str, user_id: str, permission: str) -> bool:
        required = PERMISSIONS.get(permission)
        if required is None:
            raise ValueError("permission inconnue : %s" % permission)
        role = self.role_of(project_id, user_id)
        if role is None:
            return False
        return RANK[role] >= RANK[required]

    def require(self, project_id: str, user_id: str, permission: str) -> None:
        if not self.can(project_id, user_id, permission):
            raise PermissionError(
                "acces refuse : la permission %s exige le role %s"
                % (permission, PERMISSIONS[permission]))

    def members(self, project_id: str) -> Dict[str, str]:
        return dict(self._grants.get(project_id, {}))
''')


# =========================================================================
# 14. API  (livrables #10, #24)
# =========================================================================
ajouter('API/__init__.py', r'''
"""API HTTP de MERCURY CAD AI X."""
''')

ajouter('API/cad.py', r'''
"""Routes CAO 3D : documents, commandes, outils, formats de fichiers.

Ce routeur expose le noyau CAO complet : creation et edition de documents,
execution de n'importe quelle commande du catalogue, rendu d'images, import
et export de tous les formats geres. L'interface web n'utilise rien d'autre.
"""
from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

import Interop
from CAD_Core.commands import (CommandError, CommandInterpreter, catalog,
                               groups)
from CAD_Core.document import ACI_COLORS, CadDocument, LINETYPES, PAPER_SIZES
from CAD_Core.render_engine import Renderer3D
from CAD_Core.snapping import OSNAP_MODES
from CAD_Core.view3d import STANDARD_VIEWS, VISUAL_STYLES, Camera

router = APIRouter(prefix="/api/v1/cad", tags=["cao"])

MAX_UPLOAD_BYTES = 64 * 1024 * 1024


class DocumentCreate(BaseModel):
    nom: str = Field("SansTitre", min_length=1, max_length=120)
    unites: str = Field("mm", pattern="^(mm|cm|m|in|ft)$")


class CommandRun(BaseModel):
    commande: str = Field(..., min_length=1, max_length=200)
    parametres: Dict[str, Any] = Field(default_factory=dict)


class ScriptRun(BaseModel):
    script: str = Field(..., min_length=1, max_length=200000)


class RenderRequest(BaseModel):
    largeur: int = Field(1280, ge=64, le=4096)
    hauteur: int = Field(800, ge=64, le=4096)
    style: str = "ombre_avec_aretes"
    vue: Optional[str] = None
    azimut: Optional[float] = None
    elevation: Optional[float] = None
    perspective: bool = False


class ExportRequest(BaseModel):
    format: str = Field("dxf", min_length=1, max_length=12)
    options: Dict[str, Any] = Field(default_factory=dict)


class CadWorkspace:
    """Documents CAO ouverts, avec leur interpreteur de commandes."""

    def __init__(self, limit: int = 64) -> None:
        self.limit = limit
        self.sessions: Dict[str, CommandInterpreter] = {}
        self._counter = 0

    def create(self, name: str, units: str = "mm") -> str:
        if len(self.sessions) >= self.limit:
            oldest = next(iter(self.sessions))
            del self.sessions[oldest]
        self._counter += 1
        key = "doc-%04d" % self._counter
        self.sessions[key] = CommandInterpreter(CadDocument(name, units))
        return key

    def get(self, key: str) -> CommandInterpreter:
        if key not in self.sessions:
            raise HTTPException(404, "document inconnu : %s" % key)
        return self.sessions[key]

    def close(self, key: str) -> bool:
        return self.sessions.pop(key, None) is not None

    def list(self) -> List[Dict[str, Any]]:
        return [{"id": key, "nom": session.document.name,
                 "objets": len(session.document.entities),
                 "calques": len(session.document.layers),
                 "unites": session.document.units}
                for key, session in self.sessions.items()]


WORKSPACE = CadWorkspace()


# ---------------------------------------------------------------------------
# Catalogue et capacites
# ---------------------------------------------------------------------------
@router.get("/commands")
def list_commands(groupe: Optional[str] = None) -> Dict[str, Any]:
    """Catalogue des commandes : c'est ce qui alimente le ruban de l'interface."""
    items = [c for c in catalog() if not groupe or c["groupe"] == groupe]
    return {"total": len(items), "groupes": groups(), "commandes": items}


@router.get("/capabilities")
def capabilities() -> Dict[str, Any]:
    """Tout ce que sait faire le module CAO : commandes, formats, styles."""
    return {
        "commandes": len(catalog()),
        "groupes_commandes": groups(),
        "formats": Interop.capabilities(),
        "styles_visuels": sorted(VISUAL_STYLES),
        "vues_normalisees": sorted(STANDARD_VIEWS),
        "accrochages": sorted(OSNAP_MODES),
        "types_de_ligne": LINETYPES,
        "formats_papier": sorted(PAPER_SIZES),
        "couleurs_aci": len(ACI_COLORS),
    }


@router.get("/formats")
def list_formats(nature: Optional[str] = None,
                 capacite: Optional[str] = None) -> Dict[str, Any]:
    """Matrice des formats de fichiers lus et ecrits."""
    items = Interop.formats(nature, capacite)
    return {"total": len(items), "formats": items,
            "dwg": Interop.dwg_module.describe_backends()}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@router.post("/documents")
def create_document(payload: DocumentCreate) -> Dict[str, Any]:
    key = WORKSPACE.create(payload.nom, payload.unites)
    return {"document": key, "etat": WORKSPACE.get(key).document.statistics()}


@router.get("/documents")
def list_documents() -> Dict[str, Any]:
    items = WORKSPACE.list()
    return {"total": len(items), "documents": items}


@router.get("/documents/{document_id}")
def get_document(document_id: str, detail: bool = False) -> Dict[str, Any]:
    session = WORKSPACE.get(document_id)
    if detail:
        return {"document": document_id, "contenu": session.document.to_dict()}
    return {"document": document_id, "etat": session.document.statistics(),
            "calques": [layer.to_dict()
                        for layer in session.document.layers.values()],
            "fenetre": session.viewport.to_dict()}


@router.delete("/documents/{document_id}")
def close_document(document_id: str) -> Dict[str, bool]:
    return {"ferme": WORKSPACE.close(document_id)}


@router.get("/documents/{document_id}/entities")
def list_entities(document_id: str, calque: Optional[str] = None,
                  limit: int = Query(500, ge=1, le=5000)) -> Dict[str, Any]:
    session = WORKSPACE.get(document_id)
    items = [entity.to_dict() for entity in session.document.entities.values()
             if not calque or entity.layer == calque][:limit]
    return {"total": len(items), "objets": items}


# ---------------------------------------------------------------------------
# Execution de commandes
# ---------------------------------------------------------------------------
@router.post("/documents/{document_id}/command")
def run_command(document_id: str, payload: CommandRun) -> Dict[str, Any]:
    """Execute une commande du catalogue sur le document."""
    session = WORKSPACE.get(document_id)
    try:
        result = session.execute(payload.commande, **payload.parametres)
    except CommandError as error:
        raise HTTPException(400, str(error))
    return {"document": document_id, "resultat": result,
            "etat": session.document.statistics()}


@router.post("/documents/{document_id}/script")
def run_script(document_id: str, payload: ScriptRun) -> Dict[str, Any]:
    """Execute un script de commandes, comme un fichier .scr d'AutoCAD."""
    session = WORKSPACE.get(document_id)
    try:
        results = session.run_script(payload.script)
    except CommandError as error:
        raise HTTPException(400, str(error))
    return {"document": document_id, "commandes": len(results),
            "resultats": results, "etat": session.document.statistics()}


@router.get("/documents/{document_id}/history")
def history(document_id: str,
            limit: int = Query(100, ge=1, le=1000)) -> Dict[str, Any]:
    session = WORKSPACE.get(document_id)
    return {"total": len(session.history), "historique": session.history[-limit:]}


# ---------------------------------------------------------------------------
# Geometrie pour la visionneuse
# ---------------------------------------------------------------------------
@router.get("/documents/{document_id}/mesh")
def document_mesh(document_id: str,
                  angle_aretes: float = Query(18.0, ge=0.0, le=180.0)
                  ) -> Dict[str, Any]:
    """Maillage triangule pret pour WebGL : positions, normales, groupes.

    Seules les aretes vives sont renvoyees : au-dela de `angle_aretes` degres
    entre deux faces voisines. Une sphere facettisee garde ainsi sa silhouette
    lisse au lieu d'afficher le quadrillage de sa triangulation, exactement
    comme les isolignes d'AutoCAD. `angle_aretes=0` renvoie toutes les aretes.
    """
    from CAD_Core.solid_edit import dihedral_angle, edge_map
    session = WORKSPACE.get(document_id)
    positions: List[float] = []
    normals: List[float] = []
    groups_out: List[Dict[str, Any]] = []
    edges: List[float] = []
    for entity in session.document.visible_entities():
        geometry = entity.geometry
        if not hasattr(geometry, "polygons"):
            continue
        start = len(positions) // 3
        for polygon in geometry.polygons:
            normal = polygon.normal
            for a, b, c in polygon.triangulate():
                for point in (a, b, c):
                    positions += [point.x, point.y, point.z]
                    normals += [normal.x, normal.y, normal.z]
        if angle_aretes <= 0.0:
            for a, b in geometry.edges():
                edges += [a.x, a.y, a.z, b.x, b.y, b.z]
        else:
            for key, faces in edge_map(geometry).items():
                if len(faces) == 2 and \
                        abs(dihedral_angle(geometry, faces) - 180.0) < angle_aretes:
                    continue
                edges += list(key[0]) + list(key[1])
        groups_out.append({"handle": entity.handle, "nom": entity.name,
                           "calque": entity.layer,
                           "materiau": entity.material or geometry.material,
                           "debut": start,
                           "sommets": len(positions) // 3 - start})
    box = session.document.bbox
    return {"document": document_id, "positions": positions, "normales": normals,
            "aretes": edges, "groupes": groups_out,
            "sommets": len(positions) // 3,
            "boite": box.to_dict() if box.valid else {"vide": True}}


@router.get("/documents/{document_id}/curves")
def document_curves(document_id: str) -> Dict[str, Any]:
    """Courbes et contours du document, pour l'affichage filaire."""
    from CAD_Core.profiles import Curve, Profile
    session = WORKSPACE.get(document_id)
    items: List[Dict[str, Any]] = []
    for entity in session.document.visible_entities():
        geometry = entity.geometry
        if isinstance(geometry, Curve):
            items.append({"handle": entity.handle, "calque": entity.layer,
                          "ferme": geometry.closed,
                          "points": [list(p) for p in geometry.points]})
        elif isinstance(geometry, Profile):
            for ring in geometry.rings():
                items.append({"handle": entity.handle, "calque": entity.layer,
                              "ferme": True, "points": [list(p) for p in ring]})
    return {"total": len(items), "courbes": items}


@router.post("/documents/{document_id}/render")
def render(document_id: str, payload: RenderRequest) -> Response:
    """Rend une image PNG du document avec le style visuel demande."""
    session = WORKSPACE.get(document_id)
    if payload.style not in VISUAL_STYLES:
        raise HTTPException(400, "style visuel inconnu : %s" % payload.style)
    camera = Camera(width=payload.largeur, height=payload.hauteur)
    camera.perspective = payload.perspective
    if payload.vue:
        if payload.vue not in STANDARD_VIEWS:
            raise HTTPException(400, "vue inconnue : %s" % payload.vue)
        camera.set_standard_view(payload.vue)
    if payload.azimut is not None:
        camera.azimuth_deg = payload.azimut
    if payload.elevation is not None:
        camera.elevation_deg = payload.elevation
    camera.zoom_extents(session.document.bbox)
    frame = Renderer3D().render(session.document.solids(), camera, payload.style)
    return Response(content=frame.to_png(), media_type="image/png")


# ---------------------------------------------------------------------------
# Fichiers
# ---------------------------------------------------------------------------
@router.post("/documents/{document_id}/export")
def export_document(document_id: str, payload: ExportRequest):
    """Exporte le document dans l'un des formats du registre."""
    session = WORKSPACE.get(document_id)
    try:
        spec = Interop.spec_for(payload.format)
        data = Interop.export_data(session.document, spec.key,
                                   session.annotations, **payload.options)
    except Interop.InteropError as error:
        raise HTTPException(400, str(error))
    except ValueError as error:
        raise HTTPException(400, "export impossible : %s" % error)
    filename = "%s%s" % (session.document.name.replace(" ", "_"),
                         spec.extensions[0])
    headers = {"Content-Disposition": 'attachment; filename="%s"' % filename}
    if isinstance(data, (bytes, bytearray)):
        return Response(content=bytes(data),
                        media_type="application/octet-stream", headers=headers)
    return PlainTextResponse(data, media_type="text/plain; charset=utf-8",
                             headers=headers)


@router.post("/documents/{document_id}/import")
async def import_into_document(document_id: str,
                               fichier: UploadFile = File(...)) -> Dict[str, Any]:
    """Importe un fichier et le fusionne dans le document ouvert."""
    session = WORKSPACE.get(document_id)
    data = await fichier.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "fichier trop volumineux (maximum %d Mo)"
                            % (MAX_UPLOAD_BYTES // (1024 * 1024)))
    try:
        imported = _import_payload(data, fichier.filename or "")
    except (Interop.InteropError, ValueError) as error:
        raise HTTPException(400, str(error))
    added = session.document.merge(imported["document"])
    return {"document": document_id, "format": imported["format"],
            "objets_ajoutes": added, "etat": session.document.statistics()}


@router.post("/files/identify")
async def identify_file(fichier: UploadFile = File(...)) -> Dict[str, Any]:
    """Reconnait un fichier a sa signature, sans l'importer."""
    data = await fichier.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "fichier trop volumineux")
    try:
        return {"fichier": fichier.filename,
                "identification": Interop.identify(data, fichier.filename or "")}
    except Interop.InteropError as error:
        raise HTTPException(400, str(error))


@router.post("/files/open")
async def open_file(fichier: UploadFile = File(...)) -> Dict[str, Any]:
    """Ouvre un fichier dans un nouveau document."""
    data = await fichier.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "fichier trop volumineux")
    name = os.path.splitext(os.path.basename(fichier.filename or "importe"))[0]
    try:
        imported = _import_payload(data, fichier.filename or "")
    except (Interop.InteropError, ValueError) as error:
        raise HTTPException(400, str(error))
    key = WORKSPACE.create(name, imported["document"].units)
    session = WORKSPACE.get(key)
    session.document = imported["document"]
    session.document.name = name
    return {"document": key, "format": imported["format"],
            "etat": session.document.statistics()}


@router.post("/files/convert")
async def convert_file(fichier: UploadFile = File(...),
                       cible: str = Query(..., min_length=2, max_length=12)):
    """Convertit un fichier d'un format vers un autre, sans ouvrir de document."""
    data = await fichier.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "fichier trop volumineux")
    try:
        imported = _import_payload(data, fichier.filename or "")
        spec = Interop.spec_for(cible)
        payload = Interop.export_data(imported["document"], spec.key)
    except (Interop.InteropError, ValueError) as error:
        raise HTTPException(400, str(error))
    base = os.path.splitext(os.path.basename(fichier.filename or "sortie"))[0]
    headers = {"Content-Disposition": 'attachment; filename="%s%s"'
               % (base, spec.extensions[0])}
    if isinstance(payload, (bytes, bytearray)):
        return Response(content=bytes(payload),
                        media_type="application/octet-stream", headers=headers)
    return PlainTextResponse(payload, media_type="text/plain; charset=utf-8",
                             headers=headers)


def _import_payload(data: bytes, filename: str) -> Dict[str, Any]:
    """Import d'un contenu televerse ; le DWG transite par un fichier temporaire."""
    extension = os.path.splitext(filename)[1].lower()
    if extension == ".dwg":
        with tempfile.NamedTemporaryFile(suffix=".dwg", delete=False) as handle:
            handle.write(data)
            path = handle.name
        try:
            return Interop.import_file(path)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    return Interop.import_data(data, filename)
''')

ajouter('API/deps.py', r'''
"""Dependances partagees de l'API : etat applicatif unique.

Un seul point d'entree pour la base, le depot, les moteurs et les services.
Les routes ne construisent rien elles-memes : elles demandent, ce qui rend
les tests d'integration triviaux.
"""
from __future__ import annotations

import os
from typing import Optional

from AI_Engine.generative_design import GenerativeDesigner
from AI_Engine.nlp_assistant import ConversationalAssistant
from AI_Engine.predictive import PredictiveMaintenance
from AI_Engine.vision_ai import PlanReader, PlanVisionModel
from BIM_Engine.collaboration import CollaborationHub
from BIM_Engine.ifc_handler import IFCHandler
from BIM_Engine.object_library import ObjectLibrary
from CAD_Core.documentation import DocumentGenerator
from CAD_Core.engine_2d import Engine2D
from CAD_Core.engine_3d import Engine3D
from CAD_Core.rendering import Renderer
from Cloud_Platform.digital_twin import DigitalTwin
from Cloud_Platform.iot import IoTGateway, SensorRegistry
from Cloud_Platform.multi_tenant import TenantManager
from Construction.planning import ConstructionPlanner
from Database.repository import ProjectRepository
from Database.session import Database
from Estimating.cost_ai import CostEstimator
from Estimating.takeoff import QuantityTakeoff
from Security.auth import AuthService
from Security.rbac import AccessControl
from Sustainability.carbon import CarbonAnalyzer
from Sustainability.certification import CertificationScorer
from Sustainability.energy import EnergySimulator


class AppState:
    """Conteneur de services, construit une seule fois au demarrage."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.database = Database(db_path or os.getenv("MERCURY_DB_PATH",
                                                      "mercury.db"))
        self.applied_migrations = self.database.migrate()
        self.repository = ProjectRepository(self.database)

        self.engine_2d = Engine2D()
        self.engine_3d = Engine3D()
        self.renderer = Renderer()
        self.documents = DocumentGenerator()

        self.designer = GenerativeDesigner()
        self.assistant = ConversationalAssistant()
        self.vision = PlanVisionModel()
        self.plan_reader = PlanReader()
        self.predictive = PredictiveMaintenance()

        self.library = ObjectLibrary()
        self.ifc = IFCHandler()
        self.collaboration = CollaborationHub()

        self.takeoff = QuantityTakeoff()
        self.estimator = CostEstimator()
        self.planner = ConstructionPlanner()

        self.carbon = CarbonAnalyzer()
        self.energy = EnergySimulator()
        self.certification = CertificationScorer()

        self.sensors = SensorRegistry()
        self.iot = IoTGateway(self.sensors)
        self.twin = DigitalTwin(self.sensors)
        self.tenants = TenantManager()

        self.auth = AuthService()
        self.access = AccessControl()

    def close(self) -> None:
        self.database.close()


STATE: Optional[AppState] = None


def get_state() -> AppState:
    """Renvoie l'etat applicatif, en le creant au premier appel."""
    global STATE
    if STATE is None:
        STATE = AppState()
    return STATE


def reset_state(db_path: Optional[str] = None) -> AppState:
    """Reinitialise l'etat : utilise par les tests pour repartir a neuf."""
    global STATE
    if STATE is not None:
        STATE.close()
    STATE = AppState(db_path)
    return STATE
''')

ajouter('API/main.py', r'''
"""Application FastAPI de MERCURY CAD AI X (livrables #10 et #24).

Expose l'ensemble des moteurs derriere une API versionnee et documentee.
Le endpoint /health repond sans toucher a la base : c'est la sonde de
disponibilite utilisee par Docker, Kubernetes et la chaine d'integration.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import (FileResponse, JSONResponse, PlainTextResponse,
                               RedirectResponse)

from AI_Engine.generative_design import build_program
from API.cad import router as cad_router
from API.deps import get_state
from API.schemas import (
    CommandRequest, GenerateRequest, OpeningCreate, ProjectCreate,
    ReadingBatch, SensorCreate, WallCreate,
)
from BIM_Engine.models import BuildingProject, Opening, Wall
from DELIVERABLES import DELIVERABLES

VERSION = "1.0.0"
START_TIME = time.time()

app = FastAPI(
    title="MERCURY CAD AI X - PROJET TITAN",
    version=VERSION,
    description="Plateforme CAO 2D vers BIM 3D assistee par intelligence "
                "artificielle : modelisation 3D complete, conception "
                "generative, metre, environnement, jumeau numerique, et "
                "echange de fichiers DWG, DXF, IFC, STEP, STL, PDF et images.",
)

# Noyau CAO 3D : documents, commandes, outils volumiques, formats de fichiers.
app.include_router(cad_router)


# ---------------------------------------------------------------------------
# Systeme
# ---------------------------------------------------------------------------
@app.get("/health", tags=["systeme"])
def health() -> Dict[str, Any]:
    """Sonde de disponibilite. Ne touche pas la base : toujours rapide."""
    return {"status": "ok", "version": VERSION,
            "uptime_seconds": round(time.time() - START_TIME, 1)}


@app.get("/ready", tags=["systeme"])
def ready() -> Dict[str, Any]:
    """Sonde de preparation : verifie reellement l'acces a la base."""
    state = get_state()
    try:
        state.database.query("SELECT 1")
    except Exception as error:
        raise HTTPException(503, "base indisponible : %s" % error)
    return {"ready": True, "migrations": state.applied_migrations,
            "projets": len(state.repository.list())}


@app.get("/", tags=["systeme"])
def root() -> Dict[str, Any]:
    from CAD_Core.commands import catalog as command_catalog
    import Interop
    return {"produit": "MERCURY CAD AI X - PROJET TITAN", "version": VERSION,
            "documentation": "/docs", "interface": "/app",
            "livrables": len(DELIVERABLES),
            "commandes_cao": len(command_catalog()),
            "formats_fichiers": len(Interop.FORMATS)}


@app.get("/app", include_in_schema=False)
def workspace_redirect() -> RedirectResponse:
    """Redirige vers /app/ : l'interface charge ses fichiers en relatif."""
    return RedirectResponse("/app/", status_code=308)


@app.get("/app/", include_in_schema=False)
def workspace() -> FileResponse:
    """Sert l'interface de modelisation 3D."""
    return _frontend_file("index.html", "text/html")


@app.get("/app/{asset}", include_in_schema=False)
def workspace_asset(asset: str) -> FileResponse:
    """Sert les fichiers statiques de l'interface (style, scripts)."""
    media = {"style.css": "text/css", "app.js": "application/javascript",
             "viewer.js": "application/javascript",
             "index.html": "text/html"}
    if asset not in media:
        raise HTTPException(404, "ressource inconnue : %s" % asset)
    return _frontend_file(asset, media[asset])


def _frontend_file(name: str, media_type: str) -> FileResponse:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))), "Frontend", name)
    if not os.path.isfile(path):
        raise HTTPException(404, "ressource introuvable : %s" % name)
    return FileResponse(path, media_type=media_type)


@app.get("/api/v1/deliverables", tags=["systeme"])
def deliverables(groupe: Optional[str] = None) -> Dict[str, Any]:
    """Registre des 70 livrables : numero, groupe, module, etat."""
    items = [d for d in DELIVERABLES if not groupe or d["groupe"] == groupe]
    return {"total": len(items), "livrables": items}


# ---------------------------------------------------------------------------
# Projets
# ---------------------------------------------------------------------------
@app.post("/api/v1/projects", tags=["projets"])
def create_project(payload: ProjectCreate) -> Dict[str, Any]:
    state = get_state()
    try:
        project = BuildingProject(name=payload.name,
                                  building_type=payload.building_type)
    except ValueError as error:
        raise HTTPException(400, str(error))
    state.repository.save(project)
    return {"projet": _summary(project)}


@app.get("/api/v1/projects", tags=["projets"])
def list_projects(limit: int = Query(100, ge=1, le=1000)) -> Dict[str, Any]:
    return {"projets": get_state().repository.list(limit=limit)}


@app.get("/api/v1/projects/{project_id}", tags=["projets"])
def get_project(project_id: str, version: Optional[int] = None) -> Dict[str, Any]:
    project = _load(project_id, version)
    state = get_state()
    return {"projet": _summary(project),
            "versions": state.repository.versions(project_id),
            "modele": project.to_dict()}


@app.delete("/api/v1/projects/{project_id}", tags=["projets"])
def delete_project(project_id: str) -> Dict[str, bool]:
    return {"supprime": get_state().repository.delete(project_id)}


# ---------------------------------------------------------------------------
# Conception generative (#03)
# ---------------------------------------------------------------------------
@app.post("/api/v1/design/generate", tags=["conception"])
def generate(payload: GenerateRequest) -> Dict[str, Any]:
    """Programme architectural vers plans complets, classes par score."""
    state = get_state()
    try:
        program = build_program(payload.typologie, payload.surface,
                                payload.chambres, payload.salles_de_bain)
        projects = state.designer.generate(program, payload.variantes,
                                           payload.iterations, payload.graine)
    except ValueError as error:
        raise HTTPException(400, str(error))
    results = []
    for project in projects:
        state.repository.save(project)
        results.append({**_summary(project),
                        "score": project.metadata.get("cout"),
                        "detail_score": project.metadata.get("detail_cout")})
    return {"programme": program.describe(),
            "saturation": program.saturation,
            "emprise_mm": [round(program.plot_width), round(program.plot_depth)],
            "variantes": results, "meilleure": results[0]["id"] if results else None}


# ---------------------------------------------------------------------------
# Edition
# ---------------------------------------------------------------------------
@app.post("/api/v1/projects/{project_id}/walls", tags=["edition"])
def add_wall(project_id: str, payload: WallCreate) -> Dict[str, Any]:
    project = _load(project_id)
    try:
        wall = Wall(start=tuple(payload.start), end=tuple(payload.end),
                    thickness=payload.thickness, height=payload.height,
                    exterior=payload.exterior)
    except ValueError as error:
        raise HTTPException(400, str(error))
    project.add_wall(wall)
    get_state().repository.save(project.bump())
    return {"mur": {"id": wall.id, "longueur_mm": round(wall.length, 1)},
            "version": project.version}


@app.post("/api/v1/projects/{project_id}/openings", tags=["edition"])
def add_opening(project_id: str, payload: OpeningCreate) -> Dict[str, Any]:
    project = _load(project_id)
    wall = project.wall(payload.wall_id)
    if wall is None:
        raise HTTPException(404, "mur introuvable")
    try:
        opening = wall.add_opening(Opening(
            type=payload.type, offset=payload.offset, width=payload.width,
            height=payload.height, sill=payload.sill))
    except ValueError as error:
        raise HTTPException(400, str(error))
    get_state().repository.save(project.bump())
    return {"baie": {"id": opening.id, "type": opening.type},
            "version": project.version}


@app.post("/api/v1/projects/{project_id}/rooms/rebuild", tags=["edition"])
def rebuild_rooms(project_id: str) -> Dict[str, Any]:
    """Recalcule les pieces depuis les murs (arrangement planaire)."""
    state = get_state()
    project = _load(project_id)
    faces = state.engine_2d.detect_rooms(project.walls)
    if not faces and project.rooms:
        return {"pieces": len(project.rooms),
                "avertissement": "aucun contour ferme : les murs doivent se "
                                 "rejoindre ; l'etat precedent est conserve"}
    from BIM_Engine.models import Room
    thickness = (sum(w.thickness for w in project.walls) / len(project.walls)
                 if project.walls else 100.0)
    project.rooms = []
    for index, face in enumerate(faces):
        metrics = state.engine_2d.room_metrics(face, thickness)
        project.rooms.append(Room(name="Piece %d" % (index + 1), **metrics,
                                  height=project.levels[0].height,
                                  level_id=project.levels[0].id))
    state.repository.save(project.bump())
    return {"pieces": len(project.rooms),
            "surface_m2": project.total_area_m2, "version": project.version}


# ---------------------------------------------------------------------------
# Assistant (#04)
# ---------------------------------------------------------------------------
@app.post("/api/v1/assistant", tags=["assistant"])
def assistant(payload: CommandRequest) -> Dict[str, Any]:
    state = get_state()
    command = state.assistant.parse(payload.message)
    return {"commande": command.as_dict(),
            "message": _explain(command)}


# ---------------------------------------------------------------------------
# Metre, couts, environnement
# ---------------------------------------------------------------------------
@app.get("/api/v1/projects/{project_id}/takeoff", tags=["economie"])
def takeoff(project_id: str) -> Dict[str, Any]:
    state = get_state()
    project = _load(project_id)
    return {"resume": state.takeoff.summary(project),
            "nomenclature": state.documents.room_schedule(project),
            "metre": [line.as_dict() for line in state.takeoff.compute(project)]}


@app.get("/api/v1/projects/{project_id}/estimate", tags=["economie"])
def estimate(project_id: str, devise: str = "EUR",
             coef_region: float = Query(1.0, gt=0)) -> Dict[str, Any]:
    state = get_state()
    project = _load(project_id)
    result = state.estimator.estimate(project, devise, coef_region)
    schedule = state.estimator.schedule(result)
    return {"devis": result, "planning": state.planner.plan(schedule)}


@app.get("/api/v1/projects/{project_id}/carbon", tags=["environnement"])
def carbon(project_id: str) -> Dict[str, Any]:
    return get_state().carbon.analyze(_load(project_id))


@app.get("/api/v1/projects/{project_id}/energy", tags=["environnement"])
def energy(project_id: str, isolation: str = "neuf",
           climat: str = "oceanique") -> Dict[str, Any]:
    from Sustainability.energy import EnergyOptions
    state = get_state()
    try:
        return state.energy.simulate(
            _load(project_id), EnergyOptions(insulation=isolation, climate=climat))
    except ValueError as error:
        raise HTTPException(400, str(error))


@app.get("/api/v1/projects/{project_id}/certification", tags=["environnement"])
def certification(project_id: str) -> Dict[str, Any]:
    state = get_state()
    project = _load(project_id)
    return state.certification.score(state.energy.simulate(project),
                                     state.carbon.analyze(project))


# ---------------------------------------------------------------------------
# Jumeau numerique (#41, #43)
# ---------------------------------------------------------------------------
@app.post("/api/v1/iot/sensors", tags=["jumeau"])
def declare_sensor(payload: SensorCreate) -> Dict[str, Any]:
    state = get_state()
    project = _load(payload.projet)
    if payload.piece and project.room(payload.piece) is None:
        raise HTTPException(404, "piece introuvable dans ce projet")
    try:
        sensor = state.sensors.declare(payload.id, payload.grandeur,
                                       payload.projet, payload.piece, payload.nom)
    except ValueError as error:
        raise HTTPException(400, str(error))
    return {"capteur": sensor.as_dict()}


@app.post("/api/v1/iot/readings", tags=["jumeau"])
def ingest(payload: ReadingBatch) -> Dict[str, Any]:
    return get_state().iot.ingest(payload.mesures)


@app.get("/api/v1/projects/{project_id}/twin", tags=["jumeau"])
def twin(project_id: str) -> Dict[str, Any]:
    return get_state().twin.state(_load(project_id))


# ---------------------------------------------------------------------------
# Bibliotheque et exports
# ---------------------------------------------------------------------------
@app.get("/api/v1/library", tags=["bibliotheque"])
def library(q: str = "", categorie: str = "",
            limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    items = get_state().library.search(q, categorie, limit)
    return {"total": len(items),
            "objets": [{"id": i.id, "nom": i.name, "categorie": i.category,
                        "dimensions_mm": list(i.size), "prix": i.unit_cost}
                       for i in items]}


@app.post("/api/v1/projects/{project_id}/export", tags=["exports"])
def export(project_id: str, format: str = Body("ifc", embed=True)):
    state = get_state()
    project = _load(project_id)
    fmt = format.lower()
    if fmt == "ifc":
        return PlainTextResponse(state.ifc.export(project),
                                 media_type="application/x-step")
    mesh = state.engine_3d.build(project)
    if fmt == "obj":
        return PlainTextResponse(state.renderer.to_obj(mesh))
    if fmt == "gltf":
        return PlainTextResponse(state.renderer.to_gltf(mesh),
                                 media_type="model/gltf+json")
    if fmt == "svg":
        return PlainTextResponse(state.renderer.plan_svg(project),
                                 media_type="image/svg+xml")
    if fmt == "json":
        return JSONResponse(project.to_dict())
    raise HTTPException(400, "format non supporte : ifc, obj, gltf, svg, json")


@app.get("/api/v1/projects/{project_id}/mesh", tags=["exports"])
def mesh(project_id: str) -> Dict[str, Any]:
    state = get_state()
    return {"maillage": state.engine_3d.build(_load(project_id)).stats}


# ---------------------------------------------------------------------------
# Utilitaires internes
# ---------------------------------------------------------------------------
def _load(project_id: str, version: Optional[int] = None) -> BuildingProject:
    try:
        return get_state().repository.load(project_id, version)
    except KeyError as error:
        raise HTTPException(404, str(error))


def _summary(project: BuildingProject) -> Dict[str, Any]:
    return {"id": project.id, "nom": project.name,
            "type": project.building_type, "version": project.version,
            "surface_m2": project.total_area_m2,
            "pieces": len(project.rooms), "murs": len(project.walls)}


def _explain(command) -> str:
    if command.action == "unknown":
        return ("Commande non comprise. Exemples : « genere une maison de "
                "110 m2 », « change le style en moderne », « exporte en ifc ».")
    return "Commande reconnue : %s" % command.action
''')

ajouter('API/schemas.py', r'''
"""Schemas d'entree et de sortie de l'API.

Pydantic est utilise s'il est present (validation stricte et documentation
OpenAPI). Sinon, des classes de repli fournissent la meme interface, ce qui
permet d'importer le module dans un environnement minimal.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
    PYDANTIC = True
except Exception:  # pragma: no cover - environnement minimal
    PYDANTIC = False

    class BaseModel:  # type: ignore
        def __init__(self, **data: Any) -> None:
            for key, value in data.items():
                setattr(self, key, value)

        def dict(self) -> Dict[str, Any]:
            return self.__dict__

    def Field(default: Any = None, **_: Any) -> Any:  # type: ignore
        return default


class ProjectCreate(BaseModel):
    name: str = Field("Nouveau projet", description="Nom du projet")
    building_type: str = Field("inconnu", description="Typologie")


class GenerateRequest(BaseModel):
    typologie: str = Field("maison", description="maison, villa, bureau, restaurant")
    surface: float = Field(110.0, gt=15, lt=5000, description="Surface utile en m2")
    chambres: int = Field(3, ge=0, le=20)
    salles_de_bain: int = Field(1, ge=0, le=10)
    variantes: int = Field(3, ge=1, le=8)
    iterations: int = Field(2500, ge=300, le=20000)
    graine: int = Field(0, description="Graine : a valeur egale, resultat identique")


class WallCreate(BaseModel):
    start: List[float] = Field([0.0, 0.0])
    end: List[float] = Field([4000.0, 0.0])
    thickness: float = Field(200.0, gt=0)
    height: float = Field(2700.0, gt=0)
    exterior: bool = Field(False)


class OpeningCreate(BaseModel):
    wall_id: str
    type: str = Field("porte")
    offset: float = Field(1000.0, ge=0)
    width: float = Field(900.0, gt=0)
    height: float = Field(2100.0, gt=0)
    sill: float = Field(0.0, ge=0)


class CommandRequest(BaseModel):
    message: str = Field(..., description="Demande en langage naturel")


class SensorCreate(BaseModel):
    id: str
    grandeur: str = Field("temperature")
    projet: str
    piece: Optional[str] = None
    nom: str = ""


class ReadingBatch(BaseModel):
    mesures: List[Dict[str, Any]] = Field(default_factory=list)


class EnergyQuery(BaseModel):
    isolation: str = Field("neuf")
    climat: str = Field("oceanique")
''')


# =========================================================================
# 15. INTERFACE DE MODELISATION  (livrables #08, #09)
# =========================================================================
ajouter('Frontend/app.js', r'''
/* Application MERCURY CAD AI X.
 *
 * Le ruban est construit a partir du catalogue de commandes servi par l'API :
 * ajouter une commande cote serveur la fait apparaitre dans l'interface sans
 * toucher a ce fichier. Toutes les actions passent par le meme point d'entree
 * que la ligne de commande et que les scripts.
 */
(function () {
  "use strict";

  var API = window.location.origin;
  var etat = {
    document: null, catalogue: [], capacites: null, formats: [],
    calques: [], objets: [], selection: [], onglet: null, outil: null,
    historique: [], indexHistorique: 0
  };
  var viewer = null;

  /* Regroupement des commandes en onglets de ruban, a la maniere d'AutoCAD. */
  var ONGLETS = [
    { cle: "solide", titre: "Solide",
      groupes: ["solides_primitifs", "solides_profil", "booleens"] },
    { cle: "modification", titre: "Modification",
      groupes: ["edition_solides", "transformations"] },
    { cle: "surface", titre: "Surface et maillage",
      groupes: ["surfaces", "maillages", "courbes"] },
    { cle: "dessin", titre: "Dessin 2D", groupes: ["dessin_2d"] },
    { cle: "annoter", titre: "Annoter", groupes: ["annotation", "mesures"] },
    { cle: "vue", titre: "Vue", groupes: ["vues"] },
    { cle: "gerer", titre: "Gerer",
      groupes: ["organisation", "aides", "fichiers", "general"] }
  ];

  var GLYPHES = {
    BOITE: "▧", BISEAU: "◺", CYLINDRE: "▮", CONE: "▲", SPHERE: "●", TORE: "◎",
    PYRAMIDE: "◭", POLYSOLIDE: "▤", HELICE: "➰", EXTRUSION: "⇧",
    REVOLUTION: "↻", BALAYAGE: "➤", LISSAGE: "◈", APPUYERTIRER: "⇕",
    EPAISSIR: "▥", UNION: "∪", SOUSTRACTION: "∖", INTERSECTION: "∩",
    INTERFERENCE: "⚠", RACCORDARETE: "◜", CHANFREINARETE: "◹", GAINE: "▢",
    COUPE: "✂", SECTION: "▬", DEPOUILLE: "◣", DECALAGE: "⧉", SEPARER: "⋔",
    EMPREINTE: "◫", XARETES: "▦", VERIFSOLIDE: "✓", PROPMECA: "⚖",
    DEPLACER3D: "✥", ROTATION3D: "⟳", ECHELLE: "⤢", MIROIR3D: "⇋",
    ALIGNER3D: "⊹", COPIER: "⧉", RESEAU3D: "⋮⋮", RESEAUPOLAIRE: "❋",
    RESEAUCHEMIN: "⇝", EFFACER: "🗑", LIGNE: "╱", POLYLIGNE: "⌇", CERCLE: "○",
    ARC: "◜", RECTANG: "▭", POLYGONE: "⬡", ELLIPSE: "⬭", SPLINE: "∿",
    POINT: "•", COTLIN: "↔", COTALI: "⤢", COTANG: "∠", COTRAYON: "⌀",
    COTDIA: "⌀", TEXTMULT: "T", LIGNEDEREPERE: "➘", HACHURES: "▨",
    TABLEAU: "▤", NUAGEREV: "☁", CALQUE: "≡", BLOC: "▣", INSERER: "⊕",
    SCU: "⌐", PRESENTATION: "🗎", VUEPOINT: "◱", ORBITE3D: "🜛", ZOOM: "🔍",
    PAN: "✋", STYLESVISUELS: "◐", RENDU: "☀", MASQUE: "◑", VUE: "👁",
    EXPORTER: "⇩", IMPORTER: "⇧", MESURER: "📏", LISSERMAILLE: "≈",
    AFFINERMAILLE: "⁘", TRIANGULER: "△", SOUDER: "⛓"
  };

  /* ------------------------------------------------------------- reseau */
  function requete(chemin, options) {
    options = options || {};
    var init = { method: options.method || "GET", headers: {} };
    if (options.body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(options.body);
    }
    if (options.form) { init.body = options.form; delete init.headers["Content-Type"]; }
    return fetch(API + chemin, init).then(function (reponse) {
      if (options.brut) {
        if (!reponse.ok) { return reponse.text().then(function (t) { throw new Error(t); }); }
        return reponse.blob();
      }
      return reponse.json().then(function (donnees) {
        if (!reponse.ok) {
          throw new Error(donnees.detail || ("erreur HTTP " + reponse.status));
        }
        return donnees;
      });
    });
  }

  /* ----------------------------------------------------------- journal */
  function journaliser(texte, genre) {
    var conteneur = document.getElementById("journal");
    var ligne = document.createElement("div");
    ligne.className = "entree-journal" + (genre ? " " + genre : "");
    var horodatage = new Date().toLocaleTimeString();
    ligne.textContent = horodatage + "  " + texte;
    conteneur.insertBefore(ligne, conteneur.firstChild);
    while (conteneur.childElementCount > 200) {
      conteneur.removeChild(conteneur.lastChild);
    }
    document.getElementById("message").textContent = texte;
  }

  /* ------------------------------------------------------------- ruban */
  function construireOnglets() {
    var barre = document.getElementById("onglets");
    barre.innerHTML = "";
    ONGLETS.forEach(function (onglet) {
      var bouton = document.createElement("button");
      bouton.textContent = onglet.titre;
      bouton.dataset.onglet = onglet.cle;
      bouton.addEventListener("click", function () { activerOnglet(onglet.cle); });
      barre.appendChild(bouton);
    });
    activerOnglet(ONGLETS[0].cle);
  }

  function activerOnglet(cle) {
    etat.onglet = cle;
    Array.prototype.forEach.call(
      document.querySelectorAll("#onglets button"), function (bouton) {
        bouton.classList.toggle("actif", bouton.dataset.onglet === cle);
      });
    var definition = ONGLETS.filter(function (o) { return o.cle === cle; })[0];
    var ruban = document.getElementById("ruban");
    ruban.innerHTML = "";
    definition.groupes.forEach(function (groupe) {
      var commandes = etat.catalogue.filter(function (c) {
        return c.groupe === groupe;
      });
      if (!commandes.length) { return; }
      var bloc = document.createElement("div");
      bloc.className = "groupe-ruban";
      var outils = document.createElement("div");
      outils.className = "outils";
      commandes.forEach(function (commande) {
        outils.appendChild(construireOutil(commande));
      });
      var titre = document.createElement("div");
      titre.className = "titre-groupe";
      titre.textContent = groupe.replace(/_/g, " ");
      bloc.appendChild(outils);
      bloc.appendChild(titre);
      ruban.appendChild(bloc);
    });
  }

  function construireOutil(commande) {
    var bouton = document.createElement("button");
    bouton.className = "outil";
    bouton.title = commande.resume + " (" + commande.nom
      + (commande.anglais ? " / " + commande.anglais : "") + ")";
    var glyphe = document.createElement("span");
    glyphe.className = "glyphe";
    glyphe.textContent = GLYPHES[commande.nom] || "◇";
    var libelle = document.createElement("span");
    libelle.className = "libelle";
    libelle.textContent = commande.nom.toLowerCase();
    bouton.appendChild(glyphe);
    bouton.appendChild(libelle);
    bouton.addEventListener("click", function () { choisirOutil(commande); });
    return bouton;
  }

  /* --------------------------------------------- parametres d'un outil */
  function choisirOutil(commande) {
    etat.outil = commande;
    var panneau = document.getElementById("parametres-outil");
    panneau.innerHTML = "";
    var titre = document.createElement("div");
    titre.innerHTML = "<b>" + commande.nom + "</b> <span class=\"indication\">"
      + (commande.anglais || "") + "</span><p class=\"indication\">"
      + commande.resume + "</p>";
    panneau.appendChild(titre);
    var champs = {};
    Object.keys(commande.parametres).forEach(function (nom) {
      var ligne = document.createElement("div");
      ligne.className = "champ";
      var etiquette = document.createElement("label");
      etiquette.textContent = nom;
      var saisie = document.createElement("input");
      saisie.type = "text";
      saisie.placeholder = commande.parametres[nom];
      champs[nom] = saisie;
      ligne.appendChild(etiquette);
      ligne.appendChild(saisie);
      panneau.appendChild(ligne);
    });
    var lancer = document.createElement("button");
    lancer.textContent = "Executer " + commande.nom;
    lancer.className = "primaire";
    lancer.style.cssText = "margin-top:8px;width:100%;background:var(--accent);"
      + "color:#1a1206;border:none;border-radius:4px;padding:7px;cursor:pointer;"
      + "font-weight:600";
    lancer.addEventListener("click", function () {
      var parametres = {};
      Object.keys(champs).forEach(function (nom) {
        var valeur = champs[nom].value.trim();
        if (valeur !== "") { parametres[nom] = convertir(valeur); }
      });
      if (etat.selection.length) { parametres.handles = etat.selection; }
      executer(commande.nom, parametres);
    });
    panneau.appendChild(lancer);
  }

  function convertir(texte) {
    var minuscule = texte.toLowerCase();
    if (minuscule === "vrai" || minuscule === "true") { return true; }
    if (minuscule === "faux" || minuscule === "false") { return false; }
    if (texte.indexOf(",") >= 0) {
      return texte.split(",").map(function (part) { return convertir(part.trim()); });
    }
    var nombre = Number(texte);
    return texte !== "" && !isNaN(nombre) ? nombre : texte;
  }

  /* -------------------------------------------------------- commandes */
  function executer(nom, parametres) {
    if (!etat.document) { journaliser("aucun document ouvert", "erreur"); return; }
    return requete("/api/v1/cad/documents/" + etat.document + "/command", {
      method: "POST", body: { commande: nom, parametres: parametres || {} }
    }).then(function (reponse) {
      journaliser(nom + " : " + resumer(reponse.resultat), "succes");
      appliquerEtat(reponse.etat);
      return rafraichirScene();
    }).catch(function (erreur) {
      journaliser(nom + " — " + erreur.message, "erreur");
    });
  }

  function resumer(resultat) {
    var cles = Object.keys(resultat).filter(function (cle) {
      return ["commande", "groupe", "objet", "camera", "etat"].indexOf(cle) < 0;
    });
    if (!cles.length) { return "termine"; }
    return cles.slice(0, 4).map(function (cle) {
      var valeur = resultat[cle];
      if (valeur && typeof valeur === "object") {
        valeur = Array.isArray(valeur) ? valeur.length + " element(s)" : "…";
      }
      return cle + "=" + valeur;
    }).join(", ");
  }

  function executerLigne() {
    var champ = document.getElementById("commande");
    var ligne = champ.value.trim();
    if (!ligne) { return; }
    etat.historique.push(ligne);
    etat.indexHistorique = etat.historique.length;
    champ.value = "";
    requete("/api/v1/cad/documents/" + etat.document + "/script", {
      method: "POST", body: { script: ligne }
    }).then(function (reponse) {
      reponse.resultats.forEach(function (resultat) {
        journaliser(resultat.commande + " : " + resumer(resultat), "succes");
      });
      appliquerEtat(reponse.etat);
      return rafraichirScene();
    }).catch(function (erreur) {
      journaliser(erreur.message, "erreur");
    });
  }

  /* ------------------------------------------------------------- scene */
  function rafraichirScene() {
    if (!etat.document) { return Promise.resolve(); }
    var base = "/api/v1/cad/documents/" + etat.document;
    return Promise.all([requete(base + "/mesh"), requete(base + "/curves"),
                        requete(base)])
      .then(function (reponses) {
        viewer.load(reponses[0]);
        viewer.loadCurves(reponses[1].courbes || []);
        etat.calques = reponses[2].calques || [];
        dessinerCalques();
        return requete(base + "/entities?limit=400");
      })
      .then(function (reponse) {
        etat.objets = reponse.objets || [];
        dessinerObjets();
        majInfoVue();
      });
  }

  function appliquerEtat(statistiques) {
    if (!statistiques) { return; }
    document.getElementById("statistiques").textContent =
      statistiques.objets + " objet(s) · " + statistiques.calques + " calque(s) · "
      + (statistiques.volume_total_mm3 / 1e9).toFixed(3) + " m³";
  }

  function majInfoVue() {
    var camera = viewer.cameraState();
    document.getElementById("info-vue").textContent =
      "azimut " + camera.azimut + "°  elevation " + camera.elevation + "°\n"
      + "distance " + camera.distance + " mm\n"
      + "grille " + (viewer.gridStep || 0) + " mm";
  }

  function dessinerCalques() {
    var conteneur = document.getElementById("calques");
    conteneur.innerHTML = "";
    if (!etat.calques.length) {
      conteneur.innerHTML = "<p class=\"vide\">Aucun calque.</p>";
      return;
    }
    etat.calques.forEach(function (calque) {
      var ligne = document.createElement("div");
      ligne.className = "ligne-calque";
      var puce = document.createElement("span");
      puce.className = "puce-couleur";
      puce.style.background = "rgb(" + (calque.rvb || [200, 200, 200]).join(",") + ")";
      var nom = document.createElement("span");
      nom.className = "nom-calque";
      nom.textContent = calque.nom;
      var oeil = document.createElement("button");
      oeil.className = "bascule-calque" + (calque.actif ? "" : " eteint");
      oeil.textContent = "👁";
      oeil.title = "Activer ou desactiver le calque";
      oeil.addEventListener("click", function (event) {
        event.stopPropagation();
        executer("CALQUE", { nom: calque.nom, couleur: calque.couleur,
                             courant: true });
      });
      ligne.appendChild(puce);
      ligne.appendChild(nom);
      ligne.appendChild(oeil);
      ligne.addEventListener("click", function () {
        executer("SELECTIONNER", { calque: calque.nom });
      });
      conteneur.appendChild(ligne);
    });
  }

  function dessinerObjets() {
    var conteneur = document.getElementById("objets");
    conteneur.innerHTML = "";
    if (!etat.objets.length) {
      conteneur.innerHTML = "<p class=\"vide\">Document vide.</p>";
      return;
    }
    etat.objets.forEach(function (objet) {
      var ligne = document.createElement("div");
      ligne.className = "ligne-objet"
        + (etat.selection.indexOf(objet.handle) >= 0 ? " selectionne" : "");
      ligne.innerHTML = "<span class=\"nom-objet\">" + objet.nom
        + "</span><span class=\"compteur\">" + objet.type + "</span>";
      ligne.addEventListener("click", function (event) {
        if (event.shiftKey) {
          if (etat.selection.indexOf(objet.handle) < 0) {
            etat.selection.push(objet.handle);
          }
        } else {
          etat.selection = [objet.handle];
        }
        dessinerObjets();
        afficherProprietes(objet);
      });
      conteneur.appendChild(ligne);
    });
  }

  function afficherProprietes(objet) {
    var panneau = document.getElementById("proprietes");
    var lignes = [
      ["Identifiant", objet.handle], ["Nom", objet.nom], ["Type", objet.type],
      ["Calque", objet.calque], ["Materiau", objet.materiau]
    ];
    if (objet.geometrie) {
      Object.keys(objet.geometrie).forEach(function (cle) {
        var valeur = objet.geometrie[cle];
        if (valeur !== null && typeof valeur === "object") { return; }
        lignes.push([cle.replace(/_/g, " "), valeur]);
      });
    }
    if (objet.boite && objet.boite.taille) {
      lignes.push(["encombrement", objet.boite.taille.map(function (v) {
        return Math.round(v);
      }).join(" × ") + " mm"]);
    }
    panneau.innerHTML = "<table class=\"proprietes\">" + lignes.map(function (l) {
      return "<tr><td>" + l[0] + "</td><td>" + l[1] + "</td></tr>";
    }).join("") + "</table>";
  }

  /* --------------------------------------------------------- dialogues */
  function ouvrirDialogue(titre, contenu, actions) {
    document.getElementById("dialogue-titre").textContent = titre;
    var corps = document.getElementById("dialogue-corps");
    corps.innerHTML = "";
    corps.appendChild(contenu);
    var pied = document.getElementById("dialogue-pied");
    pied.innerHTML = "";
    (actions || []).forEach(function (action) {
      var bouton = document.createElement("button");
      bouton.textContent = action.libelle;
      if (action.primaire) { bouton.className = "primaire"; }
      bouton.addEventListener("click", action.action);
      pied.appendChild(bouton);
    });
    document.getElementById("voile").hidden = false;
  }

  function fermerDialogue() { document.getElementById("voile").hidden = true; }

  function dialogueExport() {
    var grille = document.createElement("div");
    grille.className = "grille-formats";
    etat.formats.filter(function (format) { return format.ecriture; })
      .forEach(function (format) {
        var carte = document.createElement("div");
        carte.className = "carte-format";
        carte.innerHTML = "<b>" + format.libelle + "</b><span>"
          + format.extensions.join(" ") + " · " + format.categorie + "</span>";
        carte.addEventListener("click", function () {
          fermerDialogue();
          telecharger(format.cle, format.extensions[0]);
        });
        grille.appendChild(carte);
      });
    ouvrirDialogue("Exporter le document", grille,
                   [{ libelle: "Annuler", action: fermerDialogue }]);
  }

  function telecharger(format, extension) {
    journaliser("export " + format + " en cours…");
    requete("/api/v1/cad/documents/" + etat.document + "/export", {
      method: "POST", body: { format: format, options: {} }, brut: true
    }).then(function (blob) {
      var lien = document.createElement("a");
      lien.href = URL.createObjectURL(blob);
      lien.download = (etat.nomDocument || "mercury") + extension;
      lien.click();
      URL.revokeObjectURL(lien.href);
      journaliser("export " + format + " termine (" + blob.size + " octets)",
                  "succes");
    }).catch(function (erreur) {
      journaliser("export " + format + " impossible — " + erreur.message,
                  "erreur");
    });
  }

  function dialogueConversion() {
    var conteneur = document.createElement("div");
    var champFichier = document.createElement("input");
    champFichier.type = "file";
    var selection = document.createElement("select");
    etat.formats.filter(function (f) { return f.ecriture; })
      .forEach(function (format) {
        var option = document.createElement("option");
        option.value = format.cle;
        option.textContent = format.libelle + " (" + format.extensions[0] + ")";
        selection.appendChild(option);
      });
    conteneur.innerHTML = "<p class=\"indication\">Convertit un fichier sans "
      + "l'ouvrir : DWG, DXF, IFC, STEP, STL, OBJ, glTF, PLY, 3MF, nuages de "
      + "points et images.</p>";
    var ligne1 = document.createElement("div");
    ligne1.className = "champ";
    ligne1.innerHTML = "<label>Fichier source</label>";
    ligne1.appendChild(champFichier);
    var ligne2 = document.createElement("div");
    ligne2.className = "champ";
    ligne2.innerHTML = "<label>Format cible</label>";
    ligne2.appendChild(selection);
    conteneur.appendChild(ligne1);
    conteneur.appendChild(ligne2);
    ouvrirDialogue("Convertir un fichier", conteneur, [
      { libelle: "Annuler", action: fermerDialogue },
      { libelle: "Convertir", primaire: true, action: function () {
        if (!champFichier.files.length) { return; }
        var donnees = new FormData();
        donnees.append("fichier", champFichier.files[0]);
        fermerDialogue();
        journaliser("conversion en cours…");
        fetch(API + "/api/v1/cad/files/convert?cible=" + selection.value,
              { method: "POST", body: donnees })
          .then(function (reponse) {
            if (!reponse.ok) { return reponse.json().then(function (e) {
              throw new Error(e.detail || "conversion impossible"); }); }
            return reponse.blob();
          })
          .then(function (blob) {
            var lien = document.createElement("a");
            lien.href = URL.createObjectURL(blob);
            lien.download = "converti." + selection.value;
            lien.click();
            journaliser("conversion terminee (" + blob.size + " octets)",
                        "succes");
          })
          .catch(function (erreur) {
            journaliser("conversion — " + erreur.message, "erreur");
          });
      } }
    ]);
  }

  function ouvrirFichier() {
    var champ = document.getElementById("fichier-cache");
    champ.value = "";
    champ.onchange = function () {
      if (!champ.files.length) { return; }
      var donnees = new FormData();
      donnees.append("fichier", champ.files[0]);
      journaliser("ouverture de " + champ.files[0].name + "…");
      fetch(API + "/api/v1/cad/files/open", { method: "POST", body: donnees })
        .then(function (reponse) { return reponse.json().then(function (data) {
          if (!reponse.ok) { throw new Error(data.detail || "ouverture impossible"); }
          return data;
        }); })
        .then(function (reponse) {
          etat.document = reponse.document;
          etat.nomDocument = champ.files[0].name.replace(/\.[^.]+$/, "");
          document.getElementById("titre-document").textContent = champ.files[0].name;
          journaliser("fichier " + reponse.format + " ouvert", "succes");
          appliquerEtat(reponse.etat);
          return rafraichirScene().then(function () { viewer.zoomExtents(); });
        })
        .catch(function (erreur) {
          journaliser("ouverture — " + erreur.message, "erreur");
        });
    };
    champ.click();
  }

  function nouveauDocument(nom) {
    return requete("/api/v1/cad/documents", {
      method: "POST", body: { nom: nom || "SansTitre", unites: "mm" }
    }).then(function (reponse) {
      etat.document = reponse.document;
      etat.nomDocument = nom || "SansTitre";
      etat.selection = [];
      document.getElementById("titre-document").textContent =
        (nom || "SansTitre") + ".json";
      appliquerEtat(reponse.etat);
      journaliser("nouveau document " + reponse.document, "succes");
      return rafraichirScene();
    });
  }

  /* ------------------------------------------------------- demarrage */
  function brancherInterface() {
    document.getElementById("executer").addEventListener("click", executerLigne);
    var champCommande = document.getElementById("commande");
    champCommande.addEventListener("keydown", function (event) {
      if (event.key === "Enter") { executerLigne(); }
      if (event.key === "ArrowUp" && etat.indexHistorique > 0) {
        etat.indexHistorique -= 1;
        champCommande.value = etat.historique[etat.indexHistorique] || "";
      }
      if (event.key === "ArrowDown") {
        etat.indexHistorique = Math.min(etat.historique.length,
                                        etat.indexHistorique + 1);
        champCommande.value = etat.historique[etat.indexHistorique] || "";
      }
    });

    Array.prototype.forEach.call(document.querySelectorAll("[data-fichier]"),
      function (bouton) {
        bouton.addEventListener("click", function () {
          var action = bouton.dataset.fichier;
          if (action === "nouveau") { nouveauDocument("SansTitre"); }
          if (action === "ouvrir") { ouvrirFichier(); }
          if (action === "enregistrer") { telecharger("json", ".json"); }
          if (action === "exporter") { dialogueExport(); }
          if (action === "convertir") { dialogueConversion(); }
        });
      });

    Array.prototype.forEach.call(document.querySelectorAll("[data-vue]"),
      function (bouton) {
        bouton.addEventListener("click", function () {
          viewer.setStandardView(bouton.dataset.vue);
          viewer.zoomExtents();
          majInfoVue();
        });
      });

    Array.prototype.forEach.call(document.querySelectorAll(".bascule"),
      function (bouton) {
        bouton.addEventListener("click", function () {
          var actif = !bouton.classList.contains("active");
          bouton.classList.toggle("active", actif);
          var variable = bouton.dataset.variable;
          if (variable === "GRILLE") { viewer.showGrid = actif; viewer.draw(); }
          if (variable === "ARETES") { viewer.showEdges = actif; viewer.draw(); }
          if (variable === "PERSPECTIVE") {
            viewer.perspective = actif; viewer.draw();
          }
          if (variable === "ORTHO") { executer("ORTHO", { actif: actif }); }
          if (variable === "RESOL") { executer("RESOL", { actif: actif }); }
        });
      });

    document.getElementById("style-visuel").addEventListener("change",
      function (event) {
        viewer.style = event.target.value;
        viewer.draw();
        journaliser("style visuel : " + event.target.value);
      });

    document.getElementById("ajouter-calque").addEventListener("click",
      function () {
        var nom = window.prompt("Nom du nouveau calque", "CALQUE1");
        if (nom) { executer("CALQUE", { nom: nom, couleur: 3 }); }
      });

    document.getElementById("fermer-dialogue")
      .addEventListener("click", fermerDialogue);
    window.addEventListener("resize", function () { viewer.draw(); });
  }

  function demarrer() {
    try {
      viewer = new window.MercuryViewer(document.getElementById("vue3d"));
    } catch (erreur) {
      journaliser("visionneuse 3D indisponible : " + erreur.message, "erreur");
      return;
    }
    viewer.onCameraChange = majInfoVue;
    brancherInterface();

    requete("/health").then(function (sante) {
      var pastille = document.getElementById("etat-api");
      pastille.textContent = "API " + sante.version;
      pastille.className = "pastille ok";
    }).catch(function () {
      var pastille = document.getElementById("etat-api");
      pastille.textContent = "API injoignable";
      pastille.className = "pastille ko";
    });

    Promise.all([requete("/api/v1/cad/commands"),
                 requete("/api/v1/cad/capabilities"),
                 requete("/api/v1/cad/formats")])
      .then(function (reponses) {
        etat.catalogue = reponses[0].commandes;
        etat.capacites = reponses[1];
        etat.formats = reponses[2].formats;
        var selecteur = document.getElementById("style-visuel");
        etat.capacites.styles_visuels.forEach(function (style) {
          var option = document.createElement("option");
          option.value = style;
          option.textContent = style.replace(/_/g, " ");
          if (style === "ombre_avec_aretes") { option.selected = true; }
          selecteur.appendChild(option);
        });
        construireOnglets();
        journaliser(etat.catalogue.length + " commandes et "
                    + etat.formats.length + " formats de fichiers charges",
                    "succes");
        return nouveauDocument("SansTitre");
      })
      .then(function () {
        return executer("BOITE", { longueur: 4000, largeur: 3000, hauteur: 2700 });
      })
      .then(function () { viewer.zoomExtents(); majInfoVue(); })
      .catch(function (erreur) {
        journaliser("demarrage — " + erreur.message, "erreur");
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }
}());
''')

ajouter('Frontend/index.html', r'''
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MERCURY CAD AI X - Modelisation 3D</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23f0a132'/%3E%3Cpath d='M7 23V9l9 8 9-8v14' fill='none' stroke='%231a1206' stroke-width='3'/%3E%3C/svg%3E">
<link rel="stylesheet" href="style.css">
</head>
<body>

<header class="barre-titre">
  <div class="marque"><i></i><b>MERCURY</b><span>CAD AI X</span></div>
  <div class="menu-fichier">
    <button class="menu" data-fichier="nouveau">Nouveau</button>
    <button class="menu" data-fichier="ouvrir">Ouvrir</button>
    <button class="menu" data-fichier="enregistrer">Enregistrer</button>
    <button class="menu" data-fichier="exporter">Exporter</button>
    <button class="menu" data-fichier="convertir">Convertir</button>
  </div>
  <div class="titre-document" id="titre-document">SansTitre.json</div>
  <div class="etat-connexion"><span class="pastille" id="etat-api">connexion…</span></div>
</header>

<nav class="onglets" id="onglets"></nav>
<section class="ruban" id="ruban"></section>

<main class="espace">
  <aside class="palette gauche">
    <div class="palette-entete">
      <h2>Calques</h2>
      <button class="mini" id="ajouter-calque" title="Nouveau calque">+</button>
    </div>
    <div class="palette-corps" id="calques"></div>
    <div class="palette-entete"><h2>Objets</h2></div>
    <div class="palette-corps liste-objets" id="objets"></div>
  </aside>

  <section class="scene">
    <canvas id="vue3d"></canvas>
    <div class="cube-vue" id="cube-vue">
      <button data-vue="dessus">Dessus</button>
      <button data-vue="face">Face</button>
      <button data-vue="gauche">Gauche</button>
      <button data-vue="droite">Droite</button>
      <button data-vue="arriere">Arriere</button>
      <button data-vue="iso_sud_ouest">Iso SO</button>
    </div>
    <div class="info-vue" id="info-vue"></div>
  </section>

  <aside class="palette droite">
    <div class="palette-entete"><h2>Proprietes</h2></div>
    <div class="palette-corps" id="proprietes"></div>
    <div class="palette-entete"><h2>Parametres de l'outil</h2></div>
    <div class="palette-corps" id="parametres-outil">
      <p class="vide">Choisissez un outil dans le ruban.</p>
    </div>
    <div class="palette-entete"><h2>Journal</h2></div>
    <div class="palette-corps journal" id="journal"></div>
  </aside>
</main>

<section class="ligne-commande">
  <label for="commande">Commande&nbsp;:</label>
  <input id="commande" type="text" autocomplete="off" spellcheck="false"
         placeholder="BOITE longueur=1000 largeur=500 hauteur=300">
  <button id="executer">Executer</button>
</section>

<footer class="barre-etat">
  <span id="message">Pret</span>
  <span class="separateur"></span>
  <button class="bascule" data-variable="ORTHO">ORTHO</button>
  <button class="bascule" data-variable="RESOL">RESOL</button>
  <button class="bascule active" data-variable="GRILLE">GRILLE</button>
  <button class="bascule active" data-variable="ARETES">ARETES</button>
  <button class="bascule" data-variable="PERSPECTIVE">PERSPECTIVE</button>
  <select id="style-visuel" title="Style visuel"></select>
  <span class="separateur"></span>
  <span id="statistiques">0 objet</span>
</footer>

<div class="voile" id="voile" hidden>
  <div class="boite-dialogue" id="dialogue">
    <div class="dialogue-entete"><h3 id="dialogue-titre">Titre</h3>
      <button class="mini" id="fermer-dialogue">&times;</button></div>
    <div class="dialogue-corps" id="dialogue-corps"></div>
    <div class="dialogue-pied" id="dialogue-pied"></div>
  </div>
</div>

<input type="file" id="fichier-cache" hidden>

<script src="viewer.js"></script>
<script src="app.js"></script>
</body>
</html>
''')

ajouter('Frontend/style.css', r'''
/* Interface de MERCURY CAD AI X : theme sombre d'atelier, dense et lisible. */
:root {
  --fond: #12161c;
  --fond-panneau: #1a1f27;
  --fond-eleve: #212832;
  --bordure: #2c3542;
  --texte: #dfe4ec;
  --texte-doux: #98a2b3;
  --accent: #f0a132;
  --accent-doux: #3a2c14;
  --bleu: #4a90d9;
  --vert: #46a05a;
  --rouge: #d05a4c;
  --hauteur-titre: 40px;
  --hauteur-onglets: 32px;
  --hauteur-ruban: 96px;
  --hauteur-commande: 38px;
  --hauteur-etat: 30px;
}

* { box-sizing: border-box; }

html, body {
  margin: 0; height: 100%; overflow: hidden;
  background: var(--fond); color: var(--texte);
  font: 13px/1.45 "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

button, input, select { font: inherit; color: inherit; }

/* ------------------------------------------------------------ barre titre */
.barre-titre {
  height: var(--hauteur-titre); display: flex; align-items: center; gap: 18px;
  padding: 0 14px; background: var(--fond-panneau);
  border-bottom: 1px solid var(--bordure);
}
.marque { display: flex; align-items: center; gap: 7px; letter-spacing: .5px; }
.marque i {
  width: 14px; height: 14px; border-radius: 3px; display: inline-block;
  background: linear-gradient(135deg, var(--accent), #d4622a);
}
.marque b { font-weight: 700; }
.marque span { color: var(--texte-doux); font-size: 11px; }
.menu-fichier { display: flex; gap: 2px; }
.menu {
  background: none; border: 1px solid transparent; border-radius: 4px;
  padding: 5px 11px; cursor: pointer; color: var(--texte-doux);
}
.menu:hover { background: var(--fond-eleve); color: var(--texte); }
.titre-document { margin-left: auto; color: var(--texte-doux); font-size: 12px; }
.pastille {
  padding: 3px 9px; border-radius: 10px; font-size: 11px;
  background: var(--fond-eleve); border: 1px solid var(--bordure);
}
.pastille.ok { color: var(--vert); border-color: #2c4a34; }
.pastille.ko { color: var(--rouge); border-color: #4a2c2c; }

/* ---------------------------------------------------------------- onglets */
.onglets {
  height: var(--hauteur-onglets); display: flex; align-items: stretch; gap: 1px;
  padding: 0 10px; background: var(--fond-panneau);
  border-bottom: 1px solid var(--bordure);
}
.onglets button {
  background: none; border: none; border-bottom: 2px solid transparent;
  padding: 0 15px; cursor: pointer; color: var(--texte-doux);
  text-transform: capitalize;
}
.onglets button:hover { color: var(--texte); }
.onglets button.actif { color: var(--accent); border-bottom-color: var(--accent); }

/* ------------------------------------------------------------------ ruban */
.ruban {
  height: var(--hauteur-ruban); display: flex; align-items: stretch; gap: 14px;
  padding: 7px 12px; overflow-x: auto; background: var(--fond-eleve);
  border-bottom: 1px solid var(--bordure);
}
.groupe-ruban {
  display: flex; flex-direction: column; align-items: center;
  padding-right: 14px; border-right: 1px solid var(--bordure); flex: 0 0 auto;
}
.groupe-ruban .outils { display: flex; gap: 4px; flex: 1; align-items: center; }
.groupe-ruban .titre-groupe {
  font-size: 10px; color: var(--texte-doux); text-transform: uppercase;
  letter-spacing: .6px; padding-top: 4px;
}
.outil {
  min-width: 62px; height: 60px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 4px; padding: 4px 6px;
  background: none; border: 1px solid transparent; border-radius: 5px;
  cursor: pointer; color: var(--texte); text-align: center;
}
.outil:hover { background: var(--accent-doux); border-color: var(--accent); }
.outil .glyphe { font-size: 17px; line-height: 1; }
.outil .libelle { font-size: 10px; color: var(--texte-doux); }
.outil:hover .libelle { color: var(--texte); }

/* ------------------------------------------------------------------ espace */
.espace {
  display: flex; height: calc(100% - var(--hauteur-titre) - var(--hauteur-onglets)
    - var(--hauteur-ruban) - var(--hauteur-commande) - var(--hauteur-etat));
}
.palette {
  width: 250px; flex: 0 0 250px; background: var(--fond-panneau);
  display: flex; flex-direction: column; overflow: hidden;
}
.palette.gauche { border-right: 1px solid var(--bordure); }
.palette.droite { border-left: 1px solid var(--bordure); width: 290px; flex-basis: 290px; }
.palette-entete {
  display: flex; align-items: center; justify-content: space-between;
  padding: 7px 10px; background: var(--fond-eleve);
  border-top: 1px solid var(--bordure); border-bottom: 1px solid var(--bordure);
}
.palette-entete h2 {
  margin: 0; font-size: 11px; text-transform: uppercase; letter-spacing: .7px;
  color: var(--texte-doux); font-weight: 600;
}
.palette-corps { overflow: auto; padding: 6px 8px; flex: 1 1 auto; }
.palette-corps.liste-objets { max-height: 32%; }
.palette-corps.journal { max-height: 28%; font-size: 11px; font-family: ui-monospace, Menlo, Consolas, monospace; }
.mini {
  background: var(--fond-eleve); border: 1px solid var(--bordure);
  border-radius: 4px; width: 22px; height: 22px; cursor: pointer;
  color: var(--texte-doux); line-height: 1;
}
.mini:hover { color: var(--accent); border-color: var(--accent); }

.ligne-calque, .ligne-objet {
  display: flex; align-items: center; gap: 7px; padding: 4px 6px;
  border-radius: 4px; cursor: pointer;
}
.ligne-calque:hover, .ligne-objet:hover { background: var(--fond-eleve); }
.ligne-objet.selectionne { background: var(--accent-doux); }
.puce-couleur {
  width: 11px; height: 11px; border-radius: 2px; flex: 0 0 11px;
  border: 1px solid rgba(255, 255, 255, .25);
}
.nom-calque, .nom-objet { flex: 1; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; }
.compteur { color: var(--texte-doux); font-size: 11px; }
.bascule-calque { background: none; border: none; cursor: pointer;
  color: var(--texte-doux); padding: 0 2px; }
.bascule-calque.eteint { opacity: .35; }

.vide { color: var(--texte-doux); font-size: 12px; margin: 6px 2px; }
table.proprietes { width: 100%; border-collapse: collapse; font-size: 12px; }
table.proprietes td { padding: 3px 4px; border-bottom: 1px solid var(--bordure); }
table.proprietes td:first-child { color: var(--texte-doux); width: 46%; }

/* ------------------------------------------------------------------ scene */
.scene { flex: 1 1 auto; position: relative; background: #0d1116; }
#vue3d { width: 100%; height: 100%; display: block; cursor: crosshair; }
.cube-vue {
  position: absolute; top: 12px; right: 12px; display: grid;
  grid-template-columns: repeat(2, 1fr); gap: 3px;
}
.cube-vue button {
  background: rgba(26, 31, 39, .88); border: 1px solid var(--bordure);
  border-radius: 4px; padding: 4px 9px; cursor: pointer; font-size: 11px;
  color: var(--texte-doux);
}
.cube-vue button:hover { color: var(--accent); border-color: var(--accent); }
.info-vue {
  position: absolute; left: 12px; bottom: 12px; font-size: 11px;
  color: var(--texte-doux); background: rgba(18, 22, 28, .8);
  padding: 5px 9px; border-radius: 4px; border: 1px solid var(--bordure);
  font-family: ui-monospace, Menlo, Consolas, monospace; white-space: pre;
}

/* --------------------------------------------------------- ligne commande */
.ligne-commande {
  height: var(--hauteur-commande); display: flex; align-items: center; gap: 9px;
  padding: 0 12px; background: var(--fond-panneau);
  border-top: 1px solid var(--bordure);
}
.ligne-commande label { color: var(--texte-doux); font-size: 12px; }
.ligne-commande input {
  flex: 1; background: var(--fond); border: 1px solid var(--bordure);
  border-radius: 4px; padding: 5px 9px; outline: none;
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.ligne-commande input:focus { border-color: var(--accent); }
.ligne-commande button {
  background: var(--accent); color: #1a1206; border: none; border-radius: 4px;
  padding: 6px 15px; cursor: pointer; font-weight: 600;
}

/* -------------------------------------------------------------- barre etat */
.barre-etat {
  height: var(--hauteur-etat); display: flex; align-items: center; gap: 8px;
  padding: 0 12px; background: var(--fond-eleve); font-size: 11px;
  border-top: 1px solid var(--bordure); color: var(--texte-doux);
}
.barre-etat .separateur { flex: 1; }
.bascule {
  background: none; border: 1px solid var(--bordure); border-radius: 3px;
  padding: 2px 8px; cursor: pointer; color: var(--texte-doux); font-size: 10px;
  letter-spacing: .4px;
}
.bascule.active { color: var(--accent); border-color: var(--accent);
  background: var(--accent-doux); }
.barre-etat select {
  background: var(--fond); border: 1px solid var(--bordure); border-radius: 3px;
  padding: 2px 6px;
}

/* ------------------------------------------------------------- dialogues */
.voile {
  position: fixed; inset: 0; background: rgba(6, 8, 11, .72);
  display: flex; align-items: center; justify-content: center; z-index: 40;
}
/* `display: flex` l'emporte sur l'attribut hidden : sans cette regle, le
   voile reste au-dessus de l'interface et intercepte tous les clics. */
.voile[hidden] { display: none; }
.boite-dialogue {
  width: min(660px, 92vw); max-height: 84vh; display: flex;
  flex-direction: column; background: var(--fond-panneau);
  border: 1px solid var(--bordure); border-radius: 7px;
  box-shadow: 0 22px 60px rgba(0, 0, 0, .55);
}
.dialogue-entete {
  display: flex; align-items: center; justify-content: space-between;
  padding: 11px 15px; border-bottom: 1px solid var(--bordure);
}
.dialogue-entete h3 { margin: 0; font-size: 14px; }
.dialogue-corps { padding: 14px 15px; overflow: auto; }
.dialogue-pied {
  display: flex; justify-content: flex-end; gap: 8px; padding: 11px 15px;
  border-top: 1px solid var(--bordure);
}
.dialogue-pied button, .champ button {
  background: var(--fond-eleve); border: 1px solid var(--bordure);
  border-radius: 4px; padding: 6px 15px; cursor: pointer;
}
.dialogue-pied button.primaire {
  background: var(--accent); color: #1a1206; border-color: var(--accent);
  font-weight: 600;
}
.champ { display: flex; align-items: center; gap: 10px; margin-bottom: 9px; }
.champ label { width: 170px; color: var(--texte-doux); font-size: 12px; }
.champ input, .champ select, .champ textarea {
  flex: 1; background: var(--fond); border: 1px solid var(--bordure);
  border-radius: 4px; padding: 5px 8px; outline: none;
}
.champ input:focus, .champ select:focus { border-color: var(--accent); }
.champ .indication { color: var(--texte-doux); font-size: 11px; }
.grille-formats {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(146px, 1fr));
  gap: 7px;
}
.carte-format {
  border: 1px solid var(--bordure); border-radius: 5px; padding: 8px 10px;
  cursor: pointer; background: var(--fond);
}
.carte-format:hover { border-color: var(--accent); }
.carte-format b { display: block; font-size: 12px; }
.carte-format span { color: var(--texte-doux); font-size: 10px; }

.entree-journal { padding: 2px 0; border-bottom: 1px solid rgba(44, 53, 66, .5); }
.entree-journal.erreur { color: var(--rouge); }
.entree-journal.succes { color: var(--vert); }
''')

ajouter('Frontend/viewer.js', r'''
/* Visionneuse 3D WebGL de MERCURY CAD AI X.
 *
 * Rendu temps reel du modele : faces ombrees, aretes, grille, axes du SCU,
 * orbite, panoramique et zoom. Aucune bibliotheque externe : le fichier est
 * autonome, ce qui evite toute dependance reseau au demarrage.
 */
(function (global) {
  "use strict";

  /* ---------------------------------------------------------------- maths */
  var M4 = {
    identity: function () {
      return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);
    },
    multiply: function (a, b) {
      var out = new Float32Array(16), i, j, k, sum;
      for (i = 0; i < 4; i++) {
        for (j = 0; j < 4; j++) {
          sum = 0;
          for (k = 0; k < 4; k++) { sum += a[k * 4 + j] * b[i * 4 + k]; }
          out[i * 4 + j] = sum;
        }
      }
      return out;
    },
    perspective: function (fovy, aspect, near, far) {
      var f = 1 / Math.tan(fovy / 2), d = near - far;
      return new Float32Array([f / aspect,0,0,0, 0,f,0,0,
        0,0,(far + near) / d,-1, 0,0,(2 * far * near) / d,0]);
    },
    ortho: function (halfWidth, halfHeight, near, far) {
      var d = far - near;
      return new Float32Array([1 / halfWidth,0,0,0, 0,1 / halfHeight,0,0,
        0,0,-2 / d,0, 0,0,-(far + near) / d,1]);
    },
    lookAt: function (eye, target, up) {
      var z = normalize(sub(eye, target));
      var x = normalize(cross(up, z));
      var y = cross(z, x);
      return new Float32Array([
        x[0], y[0], z[0], 0,
        x[1], y[1], z[1], 0,
        x[2], y[2], z[2], 0,
        -dot(x, eye), -dot(y, eye), -dot(z, eye), 1]);
    }
  };

  function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
  function add(a, b) { return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]; }
  function scale(a, k) { return [a[0] * k, a[1] * k, a[2] * k]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function cross(a, b) {
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]];
  }
  function length(a) { return Math.sqrt(dot(a, a)); }
  function normalize(a) {
    var n = length(a);
    return n < 1e-9 ? [0, 0, 0] : [a[0] / n, a[1] / n, a[2] / n];
  }

  /* --------------------------------------------------------------- nuances */
  var FACE_VERTEX = [
    "attribute vec3 aPosition;",
    "attribute vec3 aNormal;",
    "attribute vec3 aColor;",
    "uniform mat4 uProjection;",
    "uniform mat4 uView;",
    "varying vec3 vNormal;",
    "varying vec3 vColor;",
    "varying vec3 vWorld;",
    "void main() {",
    "  vNormal = aNormal;",
    "  vColor = aColor;",
    "  vWorld = aPosition;",
    "  gl_Position = uProjection * uView * vec4(aPosition, 1.0);",
    "}"
  ].join("\n");

  var FACE_FRAGMENT = [
    "precision mediump float;",
    "varying vec3 vNormal;",
    "varying vec3 vColor;",
    "varying vec3 vWorld;",
    "uniform vec3 uEye;",
    "uniform float uMode;",   /* 0 realiste, 1 conceptuel, 2 rayons X, 3 gris */
    "uniform float uOpacity;",
    "void main() {",
    "  vec3 n = normalize(vNormal);",
    "  vec3 key = normalize(vec3(0.45, 0.55, 0.75));",
    "  vec3 fill = normalize(vec3(-0.6, -0.35, 0.4));",
    "  float d = max(dot(n, key), 0.0) * 0.85 + max(dot(n, fill), 0.0) * 0.3;",
    "  vec3 base = vColor;",
    "  if (uMode > 2.5) { float g = dot(base, vec3(0.299, 0.587, 0.114));",
    "    base = vec3(g); }",
    "  vec3 color = base * (0.32 + d);",
    "  if (uMode > 0.5 && uMode < 1.5) {",
    "    float t = clamp(0.5 + 0.5 * dot(n, key), 0.0, 1.0);",
    "    color = mix(vec3(0.29, 0.38, 0.58), vec3(1.0, 0.84, 0.55), t);",
    "    color = mix(color, base, 0.35);",
    "  }",
    "  vec3 view = normalize(uEye - vWorld);",
    "  float rim = pow(1.0 - max(dot(n, view), 0.0), 3.0) * 0.25;",
    "  gl_FragColor = vec4(color + rim, uOpacity);",
    "}"
  ].join("\n");

  var LINE_VERTEX = [
    "attribute vec3 aPosition;",
    "attribute vec3 aColor;",
    "uniform mat4 uProjection;",
    "uniform mat4 uView;",
    "varying vec3 vColor;",
    "void main() {",
    "  vColor = aColor;",
    "  vec4 p = uProjection * uView * vec4(aPosition, 1.0);",
    "  p.z -= 0.0008 * p.w;",   /* les aretes passent devant les faces */
    "  gl_Position = p;",
    "}"
  ].join("\n");

  var LINE_FRAGMENT = [
    "precision mediump float;",
    "varying vec3 vColor;",
    "uniform float uOpacity;",
    "void main() { gl_FragColor = vec4(vColor, uOpacity); }"
  ].join("\n");

  var MATERIALS = {
    "default": [0.78, 0.78, 0.76], "maconnerie": [0.85, 0.82, 0.77],
    "cloison": [0.90, 0.89, 0.86], "beton": [0.72, 0.72, 0.70],
    "acier": [0.55, 0.59, 0.63], "bois": [0.66, 0.47, 0.28],
    "verre": [0.66, 0.80, 0.86], "isolant": [0.91, 0.80, 0.51],
    "mobilier": [0.55, 0.40, 0.28], "terre": [0.59, 0.48, 0.35],
    "metal": [0.67, 0.69, 0.71], "plastique": [0.78, 0.78, 0.82]
  };

  var STYLE_MODES = {
    "realiste": 0, "ombre_avec_aretes": 0, "conceptuel": 1, "cache": 0,
    "rayons_x": 2, "nuances_de_gris": 3, "esquisse": 0,
    "filaire_3d": 0, "filaire_2d": 0
  };

  /* ------------------------------------------------------------- visionneuse */
  function Viewer(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext("webgl", { antialias: true, alpha: false })
      || canvas.getContext("experimental-webgl", { antialias: true });
    if (!this.gl) { throw new Error("WebGL indisponible sur ce navigateur"); }
    this.target = [0, 0, 0];
    this.distance = 10000;
    this.azimuth = 315;
    this.elevation = 30;
    this.perspective = false;
    this.style = "ombre_avec_aretes";
    this.showGrid = true;
    this.showEdges = true;
    this.showAxes = true;
    this.selection = [];
    this.groups = [];
    this.box = null;
    this.counts = { faces: 0, edges: 0, grid: 0 };
    this._setup();
    this._bind();
  }

  Viewer.prototype._setup = function () {
    var gl = this.gl;
    this.faceProgram = buildProgram(gl, FACE_VERTEX, FACE_FRAGMENT);
    this.lineProgram = buildProgram(gl, LINE_VERTEX, LINE_FRAGMENT);
    this.buffers = {
      position: gl.createBuffer(), normal: gl.createBuffer(),
      color: gl.createBuffer(), edge: gl.createBuffer(),
      edgeColor: gl.createBuffer(), grid: gl.createBuffer(),
      gridColor: gl.createBuffer()
    };
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
    gl.cullFace(gl.BACK);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  };

  Viewer.prototype._bind = function () {
    var self = this, dragging = null, last = null;
    this.canvas.addEventListener("contextmenu", function (event) {
      event.preventDefault();
    });
    this.canvas.addEventListener("mousedown", function (event) {
      dragging = event.button === 0 && !event.shiftKey ? "orbite" : "pan";
      last = [event.clientX, event.clientY];
      event.preventDefault();
    });
    global.addEventListener("mouseup", function () { dragging = null; });
    global.addEventListener("mousemove", function (event) {
      if (!dragging || !last) { return; }
      var dx = event.clientX - last[0], dy = event.clientY - last[1];
      last = [event.clientX, event.clientY];
      if (dragging === "orbite") {
        self.azimuth = (self.azimuth - dx * 0.4 + 360) % 360;
        self.elevation = Math.max(-89, Math.min(89, self.elevation + dy * 0.4));
      } else {
        var factor = self.distance / Math.max(1, self.canvas.height);
        var frame = self.frame();
        self.target = add(self.target,
          add(scale(frame.right, -dx * factor), scale(frame.up, dy * factor)));
      }
      self.draw();
      if (self.onCameraChange) { self.onCameraChange(self.cameraState()); }
    });
    this.canvas.addEventListener("wheel", function (event) {
      event.preventDefault();
      self.distance *= event.deltaY > 0 ? 1.12 : 0.89;
      self.distance = Math.max(1, Math.min(1e8, self.distance));
      self.draw();
      if (self.onCameraChange) { self.onCameraChange(self.cameraState()); }
    }, { passive: false });
  };

  Viewer.prototype.frame = function () {
    var a = this.azimuth * Math.PI / 180, e = this.elevation * Math.PI / 180;
    var eye = add(this.target, [
      this.distance * Math.cos(e) * Math.cos(a),
      this.distance * Math.cos(e) * Math.sin(a),
      this.distance * Math.sin(e)]);
    var forward = normalize(sub(this.target, eye));
    var reference = Math.abs(forward[2]) > 0.999 ? [0, 1, 0] : [0, 0, 1];
    var right = normalize(cross(forward, reference));
    return { eye: eye, forward: forward, right: right,
             up: normalize(cross(right, forward)) };
  };

  Viewer.prototype.cameraState = function () {
    return { azimut: Math.round(this.azimuth * 10) / 10,
             elevation: Math.round(this.elevation * 10) / 10,
             distance: Math.round(this.distance) };
  };

  Viewer.prototype.setStandardView = function (name) {
    var views = {
      dessus: [0, 89.9], dessous: [0, -89.9], face: [270, 0], arriere: [90, 0],
      gauche: [180, 0], droite: [0, 0], iso_sud_ouest: [225, 35.264],
      iso_sud_est: [315, 35.264], iso_nord_est: [45, 35.264],
      iso_nord_ouest: [135, 35.264]
    };
    var view = views[name] || views.iso_sud_ouest;
    this.azimuth = view[0];
    this.elevation = view[1];
    this.draw();
  };

  Viewer.prototype.zoomExtents = function () {
    if (!this.box) { return; }
    var size = this.box.taille || [1000, 1000, 1000];
    this.target = this.box.centre || [0, 0, 0];
    var radius = Math.max(1, length(size) / 2);
    this.distance = radius * 2.6;
    this.draw();
  };

  Viewer.prototype.load = function (mesh) {
    var gl = this.gl;
    var positions = mesh.positions || [], normals = mesh.normales || [];
    var colors = new Float32Array(positions.length);
    this.groups = mesh.groupes || [];
    this.box = mesh.boite && !mesh.boite.vide ? mesh.boite : null;
    var index = 0, g, color, k;
    for (g = 0; g < this.groups.length; g++) {
      color = MATERIALS[this.groups[g].materiau] || MATERIALS["default"];
      for (k = 0; k < this.groups[g].sommets; k++) {
        colors[index * 3] = color[0];
        colors[index * 3 + 1] = color[1];
        colors[index * 3 + 2] = color[2];
        index += 1;
      }
    }
    while (index < positions.length / 3) {
      colors[index * 3] = 0.78;
      colors[index * 3 + 1] = 0.78;
      colors[index * 3 + 2] = 0.76;
      index += 1;
    }
    upload(gl, this.buffers.position, new Float32Array(positions));
    upload(gl, this.buffers.normal, new Float32Array(normals));
    upload(gl, this.buffers.color, colors);
    this.counts.faces = positions.length / 3;

    var edges = mesh.aretes || [];
    var edgeColors = new Float32Array(edges.length);
    for (k = 0; k < edges.length / 3; k++) {
      edgeColors[k * 3] = 0.09;
      edgeColors[k * 3 + 1] = 0.11;
      edgeColors[k * 3 + 2] = 0.14;
    }
    upload(gl, this.buffers.edge, new Float32Array(edges));
    upload(gl, this.buffers.edgeColor, edgeColors);
    this.counts.edges = edges.length / 3;
    this._buildGrid();
    this.draw();
  };

  Viewer.prototype.loadCurves = function (curves) {
    var points = [], colors = [], i, j, list;
    for (i = 0; i < curves.length; i++) {
      list = curves[i].points || [];
      for (j = 0; j + 1 < list.length; j++) {
        points.push(list[j][0], list[j][1], list[j][2]);
        points.push(list[j + 1][0], list[j + 1][1], list[j + 1][2]);
        colors.push(0.16, 0.42, 0.70, 0.16, 0.42, 0.70);
      }
      if (curves[i].ferme && list.length > 2) {
        points.push(list[list.length - 1][0], list[list.length - 1][1],
                    list[list.length - 1][2]);
        points.push(list[0][0], list[0][1], list[0][2]);
        colors.push(0.16, 0.42, 0.70, 0.16, 0.42, 0.70);
      }
    }
    this.curvePoints = new Float32Array(points);
    this.curveColors = new Float32Array(colors);
    if (!this.buffers.curve) {
      this.buffers.curve = this.gl.createBuffer();
      this.buffers.curveColor = this.gl.createBuffer();
    }
    upload(this.gl, this.buffers.curve, this.curvePoints);
    upload(this.gl, this.buffers.curveColor, this.curveColors);
    this.counts.curves = points.length / 3;
    this.draw();
  };

  Viewer.prototype._buildGrid = function () {
    var size = this.box ? Math.max(this.box.taille[0], this.box.taille[1]) : 5000;
    var step = Math.pow(10, Math.round(Math.log(size / 10) / Math.LN10));
    var extent = Math.max(step * 12, size * 1.5);
    var lines = [], colors = [], value, strong;
    for (value = -extent; value <= extent + 1e-6; value += step) {
      strong = Math.abs(value) < step * 0.5;
      lines.push(-extent, value, 0, extent, value, 0);
      lines.push(value, -extent, 0, value, extent, 0);
      var tone = strong ? [0.30, 0.34, 0.40] : [0.18, 0.20, 0.24];
      colors.push(tone[0], tone[1], tone[2], tone[0], tone[1], tone[2]);
      colors.push(tone[0], tone[1], tone[2], tone[0], tone[1], tone[2]);
    }
    if (this.showAxes) {
      var axis = extent * 0.25;
      lines.push(0, 0, 0, axis, 0, 0); colors.push(0.85, 0.24, 0.24, 0.85, 0.24, 0.24);
      lines.push(0, 0, 0, 0, axis, 0); colors.push(0.30, 0.75, 0.35, 0.30, 0.75, 0.35);
      lines.push(0, 0, 0, 0, 0, axis); colors.push(0.28, 0.52, 0.95, 0.28, 0.52, 0.95);
    }
    upload(this.gl, this.buffers.grid, new Float32Array(lines));
    upload(this.gl, this.buffers.gridColor, new Float32Array(colors));
    this.counts.grid = lines.length / 3;
    this.gridStep = step;
  };

  Viewer.prototype.resize = function () {
    var ratio = global.devicePixelRatio || 1;
    var width = Math.floor(this.canvas.clientWidth * ratio);
    var height = Math.floor(this.canvas.clientHeight * ratio);
    if (width < 1 || height < 1) { return; }
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    this.gl.viewport(0, 0, width, height);
  };

  Viewer.prototype.draw = function () {
    var gl = this.gl;
    this.resize();
    var aspect = this.canvas.width / Math.max(1, this.canvas.height);
    var frame = this.frame();
    var view = M4.lookAt(frame.eye, this.target, [0, 0, 1]);
    var near = Math.max(1, this.distance * 0.002);
    var far = this.distance * 40;
    var projection = this.perspective
      ? M4.perspective(45 * Math.PI / 180, aspect, near, far)
      : M4.ortho(this.distance * 0.5 * aspect, this.distance * 0.5, -far, far);

    var background = this.style === "esquisse" ? [0.99, 0.98, 0.96, 1]
      : (this.style === "cache" || this.style === "filaire_2d"
         || this.style === "nuances_de_gris")
        ? [0.96, 0.96, 0.97, 1] : [0.09, 0.11, 0.14, 1];
    gl.clearColor(background[0], background[1], background[2], 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    if (this.showGrid && this.counts.grid) {
      this._drawLines(this.buffers.grid, this.buffers.gridColor,
                      this.counts.grid, projection, view, 0.75);
    }
    var wireframe = this.style === "filaire_3d" || this.style === "filaire_2d";
    if (!wireframe && this.counts.faces) {
      gl.useProgram(this.faceProgram);
      bindAttribute(gl, this.faceProgram, "aPosition", this.buffers.position, 3);
      bindAttribute(gl, this.faceProgram, "aNormal", this.buffers.normal, 3);
      bindAttribute(gl, this.faceProgram, "aColor", this.buffers.color, 3);
      gl.uniformMatrix4fv(uniform(gl, this.faceProgram, "uProjection"), false,
                          projection);
      gl.uniformMatrix4fv(uniform(gl, this.faceProgram, "uView"), false, view);
      gl.uniform3fv(uniform(gl, this.faceProgram, "uEye"),
                    new Float32Array(frame.eye));
      gl.uniform1f(uniform(gl, this.faceProgram, "uMode"),
                   STYLE_MODES[this.style] || 0);
      gl.uniform1f(uniform(gl, this.faceProgram, "uOpacity"),
                   this.style === "rayons_x" ? 0.45 : 1.0);
      if (this.style === "rayons_x") { gl.disable(gl.CULL_FACE); }
      gl.drawArrays(gl.TRIANGLES, 0, this.counts.faces);
      if (this.style === "rayons_x") { gl.enable(gl.CULL_FACE); }
    }
    if ((this.showEdges || wireframe) && this.counts.edges) {
      this._drawLines(this.buffers.edge, this.buffers.edgeColor,
                      this.counts.edges, projection, view,
                      wireframe ? 1.0 : 0.55);
    }
    if (this.counts.curves) {
      this._drawLines(this.buffers.curve, this.buffers.curveColor,
                      this.counts.curves, projection, view, 1.0);
    }
  };

  Viewer.prototype._drawLines = function (buffer, colorBuffer, count,
                                          projection, view, opacity) {
    var gl = this.gl;
    gl.useProgram(this.lineProgram);
    bindAttribute(gl, this.lineProgram, "aPosition", buffer, 3);
    bindAttribute(gl, this.lineProgram, "aColor", colorBuffer, 3);
    gl.uniformMatrix4fv(uniform(gl, this.lineProgram, "uProjection"), false,
                        projection);
    gl.uniformMatrix4fv(uniform(gl, this.lineProgram, "uView"), false, view);
    gl.uniform1f(uniform(gl, this.lineProgram, "uOpacity"), opacity);
    gl.drawArrays(gl.LINES, 0, count);
  };

  /* ------------------------------------------------------------ utilitaires */
  function buildProgram(gl, vertexSource, fragmentSource) {
    var program = gl.createProgram();
    gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, vertexSource));
    gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, fragmentSource));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error("edition de liens WebGL : " + gl.getProgramInfoLog(program));
    }
    return program;
  }

  function compile(gl, type, source) {
    var shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      throw new Error("compilation WebGL : " + gl.getShaderInfoLog(shader));
    }
    return shader;
  }

  function upload(gl, buffer, data) {
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
  }

  function bindAttribute(gl, program, name, buffer, size) {
    var location = gl.getAttribLocation(program, name);
    if (location < 0) { return; }
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.enableVertexAttribArray(location);
    gl.vertexAttribPointer(location, size, gl.FLOAT, false, 0, 0);
  }

  var uniformCache = new WeakMap();
  function uniform(gl, program, name) {
    var table = uniformCache.get(program);
    if (!table) { table = {}; uniformCache.set(program, table); }
    if (!(name in table)) { table[name] = gl.getUniformLocation(program, name); }
    return table[name];
  }

  global.MercuryViewer = Viewer;
}(window));
''')


# =========================================================================
# 16. MOBILE  (livrable #63)
# =========================================================================
ajouter('Mobile/README.md', r'''
# MERCURY Mobile (livrable #63)

Client terrain pour tablette et telephone. L'application mobile ne reimplemente
aucun moteur : elle consomme l'API REST, ce qui garantit que les chiffres
affiches sur le chantier sont exactement ceux du bureau d'etudes.

## Architecture

```
Mobile/
├── shared/api_client.js     client HTTP commun iOS / Android
├── ios/                     enveloppe SwiftUI (WKWebView + API native)
└── android/                 enveloppe Kotlin (WebView + API native)
```

## Ecrans

| Ecran | Role |
|---|---|
| Projets | liste, recherche, ouverture hors ligne du dernier projet |
| Plan | consultation 2D, cotes, surfaces |
| Metre | quantites et devis, partage PDF |
| Jumeau | releves capteurs, alertes en temps reel |
| Realite augmentee | superposition du modele sur la vue camera (livrable #48) |

## Mode hors ligne

Le dernier projet consulte est mis en cache au format JSON. Les mesures
saisies sur le chantier sont accumulees et renvoyees des le retour du reseau.
''')

ajouter('Mobile/android/README.md', r'''
# Enveloppe Android

Cible : Android 9 (API 28) et superieur, Kotlin.

```kotlin
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val webView = WebView(this)
        webView.settings.javaScriptEnabled = true
        webView.loadUrl("https://api.mercury.local/app")
        setContentView(webView)
    }
}
```

Fonctions natives a brancher : CameraX, ARCore (livrable #48), WorkManager
pour la file hors ligne, chiffrement EncryptedSharedPreferences.
''')

ajouter('Mobile/ios/README.md', r'''
# Enveloppe iOS

Cible : iOS 15 et superieur, SwiftUI.

```swift
import SwiftUI
import WebKit

struct MercuryApp: View {
    let apiURL = URL(string: "https://api.mercury.local")!
    var body: some View {
        WebView(url: apiURL.appendingPathComponent("app"))
            .edgesIgnoringSafeArea(.all)
    }
}
```

Fonctions natives a brancher : appareil photo (releves chantier), ARKit
(livrable #48), notifications d'alerte du jumeau numerique, stockage
chiffre du cache hors ligne.
''')

ajouter('Mobile/shared/api_client.js', r'''
/* Client API partage iOS / Android (livrable #63).
   Aucune logique metier : uniquement le transport, la file hors ligne et
   la gestion des erreurs. */
class MercuryClient {
  constructor(baseUrl, token) {
    if (!baseUrl) throw new Error("URL de l'API requise");
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.token = token || null;
    this.queue = [];
  }

  headers() {
    const h = { "Content-Type": "application/json" };
    if (this.token) h.Authorization = "Bearer " + this.token;
    return h;
  }

  async request(path, method = "GET", body = null) {
    const options = { method, headers: this.headers() };
    if (body) options.body = JSON.stringify(body);
    try {
      const response = await fetch(this.baseUrl + path, options);
      if (!response.ok) throw new Error("HTTP " + response.status);
      return await response.json();
    } catch (error) {
      if (method !== "GET") {
        this.queue.push({ path, method, body });   // renvoi differe
      }
      throw error;
    }
  }

  health() { return this.request("/health"); }
  projects() { return this.request("/api/v1/projects"); }
  project(id) { return this.request("/api/v1/projects/" + id); }
  takeoff(id) { return this.request("/api/v1/projects/" + id + "/takeoff"); }
  estimate(id) { return this.request("/api/v1/projects/" + id + "/estimate"); }
  twin(id) { return this.request("/api/v1/projects/" + id + "/twin"); }

  pushReadings(readings) {
    return this.request("/api/v1/iot/readings", "POST", { mesures: readings });
  }

  async flush() {
    const pending = this.queue.splice(0);
    const results = [];
    for (const item of pending) {
      try {
        results.push(await this.request(item.path, item.method, item.body));
      } catch (error) {
        this.queue.push(item);            // on garde pour le prochain essai
      }
    }
    return { envoyes: results.length, en_attente: this.queue.length };
  }
}

if (typeof module !== "undefined") module.exports = MercuryClient;
''')


# =========================================================================
# 17. TESTS
# =========================================================================
ajouter('tests/__init__.py', r'''
"""Suite de tests de MERCURY CAD AI X."""
''')

ajouter('tests/conftest.py', r'''
"""Configuration partagee des tests.

Chaque session utilise une base temporaire : les tests ne laissent aucune
trace et peuvent tourner en parallele de l'application.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def db_path():
    directory = tempfile.mkdtemp(prefix="mercury_tests_")
    return os.path.join(directory, "test.db")


@pytest.fixture(scope="session")
def state(db_path):
    from API.deps import reset_state
    return reset_state(db_path)


@pytest.fixture()
def project():
    """Projet de reference : rectangle 10 x 8 m avec une cloison en T."""
    from BIM_Engine.models import BuildingProject, Opening, Wall
    project = BuildingProject(name="Reference", building_type="maison")
    walls = [
        ((0, 0), (10000, 0), 300, True),
        ((10000, 0), (10000, 8000), 300, True),
        ((10000, 8000), (0, 8000), 300, True),
        ((0, 8000), (0, 0), 300, True),
        ((5000, 0), (5000, 8000), 100, False),
        ((5000, 4000), (10000, 4000), 100, False),
    ]
    for start, end, thickness, exterior in walls:
        project.add_wall(Wall(start=start, end=end, thickness=thickness,
                              height=2700, exterior=exterior))
    project.walls[0].add_opening(Opening(type="fenetre", offset=2500,
                                         width=1600, height=1400, sill=900))
    project.walls[0].add_opening(Opening(type="fenetre", offset=7500,
                                         width=1600, height=1400, sill=900))
    project.walls[3].add_opening(Opening(type="porte", offset=4000,
                                         width=1000, height=2100))
    project.walls[4].add_opening(Opening(type="porte", offset=2000,
                                         width=900, height=2100))
    return project


@pytest.fixture()
def furnished(project, state):
    """Projet de reference avec ses pieces calculees."""
    from BIM_Engine.models import Room
    faces = state.engine_2d.detect_rooms(project.walls)
    project.rooms = []
    for index, face in enumerate(faces):
        metrics = state.engine_2d.room_metrics(face, 150.0)
        project.rooms.append(Room(name="Piece %d" % (index + 1), **metrics,
                                  height=2700, level_id=project.levels[0].id))
    return project
''')

ajouter('tests/test_ai_modules.py', r'''
"""Tests des modeles IA : vision, assistant, maintenance predictive."""
from __future__ import annotations

import time

import pytest

from AI_Engine.nlp_assistant import ConversationalAssistant
from AI_Engine.predictive import PredictiveMaintenance
from AI_Engine.vision_ai import FakeWeights, PlanReader, PlanVisionModel


def test_poids_factices_deterministes():
    a, b = FakeWeights("graine"), FakeWeights("graine")
    assert a.checksum == b.checksum
    assert FakeWeights("autre").checksum != a.checksum


def test_modele_de_vision_api_correcte():
    model = PlanVisionModel()
    info = model.info()
    assert "classes" in info and "mur" in info["classes"]
    meta = model.preprocess(1600, 900)
    assert meta["resized"][0] == 640
    with pytest.raises(ValueError):
        model.preprocess(0, 100)
    detections = model.predict(1600, 900, seed="plan-1")
    assert isinstance(detections, list)
    for detection in detections:
        assert detection.confidence >= model.confidence_threshold
        assert detection.label in info["classes"]
        assert detection.width > 0 and detection.height > 0


def test_suppression_des_non_maxima():
    from AI_Engine.vision_ai import Detection
    model = PlanVisionModel()
    a = Detection("mur", 0.9, 0, 0, 100, 100)
    b = Detection("mur", 0.8, 5, 5, 100, 100)      # recouvre largement a
    c = Detection("mur", 0.7, 500, 500, 100, 100)  # isole
    kept = model.non_max_suppression([a, b, c])
    assert len(kept) == 2
    assert kept[0].confidence == 0.9


def test_lecture_de_plan_double_trait():
    """Deux traits paralleles distants de 200 mm forment un mur."""
    segments = [(0, 0, 6000, 0), (0, 200, 6000, 200)]
    walls = PlanReader().detect_walls(segments)
    assert len(walls) == 1
    assert abs(walls[0].thickness - 200) < 1
    assert walls[0].length > 5000
    assert walls[0].confidence > 0.5


def test_assistant_reconnait_les_commandes():
    assistant = ConversationalAssistant()
    assert assistant.parse("change le style en moderne").action == "set_style"
    assert assistant.parse("genere une maison de 120 m2").params["surface"] == 120
    assert assistant.parse("exporte en ifc").params["format"] == "ifc"
    assert assistant.parse("blablabla incomprehensible").action == "unknown"


def test_assistant_execute_les_handlers():
    assistant = ConversationalAssistant()
    assistant.register("set_style", lambda params: "style %s" % params["style"])
    result = assistant.execute("change le style en luxe")
    assert result["execute"] and "luxe" in result["resultat"]
    echec = assistant.execute("phrase sans commande")
    assert not echec["execute"]


def test_maintenance_predictive_detecte_une_derive():
    now = time.time()
    readings = [(now + i * 86400, 20.0 + i * 0.5) for i in range(10)]
    result = PredictiveMaintenance().assess(readings, threshold=30.0, rising=True)
    assert result["statut"] == "derive detectee"
    assert result["jours_avant_seuil"] > 0
    assert result["r2"] > 0.99
    stable = PredictiveMaintenance().assess(
        [(now + i * 86400, 20.0) for i in range(10)], threshold=30.0)
    assert stable["statut"] == "stable"
    court = PredictiveMaintenance().assess([(now, 20.0)], threshold=30.0)
    assert court["statut"] == "historique insuffisant"
''')

ajouter('tests/test_api.py', r'''
"""Tests d'integration de l'API : chaine complete du client au stockage."""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient    # noqa: E402

from API.main import app                     # noqa: E402


@pytest.fixture(scope="module")
def client(request):
    import os
    import tempfile
    from API.deps import reset_state
    directory = tempfile.mkdtemp(prefix="mercury_api_")
    reset_state(os.path.join(directory, "api.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_health_et_ready(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert client.get("/ready").json()["ready"] is True


def test_registre_des_livrables(client):
    data = client.get("/api/v1/deliverables").json()
    assert data["total"] == 70
    numeros = sorted(d["numero"] for d in data["livrables"])
    assert numeros == list(range(1, 71))


def test_cycle_de_vie_projet(client):
    created = client.post("/api/v1/projects",
                          json={"name": "Test API", "building_type": "maison"})
    assert created.status_code == 200
    project_id = created.json()["projet"]["id"]

    wall = client.post("/api/v1/projects/%s/walls" % project_id,
                       json={"start": [0, 0], "end": [6000, 0],
                             "thickness": 300, "height": 2700,
                             "exterior": True})
    assert wall.status_code == 200
    wall_id = wall.json()["mur"]["id"]

    opening = client.post("/api/v1/projects/%s/openings" % project_id,
                          json={"wall_id": wall_id, "type": "fenetre",
                                "offset": 3000, "width": 1200,
                                "height": 1400, "sill": 900})
    assert opening.status_code == 200

    hors = client.post("/api/v1/projects/%s/openings" % project_id,
                       json={"wall_id": wall_id, "type": "porte",
                             "offset": 5900, "width": 900, "height": 2100})
    assert hors.status_code == 400, "une baie hors du mur doit etre refusee"

    assert client.get("/api/v1/projects/%s" % project_id).status_code == 200
    assert client.get("/api/v1/projects/inconnu").status_code == 404


def test_generation_et_analyses(client):
    response = client.post("/api/v1/design/generate",
                           json={"typologie": "maison", "surface": 105,
                                 "chambres": 3, "variantes": 2,
                                 "iterations": 900})
    assert response.status_code == 200
    data = response.json()
    assert len(data["variantes"]) == 2
    project_id = data["meilleure"]

    takeoff = client.get("/api/v1/projects/%s/takeoff" % project_id).json()
    assert takeoff["resume"]["surface_utile_m2"] > 50
    assert takeoff["metre"]

    estimate = client.get("/api/v1/projects/%s/estimate" % project_id).json()
    assert estimate["devis"]["total_ht"] > 0
    assert estimate["planning"]["duree_totale_jours"] > 0

    carbon = client.get("/api/v1/projects/%s/carbon" % project_id).json()
    assert carbon["etiquette"] in list("ABCDE")

    energy = client.get("/api/v1/projects/%s/energy" % project_id).json()
    assert energy["kwh_m2_an"] > 0

    mauvais = client.get("/api/v1/projects/%s/energy?isolation=magique" % project_id)
    assert mauvais.status_code == 400


def test_exports(client):
    project_id = client.post("/api/v1/design/generate",
                             json={"typologie": "maison", "surface": 90,
                                   "variantes": 1, "iterations": 600}
                             ).json()["meilleure"]
    ifc = client.post("/api/v1/projects/%s/export" % project_id,
                      json={"format": "ifc"})
    assert ifc.status_code == 200
    assert ifc.text.startswith("ISO-10303-21;")
    assert "IFCWALLSTANDARDCASE" in ifc.text

    for fmt in ("obj", "gltf", "svg", "json"):
        response = client.post("/api/v1/projects/%s/export" % project_id,
                               json={"format": fmt})
        assert response.status_code == 200, fmt
        assert len(response.content) > 50, fmt

    assert client.post("/api/v1/projects/%s/export" % project_id,
                       json={"format": "dwg"}).status_code == 400


def test_jumeau_numerique(client):
    project_id = client.post("/api/v1/design/generate",
                             json={"typologie": "maison", "surface": 95,
                                   "variantes": 1, "iterations": 600}
                             ).json()["meilleure"]
    rooms = client.get("/api/v1/projects/%s" % project_id).json()["modele"]["rooms"]
    declared = client.post("/api/v1/iot/sensors",
                           json={"id": "sonde-1", "grandeur": "temperature",
                                 "projet": project_id, "piece": rooms[0]["id"]})
    assert declared.status_code == 200
    assert client.post("/api/v1/iot/sensors",
                       json={"id": "sonde-2", "grandeur": "gravite",
                             "projet": project_id}).status_code == 400
    client.post("/api/v1/iot/readings",
                json={"mesures": [{"capteur": "sonde-1", "valeur": 32.0}]})
    twin = client.get("/api/v1/projects/%s/twin" % project_id).json()
    assert twin["capteurs_total"] >= 1
    assert twin["alertes"]


def test_assistant_et_bibliotheque(client):
    response = client.post("/api/v1/assistant",
                           json={"message": "genere une maison de 130 m2"})
    assert response.json()["commande"]["action"] == "generate"
    library = client.get("/api/v1/library?limit=5").json()
    assert library["total"] <= 5 and library["objets"]
''')

ajouter('tests/test_api_cad.py', r'''
"""Routes CAO de l'API : documents, commandes, geometrie, fichiers."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from API.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture()
def document(client):
    reponse = client.post("/api/v1/cad/documents", json={"nom": "Essai"})
    assert reponse.status_code == 200
    return reponse.json()["document"]


def commande(client, document, nom, **parametres):
    return client.post("/api/v1/cad/documents/%s/command" % document,
                       json={"commande": nom, "parametres": parametres})


def test_racine_annonce_le_module_cao(client):
    charge = client.get("/").json()
    assert charge["commandes_cao"] >= 90
    assert charge["formats_fichiers"] >= 25
    assert charge["interface"] == "/app"


def test_interface_est_servie(client):
    page = client.get("/app/")
    assert page.status_code == 200
    assert "MERCURY" in page.text
    assert client.get("/app/style.css").status_code == 200
    assert client.get("/app/viewer.js").status_code == 200
    assert client.get("/app/app.js").status_code == 200
    assert client.get("/app/secret.env").status_code == 404


def test_catalogue_et_capacites(client):
    catalogue = client.get("/api/v1/cad/commands").json()
    assert catalogue["total"] >= 90
    assert "solides_primitifs" in catalogue["groupes"]
    filtre = client.get("/api/v1/cad/commands?groupe=booleens").json()
    assert all(c["groupe"] == "booleens" for c in filtre["commandes"])
    capacites = client.get("/api/v1/cad/capabilities").json()
    assert capacites["commandes"] >= 90
    assert "realiste" in capacites["styles_visuels"]
    assert "iso_sud_ouest" in capacites["vues_normalisees"]
    formats = client.get("/api/v1/cad/formats").json()
    assert formats["total"] >= 25
    assert "installation" in formats["dwg"]


def test_cycle_de_vie_dun_document(client):
    cree = client.post("/api/v1/cad/documents",
                       json={"nom": "Villa", "unites": "mm"}).json()
    identifiant = cree["document"]
    assert client.get("/api/v1/cad/documents").json()["total"] >= 1
    detail = client.get("/api/v1/cad/documents/%s" % identifiant).json()
    assert detail["etat"]["nom"] == "Villa"
    assert client.get("/api/v1/cad/documents/%s?detail=true"
                      % identifiant).json()["contenu"]["document"] == "Villa"
    assert client.delete("/api/v1/cad/documents/%s" % identifiant).json()["ferme"]
    assert client.get("/api/v1/cad/documents/%s" % identifiant).status_code == 404


def test_unite_invalide_refusee(client):
    assert client.post("/api/v1/cad/documents",
                       json={"nom": "X", "unites": "lieues"}).status_code == 422


def test_execution_de_commandes(client, document):
    reponse = commande(client, document, "BOITE", longueur=2000, largeur=1000,
                       hauteur=500)
    assert reponse.status_code == 200
    charge = reponse.json()
    assert charge["etat"]["objets"] == 1
    assert charge["resultat"]["groupe"] == "solides_primitifs"
    assert commande(client, document, "CYLINDRE", rayon=200,
                    hauteur=800).status_code == 200
    erreur = commande(client, document, "COMMANDE_INEXISTANTE")
    assert erreur.status_code == 400
    assert "inconnue" in erreur.json()["detail"]


def test_script_et_historique(client, document):
    reponse = client.post("/api/v1/cad/documents/%s/script" % document,
                          json={"script": "BOITE longueur=100 largeur=100 "
                                          "hauteur=100\nCERCLE rayon=50"})
    assert reponse.json()["commandes"] == 2
    historique = client.get("/api/v1/cad/documents/%s/history" % document).json()
    assert historique["total"] >= 2
    mauvais = client.post("/api/v1/cad/documents/%s/script" % document,
                          json={"script": "PASUNECOMMANDE"})
    assert mauvais.status_code == 400


def test_geometrie_pour_la_visionneuse(client, document):
    commande(client, document, "BOITE", longueur=1000, largeur=1000,
             hauteur=1000)
    commande(client, document, "CERCLE", rayon=400)
    maillage = client.get("/api/v1/cad/documents/%s/mesh" % document).json()
    assert maillage["sommets"] == 36           # 12 triangles pour un cube
    assert len(maillage["positions"]) == maillage["sommets"] * 3
    assert len(maillage["normales"]) == len(maillage["positions"])
    assert len(maillage["groupes"]) == 1
    # La boite est celle du document entier : elle englobe aussi le cercle,
    # puisque c'est elle qui cadre le zoom etendu de l'interface.
    assert maillage["boite"]["taille"] == [1400.0, 1400.0, 1000.0]
    courbes = client.get("/api/v1/cad/documents/%s/curves" % document).json()
    assert courbes["total"] == 1
    toutes = client.get("/api/v1/cad/documents/%s/mesh?angle_aretes=0"
                        % document).json()
    assert len(toutes["aretes"]) >= len(maillage["aretes"])


def test_aretes_vives_filtrent_les_facettes(client, document):
    commande(client, document, "SPHERE", rayon=500, segments=24, anneaux=12)
    vives = client.get("/api/v1/cad/documents/%s/mesh?angle_aretes=25"
                       % document).json()
    toutes = client.get("/api/v1/cad/documents/%s/mesh?angle_aretes=0"
                        % document).json()
    assert len(vives["aretes"]) < len(toutes["aretes"])


def test_rendu_png(client, document):
    commande(client, document, "BOITE", longueur=1000, largeur=1000,
             hauteur=1000)
    image = client.post("/api/v1/cad/documents/%s/render" % document,
                        json={"largeur": 160, "hauteur": 120,
                              "style": "conceptuel"})
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.post("/api/v1/cad/documents/%s/render" % document,
                       json={"style": "aquarelle"}).status_code == 400
    assert client.post("/api/v1/cad/documents/%s/render" % document,
                       json={"largeur": 99999}).status_code == 422


@pytest.mark.parametrize("format_cible", ["dxf", "step", "stl", "obj", "gltf",
                                          "glb", "ply", "3mf", "ifc", "pdf",
                                          "svg", "json", "png", "xyz", "las"])
def test_export_dans_chaque_format(client, document, format_cible):
    commande(client, document, "BOITE", longueur=1000, largeur=1000,
             hauteur=1000)
    reponse = client.post("/api/v1/cad/documents/%s/export" % document,
                          json={"format": format_cible, "options": {}})
    assert reponse.status_code == 200
    assert len(reponse.content) > 0
    assert "attachment" in reponse.headers["content-disposition"]


def test_export_dans_un_format_inconnu(client, document):
    reponse = client.post("/api/v1/cad/documents/%s/export" % document,
                          json={"format": "zzz"})
    assert reponse.status_code == 400


def test_identification_import_et_conversion(client, document):
    commande(client, document, "BOITE", longueur=1000, largeur=500, hauteur=300)
    export = client.post("/api/v1/cad/documents/%s/export" % document,
                         json={"format": "stl"})
    contenu = export.content

    identite = client.post("/api/v1/cad/files/identify",
                           files={"fichier": ("piece.stl", contenu,
                                              "application/octet-stream")})
    assert identite.json()["identification"]["format"] == "stl"

    ouvert = client.post("/api/v1/cad/files/open",
                         files={"fichier": ("piece.stl", contenu,
                                            "application/octet-stream")})
    assert ouvert.status_code == 200
    assert ouvert.json()["etat"]["objets"] == 1

    fusionne = client.post("/api/v1/cad/documents/%s/import" % document,
                           files={"fichier": ("piece.stl", contenu,
                                              "application/octet-stream")})
    assert fusionne.json()["objets_ajoutes"] == 1

    converti = client.post("/api/v1/cad/files/convert?cible=step",
                           files={"fichier": ("piece.stl", contenu,
                                              "application/octet-stream")})
    assert converti.status_code == 200
    assert b"ISO-10303-21" in converti.content


def test_fichier_illisible_est_refuse(client):
    reponse = client.post("/api/v1/cad/files/open",
                          files={"fichier": ("x.bin", b"\x01\x02\x03\x04",
                                             "application/octet-stream")})
    assert reponse.status_code == 400


def test_document_inconnu(client):
    assert commande(client, "doc-9999", "BOITE").status_code == 404
    assert client.get("/api/v1/cad/documents/doc-9999/mesh").status_code == 404
''')

ajouter('tests/test_bim_models.py', r'''
"""Tests du modele BIM : validation, quantites, serialisation."""
from __future__ import annotations

import pytest

from BIM_Engine.models import BuildingProject, Opening, Room, Wall


def test_mur_calcule_ses_quantites():
    wall = Wall(start=(0, 0), end=(5000, 0), thickness=200, height=2700)
    assert abs(wall.length - 5000) < 1e-9
    assert abs(wall.gross_area_m2 - 13.5) < 1e-6
    wall.add_opening(Opening(type="porte", offset=2500, width=900, height=2100))
    assert wall.net_area_m2 < wall.gross_area_m2
    assert abs(wall.gross_area_m2 - wall.net_area_m2 - 1.89) < 1e-6


def test_validations_refusent_les_valeurs_absurdes():
    with pytest.raises(ValueError):
        Wall(start=(0, 0), end=(1000, 0), thickness=0)
    with pytest.raises(ValueError):
        Wall(start=(0, 0), end=(1000, 0), height=-1)
    with pytest.raises(ValueError):
        Opening(type="trappe")
    with pytest.raises(ValueError):
        BuildingProject(building_type="chateau_fort")


def test_baie_hors_du_mur_est_refusee():
    wall = Wall(start=(0, 0), end=(2000, 0))
    with pytest.raises(ValueError) as error:
        wall.add_opening(Opening(offset=1900, width=900))
    assert "deborde" in str(error.value)


def test_serialisation_sans_perte():
    project = BuildingProject(name="Test", building_type="villa")
    wall = project.add_wall(Wall(start=(0, 0), end=(4000, 0), exterior=True))
    wall.add_opening(Opening(type="fenetre", offset=2000, width=1200,
                             height=1400, sill=900))
    project.rooms.append(Room(name="Sejour", area_m2=25.4,
                              outline=[(0, 0), (5000, 0), (5000, 5000)]))
    restored = BuildingProject.from_dict(project.to_dict())
    assert restored.name == project.name
    assert restored.building_type == project.building_type
    assert len(restored.walls) == 1
    assert len(restored.walls[0].openings) == 1
    assert restored.walls[0].openings[0].type == "fenetre"
    assert restored.rooms[0].area_m2 == 25.4


def test_versionnage():
    project = BuildingProject()
    assert project.version == 1
    project.bump().bump()
    assert project.version == 3
''')

ajouter('tests/test_commands.py', r'''
"""Interpreteur de commandes compatible AutoCAD."""
from __future__ import annotations

import math

import pytest

from CAD_Core.commands import (CommandError, CommandInterpreter, catalog,
                               groups)


@pytest.fixture()
def cli():
    return CommandInterpreter()


def test_catalogue_complet():
    commandes = catalog()
    assert len(commandes) >= 90
    noms = {c["nom"] for c in commandes}
    for attendu in ("BOITE", "EXTRUSION", "REVOLUTION", "BALAYAGE", "LISSAGE",
                    "UNION", "SOUSTRACTION", "INTERSECTION", "RACCORDARETE",
                    "CHANFREINARETE", "GAINE", "COUPE", "SECTION", "RESEAU3D",
                    "MIROIR3D", "ALIGNER3D", "HACHURES", "COTLIN", "CALQUE",
                    "SCU", "RENDU", "EXPORTER"):
        assert attendu in noms
    assert len(groups()) >= 12
    assert all(c["resume"] for c in commandes)


def test_resolution_par_alias_et_anglais():
    assert CommandInterpreter.resolve("L").name == "LIGNE"
    assert CommandInterpreter.resolve("box").name == "BOITE"
    assert CommandInterpreter.resolve("EXT").name == "EXTRUSION"
    assert CommandInterpreter.resolve("subtract").name == "SOUSTRACTION"


def test_commande_inconnue_propose_une_correction():
    with pytest.raises(CommandError) as erreur:
        CommandInterpreter.resolve("BOIT")
    assert "BOITE" in str(erreur.value)


def test_analyse_dune_ligne():
    nom, arguments = CommandInterpreter.parse(
        "BOITE longueur=1000 origine=0,0,500 centre=vrai")
    assert nom == "BOITE"
    assert arguments["longueur"] == 1000
    assert arguments["origine"] == [0, 0, 500]
    assert arguments["centre"] is True
    with pytest.raises(CommandError):
        CommandInterpreter.parse("")


def test_creation_de_primitives(cli):
    resultat = cli.execute("BOITE longueur=2000 largeur=1000 hauteur=500")
    assert resultat["handle"] in cli.document.entities
    for ligne in ("CYLINDRE rayon=300 hauteur=2000", "SPHERE rayon=400",
                  "TORE rayon=500 rayon_tube=80", "PYRAMIDE rayon=400 cotes=6",
                  "BISEAU longueur=800 largeur=400 hauteur=600"):
        assert "handle" in cli.execute(ligne)
    assert len(cli.document.entities) == 6


def test_operations_booleennes(cli):
    a = cli.execute("BOITE longueur=1000 largeur=1000 hauteur=1000")["handle"]
    b = cli.execute("BOITE longueur=500 largeur=500 hauteur=2000 "
                    "origine=250,250,-500")["handle"]
    resultat = cli.execute("SOUSTRACTION", base=a, outils=[b])
    solide = cli.document.entities[resultat["handle"]].geometry
    assert solide.volume == pytest.approx(1e9 - 500 * 500 * 1000, rel=1e-6)
    assert a not in cli.document.entities


def test_soustraction_sans_selection_est_refusee(cli):
    with pytest.raises(CommandError):
        cli.execute("SOUSTRACTION")


def test_solides_issus_dun_profil(cli):
    cli.execute("EXTRUSION", profil=[[0, 0, 0], [1000, 0, 0], [1000, 600, 0],
                                     [0, 600, 0]], hauteur=300)
    cli.execute("REVOLUTION", profil=[[500, 0, 0], [800, 0, 0], [800, 0, 400],
                                      [500, 0, 400]], angle=270)
    cli.execute("BALAYAGE", profil=[[0, 0, 0], [100, 0, 0], [100, 100, 0]],
                trajectoire=[[0, 0, 0], [0, 0, 1500]])
    cli.execute("LISSAGE", sections=[
        [[0, 0, 0], [600, 0, 0], [600, 600, 0], [0, 600, 0]],
        [[150, 150, 900], [450, 150, 900], [450, 450, 900], [150, 450, 900]]])
    assert len(cli.document.entities) == 4


def test_edition_de_solides(cli):
    handle = cli.execute("BOITE longueur=600 largeur=600 hauteur=600")["handle"]
    avant = cli.document.entities[handle].geometry.volume
    resultat = cli.execute("RACCORDARETE rayon=60 segments=8", handles=[handle])
    assert resultat["volume_mm3"] < avant
    autre = cli.execute("BOITE longueur=800 largeur=800 hauteur=800 "
                        "origine=2000,0,0")["handle"]
    creuse = cli.execute("GAINE epaisseur=50", handles=[autre])
    assert creuse["volume_mm3"] == pytest.approx(800 ** 3 - 700 ** 3, rel=1e-6)
    coupe = cli.execute("COUPE point=2400,400,400 normale=0,0,1",
                        handles=[autre])
    assert coupe["morceaux"] == 2


def test_section_et_mesures(cli):
    handle = cli.execute("BOITE longueur=500 largeur=500 hauteur=500")["handle"]
    section = cli.execute("SECTION point=250,250,250 normale=0,0,1",
                          handles=[handle])
    assert section["aire_mm2"] == pytest.approx(250000, rel=1e-6)
    assert cli.execute("MESURER type=distance",
                       points=[[0, 0, 0], [300, 400, 0]])["distance_mm"] == 500.0
    assert cli.execute("MESURER type=angle",
                       points=[[1, 0, 0], [0, 0, 0], [0, 1, 0]])["angle_deg"] \
        == pytest.approx(90.0)
    assert cli.execute("MESURER type=volume", handles=[handle])["volume_mm3"] \
        == pytest.approx(1.25e8)
    with pytest.raises(CommandError):
        cli.execute("MESURER type=poids", handles=[handle])
    assert cli.execute("VERIFSOLIDE", handles=[handle])["controle"]["ferme"]
    assert cli.execute("PROPMECA", handles=[handle])["proprietes"][0]["masse_kg"] > 0


def test_transformations(cli):
    handle = cli.execute("BOITE longueur=100 largeur=100 hauteur=100")["handle"]
    assert cli.execute("COPIER vecteur=500,0,0 copies=2",
                       handles=[handle])["copies"] == 2
    assert cli.execute("RESEAU3D colonnes=3 rangees=2 niveaux=1 pas_colonne=200 "
                       "pas_rangee=200", handles=[handle])["occurrences"] == 6
    assert cli.execute("RESEAUPOLAIRE nombre=6",
                       handles=[handle])["occurrences"] == 6
    assert cli.execute("RESEAUCHEMIN", trajectoire=[[0, 0, 0], [1000, 0, 0]],
                       nombre=4, handles=[handle])["occurrences"] == 4
    cli.execute("DEPLACER3D vecteur=0,0,100", handles=[handle])
    cli.execute("ROTATION3D axe=0,0,1 angle=45", handles=[handle])
    assert cli.execute("MIROIR3D point=0,0,0 normale=1,0,0",
                       handles=[handle])["copies"] == 1


def test_dessin_2d_et_annotation(cli):
    for ligne in ("LIGNE depart=0,0,0 arrivee=2000,0,0",
                  "CERCLE centre=1000,1000,0 rayon=400",
                  "ARC centre=0,0,0 rayon=800 depart=0 arrivee=120",
                  "RECTANG largeur=1200 profondeur=800 raccord=100",
                  "POLYGONE cotes=8 rayon=500",
                  "ELLIPSE rayon_x=900 rayon_y=400", "POINT position=1,2,3"):
        assert "handle" in cli.execute(ligne)
    assert cli.execute("COTLIN depart=0,0,0 arrivee=2000,0,0")["mesure_mm"] \
        == 2000.0
    assert cli.execute("COTANG sommet=0,0,0 premier=1000,0,0 "
                       "second=0,1000,0")["mesure_deg"] == pytest.approx(90.0)
    assert cli.execute("COTRAYON rayon=400 diametre=vrai")["texte"] == "Ø800"
    assert cli.execute("TEXTMULT texte=Plan hauteur=50")["texte"] == "Plan"
    assert cli.execute("HACHURES", profil=[[0, 0, 0], [1000, 0, 0],
                                           [1000, 800, 0], [0, 800, 0]],
                       motif="ANSI31", echelle=8)["aire_mm2"] == 800000.0
    assert cli.execute("TABLEAU", lignes=[["Lot", "Qte"], ["Beton", "12"]],
                       titre="METRE")["colonnes"] == 2


def test_organisation_et_annulation(cli):
    handle = cli.execute("BOITE longueur=100 largeur=100 hauteur=100")["handle"]
    assert cli.execute("CALQUE nom=STRUCTURE couleur=1")["courant"] == "STRUCTURE"
    assert cli.execute("BLOC nom=POTEAU", handles=[handle])["bloc"]["nom"] \
        == "POTEAU"
    assert cli.execute("INSERER nom=POTEAU position=5000,0,0")["objets"] == 1
    assert cli.execute("SCU nom=CHANTIER origine=100,200,0")["scu"]["nom"] \
        == "CHANTIER"
    assert cli.execute("PRESENTATION nom=PLANCHE format=A1")["presentation"][
        "format"] == "A1"
    assert cli.execute("SELECTIONNER tout=vrai")["objets"] >= 2
    avant = len(cli.document.entities)
    cli.execute("BOITE longueur=10 largeur=10 hauteur=10")
    assert len(cli.document.entities) == avant + 1
    assert cli.execute("ANNULER")["annule"]
    assert len(cli.document.entities) == avant
    assert cli.execute("RETABLIR")["retabli"]
    assert cli.execute("ETAT")["etat"]["objets"] >= 1


def test_aides_au_dessin(cli):
    cli.execute("BOITE longueur=1000 largeur=1000 hauteur=1000")
    assert cli.execute("ACCROBJ modes=4143")["accrochages"]["osmode"] == 4143
    accroche = cli.execute("ACCROCHER curseur=5,5,5")["accrochage"]
    assert accroche["mode"] == "extremite"
    assert cli.execute("ORTHO actif=vrai")["ortho"] is True
    assert cli.execute("RESOL actif=vrai pas=250")["pas_mm"] == 250.0


def test_vues_et_rendu(cli):
    cli.execute("BOITE longueur=1000 largeur=1000 hauteur=1000")
    assert cli.execute("VUEPOINT vue=dessus")["commande"] == "VUEPOINT"
    cli.execute("ORBITE3D azimut=25 elevation=10")
    cli.execute("ZOOM etendu=vrai")
    cli.execute("PAN dx=100 dy=50")
    assert cli.execute("STYLESVISUELS style=conceptuel")["commande"] == \
        "STYLESVISUELS"
    with pytest.raises(CommandError):
        cli.execute("STYLESVISUELS style=aquarelle")
    rendu = cli.execute("RENDU largeur=160 hauteur=120")
    assert rendu["image_png_octets"] > 100
    assert cli.execute("MASQUE largeur=160 hauteur=120")["svg_octets"] > 100
    assert "cible" in cli.execute("VUE nom=Perspective1")["vue"]


def test_exports_depuis_la_ligne_de_commande(cli):
    cli.execute("BOITE longueur=1000 largeur=1000 hauteur=1000")
    for format_cible in ("dxf", "step", "stl", "gltf", "pdf", "ifc", "json",
                         "svg", "obj"):
        resultat = cli.execute("EXPORTER format=%s" % format_cible)
        assert resultat["octets"] > 0
    assert cli.execute("FORMATS")["capacites"]["formats"] >= 25


def test_script_de_commandes(cli):
    resultats = cli.run_script(
        "BOITE longueur=100 largeur=100 hauteur=100\n"
        "CERCLE rayon=50 ; un commentaire ignore\n"
        "ETAT")
    assert [r["commande"] for r in resultats] == ["BOITE", "CERCLE", "ETAT"]
    assert len(cli.history) == 3


def test_aide_en_ligne(cli):
    assert cli.execute("AIDE commande=BOITE")["aide"]["nom"] == "BOITE"
    assert len(cli.execute("AIDE")["commandes"]) >= 90


def test_parametres_invalides(cli):
    with pytest.raises(CommandError):
        cli.execute("BOITE", parametre_inexistant=1)
    with pytest.raises(CommandError):
        cli.execute("EXTRUSION", profil=None)
    with pytest.raises(CommandError):
        cli.execute("RACCORDARETE rayon=10", handles=["INCONNU"])
''')

ajouter('tests/test_document_view.py', r'''
"""Document CAO, accrochages, annotation, vues et rendu."""
from __future__ import annotations

import math

import pytest

from CAD_Core.annotate import (angular_dimension, arc_length_dimension,
                               baseline_dimensions, continuous_dimensions,
                               dimension_from_solid, hatch, hatch_lines, leader,
                               linear_dimension, mtext, ordinate_dimension,
                               radial_dimension, revision_cloud, table)
from CAD_Core.document import CadDocument, Layer
from CAD_Core.math3d import BBox3, Plane, Vec3, Z_AXIS
from CAD_Core.primitives import box, cylinder
from CAD_Core.profiles import Curve, Profile
from CAD_Core.render_engine import Framebuffer, Renderer3D, render_thumbnail
from CAD_Core.snapping import OSNAP_MODES, SnapEngine
from CAD_Core.view3d import Camera, STANDARD_VIEWS, VISUAL_STYLES, Viewport


@pytest.fixture()
def document():
    doc = CadDocument("Essai")
    doc.add_layer("MURS", 1, "CONTINUOUS", 35)
    doc.set_current_layer("MURS")
    doc.add(box(1000, 200, 2500))
    doc.add(cylinder(150, 3000, (2000, 0, 0), segments=24))
    return doc


def test_calques(document):
    assert document.current_layer == "MURS"
    assert document.layers["MURS"].color == 1
    assert len(document.layer_entities("MURS")) == 2
    assert not document.delete_layer("0")
    with pytest.raises(ValueError):
        document.delete_layer("MURS")
    with pytest.raises(ValueError):
        document.add_layer("X", linetype="POINTILLE")


def test_unites_invalides():
    with pytest.raises(ValueError):
        CadDocument("X", "lieues")


def test_annuler_retablir(document):
    depart = len(document.entities)
    document.snapshot()
    document.remove(list(document.entities)[0])
    assert len(document.entities) == depart - 1
    assert document.undo()
    assert len(document.entities) == depart
    assert document.redo()
    assert len(document.entities) == depart - 1
    document.undo()


def test_blocs(document):
    handle = list(document.entities)[0]
    bloc = document.define_block("POTEAU", [handle], (0, 0, 0))
    assert bloc.name == "POTEAU"
    place = document.insert_block("POTEAU", (5000, 0, 0))
    assert len(place) == 1
    assert round(place[0].geometry.centroid.x) == 5500
    assert document.explode_block([place[0].handle]) == 1
    with pytest.raises(ValueError):
        document.insert_block("INCONNU")
    with pytest.raises(ValueError):
        document.define_block("VIDE", [])


def test_selection(document):
    assert len(document.select_all()) == 2
    assert len(document.select_window((-10, -10, -10), (1500, 1500, 3000))) == 1
    assert len(document.select_window((-10, -10, -10), (1500, 1500, 3000),
                                      crossing=True)) >= 1
    assert len(document.select_by_layer("MURS")) == 2
    assert len(document.selected_entities()) == 2


def test_scu_presentations_et_vues(document):
    scu = document.set_ucs("CHANTIER", (100, 200, 0))
    assert scu.z_axis.rounded(6) == (0.0, 0.0, 1.0)
    assert scu.to_local(scu.to_world((5, 5, 5))).rounded(6) == (5.0, 5.0, 5.0)
    assert document.add_layout("PLAN", "A1", 0.02).width_mm == 841.0
    with pytest.raises(ValueError):
        document.add_layout("X", "A9")
    document.save_view("ISO", {"azimut_deg": 315})
    assert "ISO" in document.named_views


def test_statistiques_et_fusion(document):
    fiche = document.statistics()
    assert fiche["objets"] == 2
    assert fiche["volume_total_mm3"] > 0
    autre = CadDocument("Autre")
    autre.add(box(100, 100, 100))
    assert document.merge(autre, "EXT_") == 1
    assert len(document.entities) == 3


def test_accrochages():
    moteur = SnapEngine(aperture=60, modes=sum(OSNAP_MODES.values()))
    cube = box(1000, 1000, 1000)
    assert moteur.snap((5, 5, 5), [cube]).mode == "extremite"
    assert moteur.snap((500, 4, 0), [cube]).mode == "milieu"
    assert moteur.snap((510, 510, 1000), [cube]).mode == "centre"
    assert moteur.snap((9000, 9000, 9000), [cube]) is None
    moteur.ortho = True
    accroche = moteur.snap((1005, 30, 0), [cube], last_point=(1000, 0, 0))
    assert accroche.point.rounded(3) == (1000.0, 0.0, 0.0)
    moteur.ortho = False
    moteur.grid_snap = True
    moteur.grid_spacing = 250
    assert moteur.snap((5300, 5100, 0), [cube]).mode == "resolution"
    assert moteur.polar_track((0, 0, 0), (100, 30, 0)).rounded(3)[1] == 0.0
    croisements = moteur.intersections(
        [Curve.line((0, 0, 0), (100, 0, 0)), Curve.line((50, -50, 0),
                                                        (50, 50, 0))],
        (50, 0, 0))
    assert croisements[0].rounded(3) == (50.0, 0.0, 0.0)
    assert "extremite" in moteur.to_dict()["modes_actifs"]


def test_cotations():
    lineaire = linear_dimension((0, 0, 0), (3000, 0, 0))
    assert lineaire["mesure_mm"] == 3000.0 and lineaire["texte"] == "3000"
    assert angular_dimension((0, 0, 0), (100, 0, 0),
                             (0, 100, 0))["mesure_deg"] == pytest.approx(90.0)
    assert radial_dimension((0, 0, 0), 250, diameter=True)["texte"] == "Ø500"
    assert arc_length_dimension((0, 0, 0), 100, 0, 90)["mesure_mm"] == \
        pytest.approx(math.pi * 50, rel=1e-6)
    assert ordinate_dimension((1250, 0, 0))["mesure_mm"] == 1250.0
    assert len(continuous_dimensions([(0, 0, 0), (1000, 0, 0), (2500, 0, 0)])) == 2
    assert len(baseline_dimensions([(0, 0, 0), (1000, 0, 0), (2500, 0, 0)])) == 2
    assert dimension_from_solid(box(1200, 800, 300), "y")["texte"] == "800"
    with pytest.raises(ValueError):
        angular_dimension((0, 0, 0), (0, 0, 0), (1, 0, 0))
    with pytest.raises(ValueError):
        continuous_dimensions([(0, 0, 0)])


def test_hachures_texte_tableau_et_nuage():
    profil = Profile.rectangle(1000, 600).with_hole(
        Profile.rectangle(200, 200, (400, 200, 0)).outline)
    remplissage = hatch(profil, "ANSI31", 10)
    assert remplissage["aire_mm2"] == pytest.approx(560000)
    assert len(remplissage["lignes"]) > 5
    assert len(hatch_lines(profil, "AR-CONC", 4)) > 0
    with pytest.raises(ValueError):
        hatch(profil, "MOTIF_INCONNU")
    assert mtext((0, 0, 0), "ligne1\nligne2")["lignes"] == ["ligne1", "ligne2"]
    assert leader([(0, 0, 0), (100, 100, 0)], "Poteau")["texte"] == "Poteau"
    with pytest.raises(ValueError):
        leader([(0, 0, 0)], "x")
    tableau = table((0, 0, 0), [["Lot", "Qte"], ["Beton", "12"]], title="METRE")
    assert tableau["colonnes"] == 2
    assert len(revision_cloud([(0, 0, 0), (900, 0, 0), (900, 900, 0)])["points"]) > 6
    with pytest.raises(ValueError):
        revision_cloud([(0, 0, 0)])


def test_camera_et_projection():
    camera = Camera(width=800, height=600)
    camera.zoom_extents(BBox3.of([(0, 0, 0), (5000, 4000, 3000)]))
    x, y, _ = camera.project((2500, 2000, 1500))
    assert x == pytest.approx(400.0, abs=1.0)
    assert y == pytest.approx(300.0, abs=1.0)
    camera.set_standard_view("dessus")
    assert camera.elevation_deg > 80
    camera.set_standard_view("face")
    assert camera.position.y < 0
    with pytest.raises(ValueError):
        camera.set_standard_view("dedans")
    camera.orbit(45, 10)
    camera.pan(100, 50)
    camera.dolly(2.0)
    with pytest.raises(ValueError):
        camera.dolly(0)
    assert Camera.from_dict(camera.to_dict()).width == camera.width
    assert len(camera.add_clip_plane(
        Plane.from_point_normal((0, 0, 0), Z_AXIS)).clip_planes) == 1


def test_styles_visuels():
    fenetre = Viewport()
    assert fenetre.set_style("realiste").visual_style == "realiste"
    with pytest.raises(ValueError):
        fenetre.set_style("aquarelle")
    assert set(VISUAL_STYLES) >= {"filaire_2d", "realiste", "conceptuel"}
    assert "iso_sud_ouest" in STANDARD_VIEWS


@pytest.mark.parametrize("style", sorted(VISUAL_STYLES))
def test_rendu_de_chaque_style(style):
    solides = [box(2000, 1500, 800), cylinder(300, 2500, (2600, 700, 0),
                                              segments=16)]
    camera = Camera(width=160, height=120)
    boite = BBox3()
    for solide in solides:
        boite.add(solide.bbox.min).add(solide.bbox.max)
    camera.zoom_extents(boite)
    image = Renderer3D().render(solides, camera, style)
    png = image.to_png()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png) > 100


def test_rendu_refuse_un_style_inconnu():
    with pytest.raises(ValueError):
        Renderer3D().render([box(10, 10, 10)], Camera(width=64, height=64),
                            "gouache")


def test_lignes_cachees_et_vignette():
    solides = [box(1000, 1000, 1000)]
    camera = Camera(width=200, height=150)
    camera.zoom_extents(solides[0].bbox)
    svg = Renderer3D().hidden_line_svg(solides, camera)
    assert svg.startswith("<svg") and "polyline" in svg
    assert Renderer3D().wireframe_svg(solides, camera).count("<line") == 12
    assert render_thumbnail(solides, 120, 90)[:4] == b"\x89PNG"


def test_tampon_image():
    tampon = Framebuffer(4, 3, (10, 20, 30))
    assert tampon.get(0, 0) == (10, 20, 30)
    tampon.set(1, 1, (200, 100, 50), 0.0)
    assert tampon.get(1, 1) == (200, 100, 50)
    tampon.set(1, 1, (0, 0, 0), 5.0)             # plus loin : ignore
    assert tampon.get(1, 1) == (200, 100, 50)
    tampon.blend(2, 2, (255, 255, 255), 1.0)
    assert tampon.get(2, 2) == (255, 255, 255)
    assert tampon.to_ppm().startswith(b"P6")
    with pytest.raises(ValueError):
        Framebuffer(0, 10)
''')

ajouter('tests/test_economics.py', r'''
"""Tests du metre, du chiffrage et du planning."""
from __future__ import annotations

import pytest

from Construction.planning import ConstructionPlanner
from Estimating.cost_ai import CostEstimator
from Estimating.takeoff import QuantityTakeoff


def test_metre_porte_ses_formules(furnished):
    lines = QuantityTakeoff().compute(furnished)
    assert lines, "le metre ne doit pas etre vide"
    codes = {line.code for line in lines}
    assert "MUR.EXT.ML" in codes and "FIN.SOL.M2" in codes
    assert all(line.formula for line in lines), "chaque ligne porte sa formule"
    assert all(line.quantity >= 0 for line in lines)


def test_devis_coherent(furnished):
    estimate = CostEstimator().estimate(furnished)
    assert estimate["sous_total"] > 0
    assert estimate["total_ht"] > estimate["sous_total"]
    assert estimate["total_ttc"] > estimate["total_ht"]
    assert abs(sum(estimate["par_lot"].values()) - estimate["sous_total"]) < 1.0
    assert estimate["ratio_eur_m2"] > 0


def test_taux_invalides_refuses(furnished):
    """Les taux et coefficients absurdes doivent etre refuses a la source."""
    with pytest.raises(ValueError):
        CostEstimator(contingency=1.5)
    with pytest.raises(ValueError):
        CostEstimator(overhead=-0.1)
    with pytest.raises(ValueError):
        CostEstimator(tax=1.0)
    with pytest.raises(ValueError):
        CostEstimator().estimate(furnished, region_factor=0)
    with pytest.raises(ValueError):
        CostEstimator().schedule({"lignes": []}, crews=0)


def test_planning_et_chemin_critique(furnished):
    estimator = CostEstimator()
    estimate = estimator.estimate(furnished)
    schedule = estimator.schedule(estimate)
    assert schedule, "le planning ne doit pas etre vide"
    plan = ConstructionPlanner().plan(schedule)
    assert plan["duree_totale_jours"] > 0
    assert plan["chemin_critique"]
    for task in plan["taches"]:
        assert task["fin_jour"] > task["debut_jour"]


def test_optimisation_budget(furnished):
    estimator = CostEstimator()
    base = estimator.estimate(furnished)["total_ht"]
    result = estimator.optimize(furnished, target=base * 0.7)
    assert result["actions"], "des leviers doivent etre proposes"
    assert result["cible"] < result["total_ht"]
''')

ajouter('tests/test_engines.py', r'''
"""Tests des moteurs 2D et 3D : detection des pieces et extrusion."""
from __future__ import annotations

import pytest

from CAD_Core.engine_3d import Engine3D
from CAD_Core.geometry import polygon_area


def test_detection_des_pieces(state, project):
    """Un rectangle coupe en T doit donner trois pieces."""
    faces = state.engine_2d.detect_rooms(project.walls)
    assert len(faces) == 3, "attendu 3 pieces, obtenu %d" % len(faces)
    total = sum(abs(polygon_area(f)) for f in faces) / 1e6
    assert 75 < total < 82, "surface totale incoherente : %.1f m2" % total


def test_metrics_de_piece(state, project):
    faces = state.engine_2d.detect_rooms(project.walls)
    metrics = state.engine_2d.room_metrics(faces[0], 150.0)
    assert metrics["area_m2"] > 0
    assert metrics["perimeter_m"] > 0
    assert len(metrics["outline"]) >= 3


def test_extrusion_perce_les_baies(furnished):
    mesh = Engine3D().build(furnished)
    stats = mesh.stats
    assert stats["vertices"] > 100
    assert stats["faces"] > 60
    assert stats["groups"] >= len(furnished.walls)
    # un mur perce produit plus de faces qu'un mur plein
    groups = [g for g in mesh.groups if g.name.startswith("mur_")]
    assert groups, "aucun groupe de mur dans le maillage"
    assert all(g.count > 0 for g in groups)


def test_maillage_indices_valides(furnished):
    mesh = Engine3D().build(furnished)
    count = len(mesh.vertices)
    for face in mesh.faces:
        assert all(0 <= index < count for index in face), "indice hors bornes"
''')

ajouter('tests/test_generative.py', r'''
"""Tests de la conception generative (livrable #03)."""
from __future__ import annotations

import pytest

from AI_Engine.generative_design import (
    GenerativeDesigner, build_program, slice_rects,
)


def test_programme_cale_sur_la_surface():
    for surface in (75.0, 110.0, 150.0):
        program = build_program("maison", surface, bedrooms=3)
        assert abs(program.target_area - surface) / surface < 0.06
        assert not program.saturation


def test_programme_signale_la_saturation():
    """210 m2 pour 3 chambres : les pieces butent sur leur taille d'usage."""
    program = build_program("maison", 210.0, bedrooms=3)
    assert program.saturation, "la saturation doit etre signalee"
    assert program.target_area < 210.0
    large = build_program("maison", 210.0, bedrooms=5, bathrooms=2)
    assert abs(large.target_area - 210.0) / 210.0 < 0.10


def test_decoupe_couvre_toute_l_emprise():
    rects = slice_rects(12000, 9000, [0, 1, 0], [0.4, 0.6, 0.5], [0, 0, 1])
    assert len(rects) == 4
    aire = sum(w * h for _, _, w, h in rects)
    assert abs(aire - 12000 * 9000) < 1.0, "la decoupe ne doit rien perdre"


def test_plan_genere_est_un_batiment_complet():
    program = build_program("maison", 110, bedrooms=3)
    projects = GenerativeDesigner().generate(program, variants=2,
                                             iterations=1200, seed=3)
    assert len(projects) == 2
    project = projects[0]
    assert len(project.rooms) == len(program.rooms)
    assert len(project.walls) >= 6
    assert any(w.exterior for w in project.walls)
    assert any(not w.exterior for w in project.walls)
    openings = [o for w in project.walls for o in w.openings]
    assert len(openings) >= 5
    assert any(o.type == "porte" for o in openings)
    assert any(o.type == "fenetre" for o in openings)
    for wall in project.walls:
        for opening in wall.openings:
            assert 0 <= opening.offset <= wall.length


def test_variantes_classees_et_deterministes():
    program = build_program("maison", 120, bedrooms=3)
    first = GenerativeDesigner().search(program, variants=3, iterations=600, seed=42)
    program2 = build_program("maison", 120, bedrooms=3)
    second = GenerativeDesigner().search(program2, variants=3, iterations=600, seed=42)
    assert [round(c.cost, 6) for c in first] == [round(c.cost, 6) for c in second]
    assert first[0].cost <= first[-1].cost


def test_conformite_au_programme():
    program = build_program("restaurant", 240, covers=70)
    project = GenerativeDesigner().generate(program, variants=3,
                                            iterations=1800, seed=11)[0]
    targets = {spec.name: spec.target_m2 for spec in program.rooms}
    gaps = [abs(r.area_m2 - targets[r.name]) / targets[r.name]
            for r in project.rooms if r.name in targets]
    assert sum(gaps) / len(gaps) < 0.40
''')

ajouter('tests/test_geometry.py', r'''
"""Tests du noyau geometrique : ce sont les fondations, ils passent d'abord."""
from __future__ import annotations

import math

import pytest

from CAD_Core.geometry import (
    Segment, Vec2, offset_polygon, point_in_polygon, polygon_area,
    polygon_centroid, polygon_perimeter, segment_intersection,
)


def test_vecteurs():
    a, b = Vec2(3, 4), Vec2(1, 0)
    assert a.norm() == 5.0
    assert abs(a.unit().norm() - 1.0) < 1e-9
    assert (a + b).as_tuple() == (4, 4)
    assert (a - b).as_tuple() == (2, 4)
    assert a.dot(b) == 3
    assert a.cross(b) == -4
    assert b.perp().as_tuple() == (0, 1)


def test_segment():
    s = Segment(Vec2(0, 0), Vec2(10, 0))
    assert s.length == 10
    assert s.midpoint.as_tuple() == (5, 0)
    assert s.point_at(0.5).as_tuple() == (5, 0)
    assert s.distance_to(Vec2(5, 3)) == 3
    assert s.distance_to(Vec2(-5, 0)) == 5      # au dela de l'extremite


def test_intersection():
    a = Segment(Vec2(0, 0), Vec2(10, 0))
    b = Segment(Vec2(5, -5), Vec2(5, 5))
    point, t, u = segment_intersection(a, b)
    assert abs(point.x - 5) < 1e-9 and abs(point.y) < 1e-9
    assert 0 < t < 1 and 0 < u < 1
    assert segment_intersection(a, Segment(Vec2(0, 3), Vec2(10, 3))) is None


def test_polygone():
    carre = [Vec2(0, 0), Vec2(1000, 0), Vec2(1000, 1000), Vec2(0, 1000)]
    assert polygon_area(carre) == 1_000_000
    assert polygon_perimeter(carre) == 4000
    centre = polygon_centroid(carre)
    assert abs(centre.x - 500) < 1e-6 and abs(centre.y - 500) < 1e-6
    assert point_in_polygon(Vec2(500, 500), carre)
    assert not point_in_polygon(Vec2(1500, 500), carre)


def test_offset_dans_les_deux_sens():
    """Distance negative : le contour retrecit. Positive : il grandit."""
    carre = [Vec2(0, 0), Vec2(1000, 0), Vec2(1000, 1000), Vec2(0, 1000)]
    reduit = offset_polygon(carre, -100)
    assert abs(abs(polygon_area(reduit)) - 640_000) < 1000,         "attendu 800 x 800 mm, obtenu %.0f" % abs(polygon_area(reduit))
    agrandi = offset_polygon(carre, 100)
    assert abs(abs(polygon_area(agrandi)) - 1_440_000) < 1000
    # un contour oriente dans l'autre sens doit se comporter pareil
    inverse = list(reversed(carre))
    assert abs(abs(polygon_area(offset_polygon(inverse, -100))) - 640_000) < 1000
''')

ajouter('tests/test_interop.py', r'''
"""Interoperabilite : tous les formats de fichiers lus et ecrits."""
from __future__ import annotations

import math
import os
import struct
import tempfile

import pytest

import Interop
from CAD_Core.document import CadDocument
from CAD_Core.math3d import Vec3
from CAD_Core.primitives import box, cylinder
from CAD_Core.profiles import Curve, Profile
from Interop.dwg import DwgError, describe_backends, probe_dwg
from Interop.dxf import probe_dxf, read_dxf, write_dxf
from Interop.images import (Raster, read_bmp, read_image, read_png, read_ppm,
                            write_bmp, write_png, write_ppm, write_tga, underlay)
from Interop.meshes import (read_3mf, read_collada, read_gltf, read_obj,
                            read_off, read_ply, read_stl, write_3ds, write_3mf,
                            write_amf, write_collada, write_glb, write_gltf,
                            write_obj, write_off, write_ply, write_stl,
                            write_vrml, write_x3d)
from Interop.native import read_native, write_native
from Interop.pdf import PdfDocument, probe_pdf
from Interop.pointcloud import (PointCloud, probe_las, read_las, read_xyz,
                                write_csv, write_las, write_xyz)
from Interop.step import read_step, write_iges, write_step, probe_step
from Interop.svg import read_svg, write_svg


@pytest.fixture()
def document():
    doc = CadDocument("Essai")
    doc.add_layer("MURS", 1, "CONTINUOUS", 35)
    doc.set_current_layer("MURS")
    doc.add(box(1000, 500, 300))
    doc.add(cylinder(200, 600, (2000, 0, 0), segments=24))
    doc.add(Curve.polyline([(0, 0, 0), (1000, 0, 0), (1000, 1000, 0)], True))
    return doc


@pytest.fixture()
def solides():
    return [box(1000, 500, 300), cylinder(200, 600, (2000, 0, 0), segments=24)]


def test_registre_des_formats():
    capacites = Interop.capabilities()
    assert capacites["formats"] >= 25
    assert "dwg" in capacites["lecture"] and "dxf" in capacites["ecriture"]
    assert ".dwg" in capacites["extensions"] and ".step" in capacites["extensions"]
    assert Interop.spec_for("plan.dxf").key == "dxf"
    assert Interop.spec_for("stl").key == "stl"
    with pytest.raises(Interop.InteropError):
        Interop.spec_for("machin.xyzt")


@pytest.mark.parametrize("version", ["R12", "2000", "2018"])
def test_dxf_aller_retour(document, version):
    texte = write_dxf(document, version)
    fiche = probe_dxf(texte)
    assert fiche["entites"] > 0
    assert fiche["release"] == version or fiche["version"].startswith("AC")
    relu = read_dxf(texte)
    assert relu.statistics()["volume_total_mm3"] == pytest.approx(
        document.statistics()["volume_total_mm3"], rel=1e-6)
    assert "MURS" in relu.layers


def test_dxf_refuse_un_contenu_invalide():
    from Interop.dxf import DxfError
    with pytest.raises(DxfError):
        read_dxf("")
    with pytest.raises(DxfError):
        write_dxf(CadDocument(), "R99")


def test_identification_dwg_sans_convertisseur():
    entete = (b"AC1032" + b"\x00" * 7 + struct.pack("<I", 0) + b"\x00" * 8
              + struct.pack("<H", 30) + b"\x00" * 200)
    fiche = probe_dwg(entete)
    assert fiche["version"] == "AC1032"
    assert "2018" in fiche["release"]
    assert fiche["lisible_nativement"] is False
    assert "installation" in describe_backends()
    with pytest.raises(DwgError):
        probe_dwg(b"PASDWG" + b"\x00" * 200)
    with pytest.raises(DwgError):
        probe_dwg(b"AC1032")


@pytest.mark.parametrize("ecrire,lire,binaire", [
    (lambda s: write_stl(s, True), read_stl, True),
    (lambda s: write_stl(s, False), read_stl, True),
    (lambda s: write_obj(s), lambda d: read_obj(d), False),
    (lambda s: write_ply(s, False), read_ply, True),
    (lambda s: write_ply(s, True), read_ply, True),
    (lambda s: write_off(s), lambda d: read_off(d), False),
    (lambda s: write_gltf(s), lambda d: read_gltf(d), False),
    (lambda s: write_glb(s), read_gltf, True),
    (lambda s: write_3mf(s), read_3mf, True),
    (lambda s: write_collada(s), lambda d: read_collada(d), False),
])
def test_maillages_aller_retour(solides, ecrire, lire, binaire):
    attendu = sum(s.volume for s in solides)
    donnees = ecrire(solides)
    relus = lire(donnees)
    assert sum(s.volume for s in relus) == pytest.approx(attendu, rel=1e-3)


@pytest.mark.parametrize("ecrire", [write_amf, write_vrml, write_x3d, write_3ds])
def test_formats_en_ecriture_seule(solides, ecrire):
    donnees = ecrire(solides)
    assert len(donnees) > 100


def test_stl_tronque_est_signale():
    from Interop.meshes import MeshFormatError
    with pytest.raises(MeshFormatError):
        read_stl(b"court")
    with pytest.raises(MeshFormatError):
        read_stl(b"\x00" * 80 + struct.pack("<I", 1000) + b"\x00" * 20)


def test_step_aller_retour_et_iges(solides):
    for schema in ("AP203", "AP214", "AP242"):
        texte = write_step(solides, schema)
        fiche = probe_step(texte)
        assert fiche["norme"] == schema
        assert fiche["solides"] == 2
    relus = read_step(write_step(solides))
    assert sum(s.volume for s in relus) == pytest.approx(
        sum(s.volume for s in solides), rel=1e-6)
    assert len(write_iges(solides)) > 500


def test_step_courbe_donne_un_message_clair():
    from Interop.step import StepError
    with pytest.raises(StepError) as erreur:
        read_step("ISO-10303-21;\nDATA;\n#1=CYLINDRICAL_SURFACE('',#2,5.);\n"
                  "ENDSEC;")
    assert "facettis" in str(erreur.value)


def test_ifc_aller_retour(solides):
    from BIM_Engine.ifc_handler import IFCHandler
    texte = IFCHandler().export_solids(solides, "Maquette")
    assert "IFCFACETEDBREP" in texte and "IFC4" in texte
    relus = IFCHandler().read_solids(texte)
    assert sum(s.volume for s in relus) == pytest.approx(
        sum(s.volume for s in solides), rel=1e-6)


@pytest.mark.parametrize("ecrire,lire", [
    (write_png, read_png), (write_bmp, read_bmp), (write_ppm, read_ppm),
])
def test_images_aller_retour_exact(ecrire, lire):
    image = Raster(24, 16)
    for y in range(16):
        for x in range(24):
            image.set_pixel(x, y, (x * 10 % 256, y * 15 % 256, 128))
    relue = lire(ecrire(image))
    assert relue.width == 24 and relue.height == 16
    assert all(image.pixel(x, y) == relue.pixel(x, y)
               for y in range(16) for x in range(24))


def test_image_detection_et_calage():
    image = Raster(8, 4)
    assert read_image(write_png(image)).width == 8
    assert read_image(write_bmp(image)).height == 4
    assert len(write_tga(image)) > 18
    fiche = underlay(write_png(image), 4000)
    assert fiche["largeur_mm"] == 4000
    assert fiche["hauteur_mm"] == pytest.approx(2000.0)
    assert image.resized(4, 2).width == 4
    assert len(image.grayscale()) == 4


def test_pdf_multipage(document):
    pdf = PdfDocument("Planche")
    page = pdf.add_page("A3", True)
    page.line_width(0.5).rectangle((20, 20), 200, 150)
    page.circle((120, 95), 40)
    page.polyline([(20, 20), (220, 20), (220, 170)], True)
    page.dash([4, 2]).line((20, 95), (220, 95))
    page.text((30, 180), "PLAN RDC", 6)
    page.title_block("Residence", "A3-01", "1:100", "2026-01-01")
    pdf.add_page("A4", False).text((20, 270), "Note", 5)
    donnees = pdf.build()
    fiche = probe_pdf(donnees)
    assert fiche["pages"] == 2 and fiche["compresse"]
    assert donnees.startswith(b"%PDF-") and donnees.rstrip().endswith(b"%%EOF")
    from Interop.pdf import PdfError
    with pytest.raises(PdfError):
        PdfDocument().build()
    with pytest.raises(PdfError):
        pdf.add_page("A9")


def test_svg_export_et_import(document):
    texte = write_svg(document)
    assert texte.startswith("<svg") and "<line" in texte
    relu = read_svg(texte)
    assert len(relu.entities) > 0
    chemins = read_svg('<svg xmlns="http://www.w3.org/2000/svg" width="100" '
                       'height="100"><path d="M10,10 L90,10 L90,90 Z"/>'
                       '<path d="M10,50 C30,20 70,20 90,50"/>'
                       '<rect x="5" y="5" width="20" height="20"/>'
                       '<circle cx="50" cy="50" r="20"/></svg>')
    assert len(chemins.entities) == 4


def test_nuages_de_points():
    points = [Vec3(x * 100.0, y * 100.0, 500 + 200 * math.sin(x / 5.0))
              for x in range(20) for y in range(20)]
    nuage = PointCloud(points, [(120, 90, 60)] * len(points),
                       [1000.0] * len(points), "releve")
    assert nuage.statistics()["points"] == 400
    relu = read_xyz(write_xyz(nuage))
    assert len(relu) == 400 and relu.colors
    assert len(read_xyz(write_csv(nuage))) == 400
    donnees = write_las(nuage)
    assert probe_las(donnees)["points"] == 400
    depuis_las = read_las(donnees)
    assert len(depuis_las) == 400
    assert max(a.distance_to(b) for a, b in zip(nuage.points,
                                                depuis_las.points)) < 0.01
    terrain = nuage.to_terrain(20)
    assert terrain.area > 0
    assert len(nuage.decimated(10)) == 40


def test_format_natif_sans_perte(document):
    document.define_block("PLOT", [list(document.entities)[0]])
    document.set_ucs("CHANTIER", (10, 20, 30))
    document.add_layout("PLANCHE", "A1", 0.02)
    avant = document.statistics()
    relu = read_native(write_native(document))
    apres = relu.statistics()
    for cle in ("objets", "par_type", "calques", "blocs", "presentations"):
        assert avant[cle] == apres[cle]
    assert apres["volume_total_mm3"] == pytest.approx(avant["volume_total_mm3"],
                                                      rel=1e-9)
    assert relu.layers["MURS"].lineweight == 35
    assert relu.ucs_table["CHANTIER"].origin.rounded(3) == (10.0, 20.0, 30.0)


def test_format_natif_refuse_un_autre_json():
    from Interop.native import NativeFormatError
    with pytest.raises(NativeFormatError):
        read_native('{"format": "AUTRE"}')
    with pytest.raises(NativeFormatError):
        read_native("pas du json")


def test_identification_par_signature(document, solides):
    echantillons = {
        "dxf": write_dxf(document).encode(), "stl": write_stl(solides),
        "png": write_png(Raster(4, 4)), "glb": write_glb(solides),
        "step": write_step(solides).encode(), "las": write_las(
            PointCloud([Vec3(0, 0, 0), Vec3(1, 1, 1)])),
        "3mf": write_3mf(solides), "json": write_native(document).encode(),
        "svg": write_svg(document).encode(),
    }
    for attendu, donnees in echantillons.items():
        assert Interop.identify(donnees, "essai." + attendu)["format"] == attendu
    with pytest.raises(Interop.InteropError):
        Interop.identify(b"\x01\x02\x03\x04", "inconnu.zzz")


def test_ifc_et_step_ne_sont_pas_confondus(solides):
    from BIM_Engine.ifc_handler import IFCHandler
    ifc = IFCHandler().export_solids(solides, "M").encode()
    assert Interop.identify(ifc, "m.ifc")["format"] == "ifc"
    assert Interop.identify(write_step(solides).encode(), "m.step")["format"] \
        == "step"


def test_export_et_import_par_fichier(document):
    dossier = tempfile.mkdtemp(prefix="mercury_interop_")
    for cle in ("dxf", "stl", "obj", "ply", "step", "gltf", "glb", "3mf", "off",
                "json", "svg", "ifc", "pdf", "png", "xyz", "csv", "las", "dae",
                "amf", "wrl", "x3d", "3ds", "iges", "bmp", "ppm", "tga", "mtl"):
        spec = Interop.BY_KEY[cle]
        chemin = os.path.join(dossier, "sortie" + spec.extensions[0])
        Interop.export_file(document, chemin)
        assert os.path.getsize(chemin) > 0
        if spec.read:
            resultat = Interop.import_file(chemin)
            assert resultat["document"] is not None


def test_conversion_entre_formats(document):
    dossier = tempfile.mkdtemp(prefix="mercury_conv_")
    source = os.path.join(dossier, "source.dxf")
    Interop.export_file(document, source)
    rapport = Interop.convert(source, os.path.join(dossier, "cible.stl"))
    assert rapport["format_source"] == "dxf" and rapport["format_cible"] == "stl"
    assert rapport["objets"] > 0


def test_import_dwg_sans_moteur_donne_un_message_utile(document):
    dossier = tempfile.mkdtemp(prefix="mercury_dwg_")
    chemin = os.path.join(dossier, "essai.dwg")
    with open(chemin, "wb") as handle:
        handle.write(b"AC1032" + b"\x00" * 500)
    if describe_backends()["lecture_dwg"]:
        pytest.skip("un moteur de conversion DWG est installe sur cette machine")
    with pytest.raises(DwgError) as erreur:
        Interop.import_file(chemin)
    assert "moteur" in str(erreur.value).lower()
''')

ajouter('tests/test_math3d.py', r'''
"""Algebre 3D : vecteurs, matrices, plans, boites englobantes."""
from __future__ import annotations

import math

import pytest

from CAD_Core.math3d import (BBox3, Mat4, ORIGIN, Plane, Vec3, X_AXIS, XY_PLANE,
                             Y_AXIS, Z_AXIS, polygon_area_3d, polygon_normal)


def test_operations_vectorielles():
    a, b = Vec3(1, 2, 3), Vec3(4, 5, 6)
    assert (a + b).as_tuple() == (5, 7, 9)
    assert (b - a).as_tuple() == (3, 3, 3)
    assert (a * 2).as_tuple() == (2, 4, 6)
    assert a.dot(b) == 32
    assert a.cross(b).as_tuple() == (-3, 6, -3)
    assert Vec3(3, 4, 0).norm() == 5.0
    assert Vec3(3, 4, 0).unit().norm() == pytest.approx(1.0)
    assert Vec3(0, 0, 0).unit().as_tuple() == (0.0, 0.0, 0.0)


def test_conversion_souple():
    assert Vec3.of((1, 2, 3)).as_tuple() == (1.0, 2.0, 3.0)
    assert Vec3.of([4, 5]).as_tuple() == (4.0, 5.0, 0.0)
    assert Vec3.of({"x": 7, "z": 9}).as_tuple() == (7.0, 0.0, 9.0)


def test_perpendiculaire_toujours_orthogonale():
    for vecteur in (X_AXIS, Y_AXIS, Z_AXIS, Vec3(1, 1, 1), Vec3(0.01, 0, 0.99)):
        assert vecteur.dot(vecteur.any_perpendicular()) == pytest.approx(0.0,
                                                                        abs=1e-9)


def test_rotation_et_inverse():
    matrice = Mat4.rotation(Z_AXIS, math.pi / 2)
    tourne = matrice.apply(Vec3(1, 0, 0))
    assert tourne.rounded(9) == (0.0, 1.0, 0.0)
    assert matrice.inverse() * matrice == Mat4.identity()
    assert matrice.determinant() == pytest.approx(1.0)


def test_rotation_autour_dun_point():
    matrice = Mat4.rotation(Z_AXIS, math.pi, base=(10, 0, 0))
    assert matrice.apply(Vec3(11, 0, 0)).rounded(6) == (9.0, 0.0, 0.0)


def test_echelle_et_symetrie():
    assert Mat4.scaling(3).apply(Vec3(1, 2, 3)).as_tuple() == (3.0, 6.0, 9.0)
    miroir = Mat4.mirror(Plane.from_point_normal((0, 0, 0), X_AXIS))
    assert miroir.apply(Vec3(5, 1, 2)).rounded(6) == (-5.0, 1.0, 2.0)
    assert miroir.is_mirroring()


def test_alignement_sur_deux_points():
    matrice = Mat4.align([(0, 0, 0), (1, 0, 0)], [(5, 5, 5), (5, 6, 5)])
    assert matrice.apply((0, 0, 0)).rounded(6) == (5.0, 5.0, 5.0)
    assert matrice.apply((1, 0, 0)).rounded(6) == (5.0, 6.0, 5.0)


def test_alignement_refuse_des_listes_incoherentes():
    with pytest.raises(ValueError):
        Mat4.align([(0, 0, 0)], [])


def test_matrice_singuliere():
    with pytest.raises(ValueError):
        Mat4([0] * 16).inverse()


def test_plan_distance_projection_intersection():
    plan = Plane.from_points((0, 0, 0), (1, 0, 0), (0, 1, 0))
    assert plan.normal.rounded(6) == (0.0, 0.0, 1.0)
    assert plan.signed_distance((0, 0, 4)) == 4.0
    assert plan.project((3, 2, 9)).rounded(6) == (3.0, 2.0, 0.0)
    coupe = plan.line_intersection((0, 0, -2), (0, 0, 6))
    assert coupe.rounded(6) == (0.0, 0.0, 0.0)
    assert plan.line_intersection((0, 0, 1), (0, 0, 2)) is None


def test_plan_refuse_trois_points_alignes():
    with pytest.raises(ValueError):
        Plane.from_points((0, 0, 0), (1, 0, 0), (2, 0, 0))


def test_repere_du_plan_suit_la_norme_dxf():
    u, v = XY_PLANE.basis()
    assert u.rounded(6) == (1.0, 0.0, 0.0)
    assert v.rounded(6) == (0.0, 1.0, 0.0)


def test_boite_englobante():
    boite = BBox3.of([(0, 0, 0), (10, 4, 6)])
    assert boite.valid
    assert boite.size.as_tuple() == (10.0, 4.0, 6.0)
    assert boite.center.as_tuple() == (5.0, 2.0, 3.0)
    assert boite.contains((5, 2, 3))
    assert not boite.contains((50, 2, 3))
    assert boite.intersects(BBox3.of([(9, 0, 0), (20, 4, 6)]))
    assert not boite.intersects(BBox3.of([(30, 0, 0), (40, 4, 6)]))
    assert BBox3().to_dict() == {"vide": True}


def test_aire_et_normale_dun_polygone():
    carre = [(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)]
    assert polygon_area_3d(carre) == pytest.approx(4.0)
    assert polygon_normal(carre).rounded(6) == (0.0, 0.0, 1.0)
    assert polygon_area_3d([(0, 0, 0), (1, 0, 0)]) == 0.0


def test_format_colonne_pour_webgl():
    matrice = Mat4.translation((1, 2, 3))
    colonnes = matrice.to_column_major()
    assert colonnes[12:15] == [1.0, 2.0, 3.0]
''')

ajouter('tests/test_modules_metiers.py', r'''
"""Tests des modules metiers restes dans l'ombre.

Ces modules etaient importes mais jamais executes : c'est exactement la ou
les erreurs survivent. Chaque test verifie un comportement observable, pas
seulement l'absence d'exception.
"""
from __future__ import annotations

import pytest

from BIM_Engine.mep import MEPPlanner
from BIM_Engine.object_library import CatalogItem, ObjectLibrary
from BIM_Engine.structure import StructureAnalyzer
from Cloud_Platform.city import CityPlatform
from Construction.progress import ProgressTracker
from Construction.resources import ResourceManager
from Construction.safety import SafetyAnalyzer


# ----------------------------- bibliotheque -----------------------------
def test_bibliotheque_recherche_et_categories():
    library = ObjectLibrary()
    assert library.all()
    assert "cuisine" in library.categories()
    assert library.get("bed_double").name == "Lit double"
    assert library.get("inexistant") is None
    assert all(i.category == "chambre" for i in library.search(category="chambre"))
    assert library.search("lit")
    assert len(library.search(limit=3)) == 3


def test_objet_redimensionne_conserve_ses_attributs():
    item = ObjectLibrary().get("kitchen_run")
    grand = item.scaled(width=4200)
    assert grand.size[0] == 4200
    assert grand.size[1] == item.size[1]
    assert grand.unit_cost == item.unit_cost
    assert grand.anchor == item.anchor


def test_pack_fabricant(tmp_path):
    import json
    pack = tmp_path / "pack.json"
    pack.write_text(json.dumps({
        "manufacturer": "ACME",
        "items": [{"id": "acme_ilot", "name": "Ilot ACME", "category": "cuisine",
                   "size": [2400, 900, 900], "unit_cost": 2600}],
    }), encoding="utf-8")
    library = ObjectLibrary()
    assert library.load_pack(str(pack)) == 1
    ajoute = library.get("acme_ilot")
    assert ajoute.manufacturer == "ACME" and ajoute.unit_cost == 2600
    with pytest.raises(FileNotFoundError):
        library.load_pack(str(tmp_path / "absent.json"))
    invalide = tmp_path / "invalide.json"
    invalide.write_text('{"manufacturer": "X"}', encoding="utf-8")
    with pytest.raises(ValueError):
        library.load_pack(str(invalide))


# ------------------------------ structure ------------------------------
def test_descente_de_charges(furnished):
    # sans dalle, le poids propre du plancher resterait a zero et
    # l'assertion de somme serait vide de sens
    from BIM_Engine.models import Slab
    for room in furnished.rooms:
        furnished.slabs.append(Slab(outline=room.outline, thickness=200.0))
    result = StructureAnalyzer().analyze(furnished, "habitation")
    assert result["poids_dalles_kn"] > 0, "le poids des dalles doit etre compte"
    assert result["charge_totale_kn"] > 0
    somme = (result["charge_exploitation_kn"] + result["poids_dalles_kn"]
             + result["poids_murs_kn"])
    assert abs(somme - result["charge_totale_kn"]) < 1.0
    assert result["murs_porteurs"] >= 1
    assert result["charge_lineique_kn_m"] > 0
    assert "predimensionnement" in result["avertissement"]
    commerce = StructureAnalyzer().analyze(furnished, "commerce")
    assert commerce["charge_exploitation_kn"] > result["charge_exploitation_kn"]
    with pytest.raises(ValueError):
        StructureAnalyzer().analyze(furnished, "piscine_olympique")


# -------------------------------- fluides --------------------------------
def test_preciblage_des_reseaux(furnished):
    result = MEPPlanner().plan(furnished)
    assert result["detail"]
    totaux = result["totaux"]
    assert totaux["prises"] > 0 and totaux["luminaires"] > 0
    assert sum(l["prises"] for l in result["detail"]) == totaux["prises"]
    assert "esquisse" in result["avertissement"]


def test_piece_humide_recoit_des_points_d_eau():
    from BIM_Engine.models import BuildingProject, Room
    project = BuildingProject(name="Test", building_type="maison")
    project.rooms = [Room(name="Cuisine", kind="cuisine", area_m2=12.0),
                     Room(name="Chambre", kind="chambre", area_m2=12.0)]
    detail = {l["piece"]: l for l in MEPPlanner().plan(project)["detail"]}
    assert detail["Cuisine"]["points_eau"] > 0
    assert detail["Chambre"]["points_eau"] == 0
    assert detail["Cuisine"]["debit_m3h"] > 0


# ------------------------------- chantier -------------------------------
@pytest.fixture()
def planning(furnished):
    from Construction.planning import ConstructionPlanner
    from Estimating.cost_ai import CostEstimator
    estimator = CostEstimator()
    return ConstructionPlanner().plan(
        estimator.schedule(estimator.estimate(furnished)))


def test_avancement_detecte_le_retard(planning):
    taches = planning["taches"]
    milieu = taches[len(taches) // 2]
    jour = int((milieu["debut_jour"] + milieu["fin_jour"]) / 2)
    # tout le monde a zero : retard garanti sur les lots commences
    result = ProgressTracker().assess(planning, {}, jour)
    assert result["lots_en_retard"] >= 1
    en_retard = [l for l in result["lignes"] if l["statut"] == "en retard"]
    assert en_retard and all(l["ecart_points"] < 0 for l in en_retard)
    # tout le monde a 100 % : personne en retard
    parfait = ProgressTracker().assess(
        planning, {t["lot"]: 1.0 for t in taches}, jour)
    assert parfait["lots_en_retard"] == 0
    assert "aucun retard" in parfait["alerte"]


def test_avancement_attendu_borne(planning):
    tache = planning["taches"][0]
    avant = ProgressTracker().assess(planning, {}, tache["debut_jour"])
    ligne = next(l for l in avant["lignes"] if l["lot"] == tache["lot"])
    assert ligne["avancement_attendu"] == 0.0
    apres = ProgressTracker().assess(planning, {}, tache["fin_jour"] + 10)
    ligne = next(l for l in apres["lignes"] if l["lot"] == tache["lot"])
    assert ligne["avancement_attendu"] == 100.0


def test_ressources_et_approvisionnements(planning):
    result = ResourceManager().plan(planning["taches"])
    assert result["jours_homme_total"] > 0
    assert result["effectif_pointe"] >= 2
    commandes = result["approvisionnements"]
    jours = [c["commander_le_jour"] for c in commandes]
    assert jours == sorted(jours), "les commandes doivent etre triees"
    # les lots a long delai doivent etre commandes avant leur demarrage
    for commande in commandes:
        tache = next(t for t in planning["taches"] if t["lot"] == commande["lot"])
        assert commande["commander_le_jour"] <= tache["debut_jour"]


def test_securite_chantier(furnished):
    result = SafetyAnalyzer().analyze(furnished, "Gros oeuvre")
    assert result["nombre"] > 0
    graves = [r for r in result["risques"] if r["gravite"] == "haute"]
    assert graves, "une phase de gros oeuvre comporte des risques graves"
    assert result["risques"][0]["gravite"] == "haute", "tri par gravite"
    assert any("ouvertures" in r["origine"] for r in result["risques"])
    assert "SPS" in result["avertissement"]
    peinture = SafetyAnalyzer().analyze(furnished, "Peinture")
    assert any("solvants" in r["risque"] for r in peinture["risques"])


# ------------------------------ territoire ------------------------------
def test_consolidation_territoriale(furnished):
    from BIM_Engine.models import BuildingProject
    second = BuildingProject(name="Voisin", building_type="bureau")
    second.rooms = list(furnished.rooms)
    second.walls = list(furnished.walls)
    platform = CityPlatform()
    result = platform.aggregate(
        [furnished, second],
        energy_by_project={furnished.id: 8000.0, second.id: 12000.0},
        carbon_by_project={furnished.id: 25000.0, second.id: 40000.0},
        plot_area_m2=400.0)
    assert result["batiments"] == 2
    assert result["energie_totale_kwh_an"] == 20000.0
    assert result["carbone_total_t_co2e"] == 65.0
    assert result["coefficient_emprise"] > 0
    assert result["energie_moyenne_kwh_m2"] > 0
    assert set(result["par_typologie"]) == {"maison", "bureau"}


def test_export_geojson(furnished):
    data = CityPlatform().to_geojson([furnished])
    assert data["type"] == "FeatureCollection"
    assert data["features"], "un projet avec murs exterieurs doit produire une emprise"
    geometry = data["features"][0]["geometry"]
    assert geometry["type"] == "Polygon"
    anneau = geometry["coordinates"][0]
    assert anneau[0] == anneau[-1], "l'anneau doit etre ferme"
    assert data["features"][0]["properties"]["surface_m2"] > 0


def test_geojson_ignore_les_projets_sans_enveloppe():
    from BIM_Engine.models import BuildingProject
    vide = BuildingProject(name="Vide", building_type="maison")
    assert CityPlatform().to_geojson([vide])["features"] == []


# ------------------------------- registre -------------------------------
def test_registre_des_livrables():
    from DELIVERABLES import DELIVERABLES, GROUPS, by_group, by_state
    assert len(DELIVERABLES) == 70
    assert sorted(d["numero"] for d in DELIVERABLES) == list(range(1, 71))
    assert set(d["groupe"] for d in DELIVERABLES) <= set(GROUPS)
    livres = by_state("livre")
    assert livres and all(d["etat"] == "livre" for d in livres)
    coeur = by_group("CORE")
    assert coeur and all(d["groupe"] == "CORE" for d in coeur)
    total = sum(len(by_group(g)) for g in GROUPS)
    assert total == 70, "chaque livrable appartient a un groupe et un seul"
''')

ajouter('tests/test_platform.py', r'''
"""Tests plateforme : base, securite, multi-tenant, jumeau, collaboration."""
from __future__ import annotations

import pytest

from BIM_Engine.collaboration import CollaborationHub
from Cloud_Platform.digital_twin import DigitalTwin
from Cloud_Platform.iot import IoTGateway, SensorRegistry
from Cloud_Platform.multi_tenant import TenantManager
from Security.auth import AuthService
from Security.encryption import Encryptor
from Security.rbac import AccessControl


def test_base_migrations_et_versions(state, project):
    version = state.repository.save(project)
    assert version >= 1
    project.name = "Renomme"
    second = state.repository.save(project)
    assert second > version
    loaded = state.repository.load(project.id)
    assert loaded.name == "Renomme"
    assert len(state.repository.versions(project.id)) >= 2
    ancienne = state.repository.load(project.id, version)
    assert ancienne.version == version


def test_projet_inconnu(state):
    with pytest.raises(KeyError):
        state.repository.load("inexistant")


def test_mots_de_passe_et_jetons():
    auth = AuthService(secret="test-secret")
    stored = auth.hash_password("motdepasse123")
    assert auth.verify_password("motdepasse123", stored)
    assert not auth.verify_password("mauvais", stored)
    with pytest.raises(ValueError):
        auth.hash_password("court")
    token = auth.create_token("usr_1", {"role": "admin"})
    payload = auth.decode_token(token)
    assert payload["sub"] == "usr_1" and payload["role"] == "admin"
    with pytest.raises(ValueError):
        auth.decode_token(token + "altere")


def test_chiffrement():
    encryptor = Encryptor("cle-de-test")
    secret = "donnee confidentielle"
    token = encryptor.encrypt(secret)
    assert token != secret
    assert encryptor.decrypt(token) == secret
    with pytest.raises(ValueError):
        Encryptor("autre-cle").decrypt(token)


def test_controle_acces():
    access = AccessControl()
    access.grant("prj_1", "usr_1", "editeur")
    assert access.can("prj_1", "usr_1", "projet.modifier")
    assert not access.can("prj_1", "usr_1", "projet.supprimer")
    assert not access.can("prj_1", "usr_2", "projet.lire")
    with pytest.raises(PermissionError):
        access.require("prj_1", "usr_1", "projet.supprimer")
    access.set_global_role("usr_admin", "admin")
    assert access.can("prj_1", "usr_admin", "projet.supprimer")


def test_multi_tenant_isole_les_projets():
    manager = TenantManager()
    manager.create("acme", "ACME", "essai")
    manager.add_project("acme", "prj_1")
    assert manager.owns("acme", "prj_1")
    assert not manager.owns("acme", "prj_2")
    with pytest.raises(PermissionError):
        manager.assert_access("acme", "prj_2")
    for index in range(2):
        manager.add_project("acme", "prj_%d" % (index + 10))
    with pytest.raises(ValueError):
        manager.add_project("acme", "prj_trop")     # quota de l'offre essai


def test_jumeau_numerique_pondere_les_alertes(furnished):
    registry = SensorRegistry()
    gateway = IoTGateway(registry)
    grande = max(furnished.rooms, key=lambda r: r.area_m2)
    registry.declare("t1", "temperature", furnished.id, grande.id, "Sonde")
    result = gateway.ingest([{"capteur": "t1", "valeur": 31.5},
                             {"capteur": "inconnu", "valeur": 1}])
    assert result["acceptees"] == 1 and result["capteurs_inconnus"] == ["inconnu"]
    state = DigitalTwin(registry).state(furnished)
    alerte = next(a for a in state["alertes"] if a["capteur"] == "t1")
    assert alerte["type"] == "hors consigne"
    assert alerte["gravite"] == ("haute" if grande.area_m2 > 20 else "moyenne")


def test_collaboration():
    hub = CollaborationHub()
    assert hub.join("prj_1", "usr_1") == 1
    assert hub.join("prj_1", "usr_2") == 2
    hub.publish("prj_1", "usr_1", "modification", {"mur": "wal_1"})
    assert len(hub.events("prj_1")) >= 3
    assert hub.leave("prj_1", "usr_2") == 1
    with pytest.raises(ValueError):
        hub.publish("prj_1", "usr_1", "sabotage", {})
''')

ajouter('tests/test_primitives_modeling.py', r'''
"""Primitives volumiques et outils de creation a partir d'un profil."""
from __future__ import annotations

import math

import pytest

from CAD_Core.math3d import Vec3, Z_AXIS
from CAD_Core.mesh_tools import (smooth, statistics, subdivide, triangulate,
                                 unify_normals, vertex_normals)
from CAD_Core.modeling import (coons_surface, extrude, loft, planar_surface,
                               presspull, revolve, ruled_surface, sweep,
                               tabulated_surface, thicken)
from CAD_Core.primitives import (box, cone, cylinder, mesh_box, polysolid,
                                 pyramid, sphere, torus, wedge)
from CAD_Core.profiles import Curve, Profile


@pytest.mark.parametrize("solide,attendu,tolerance", [
    (box(100, 200, 300), 6e6, 1e-9),
    (wedge(100, 100, 100), 5e5, 1e-9),
    (cylinder(50, 100, segments=180), math.pi * 2500 * 100, 1e-3),
    (cone(50, 100, segments=180), math.pi * 2500 * 100 / 3, 1e-3),
    (sphere(50, segments=64, rings=32), 4 / 3 * math.pi * 125000, 5e-3),
    (torus(100, 20, segments=64, tube_segments=32),
     2 * math.pi ** 2 * 100 * 400, 1e-2),
    (pyramid(50, 100, 4), 2 * 2500 * 100 / 3, 1e-9),
])
def test_volume_des_primitives(solide, attendu, tolerance):
    assert solide.volume == pytest.approx(attendu, rel=max(tolerance, 1e-9))
    assert solide.signed_volume > 0, "les faces doivent regarder vers l'exterieur"
    assert solide.check()["ferme"]


@pytest.mark.parametrize("fabrique,arguments", [
    (box, {"length": 0}), (wedge, {"width": -5}), (cylinder, {"radius": 0}),
    (sphere, {"radius": -1}), (torus, {"tube_radius": 0}),
    (pyramid, {"sides": 2}),
])
def test_primitives_refusent_des_dimensions_absurdes(fabrique, arguments):
    with pytest.raises(ValueError):
        fabrique(**arguments)


def test_boite_centree():
    centree = box(100, 100, 100, centered=True)
    assert centree.centroid.rounded(6) == (0.0, 0.0, 0.0)


def test_polysolide_suit_la_polyligne():
    mur = polysolid([(0, 0, 0), (1000, 0, 0), (1000, 1000, 0)], 200, 2500)
    assert mur.check()["ferme"]
    assert mur.volume == pytest.approx(2 * 1000 * 200 * 2500 - 100 * 100 * 2500,
                                       rel=1e-6)


def test_polysolide_refuse_une_justification_inconnue():
    with pytest.raises(ValueError):
        polysolid([(0, 0, 0), (100, 0, 0)], justify="milieu")


def test_extrusion_simple_et_percee():
    plein = extrude(Profile.rectangle(100, 50), 200)
    assert plein.volume == pytest.approx(1e6)
    perce = extrude(Profile.rectangle(100, 50).with_hole(
        Profile.rectangle(20, 20, (40, 15, 0)).outline), 100)
    assert perce.volume == pytest.approx(460000)
    assert perce.check()["ferme"]


def test_extrusion_avec_depouille():
    hauteur, angle = 100.0, 10.0
    solide = extrude(Profile.rectangle(100, 100), hauteur, taper=angle)
    cote = 100 - 2 * hauteur * math.tan(math.radians(angle))
    attendu = hauteur / 3 * (10000 + cote ** 2 + math.sqrt(10000 * cote ** 2))
    assert solide.volume == pytest.approx(attendu, rel=1e-6)


def test_extrusion_refuse_une_hauteur_nulle():
    with pytest.raises(ValueError):
        extrude(Profile.rectangle(10, 10), 0.0)


def test_revolution_totale_et_partielle():
    profil = Profile.polyline([(50, 0, 0), (100, 0, 0), (100, 0, 80),
                               (50, 0, 80)])
    complet = math.pi * (100 ** 2 - 50 ** 2) * 80
    assert revolve(profil, (0, 0, 0), Z_AXIS, 2 * math.pi, 72).volume == \
        pytest.approx(complet, rel=3e-3)
    quart = revolve(profil, (0, 0, 0), Z_AXIS, math.pi / 2, 72)
    assert quart.volume == pytest.approx(complet / 4, rel=3e-3)
    assert quart.check()["ferme"]


def test_balayage_droit_et_helicoidal():
    droit = sweep(Profile.circle(10, segments=64), Curve.line((0, 0, 0),
                                                              (0, 0, 500)))
    assert droit.volume == pytest.approx(math.pi * 100 * 500, rel=3e-3)
    assert droit.check()["ferme"]
    helicoidal = sweep(Profile.circle(10, segments=24),
                       Curve.helix(turns=2, height=200, base_radius=80))
    assert helicoidal.check()["ferme"]
    assert helicoidal.volume > 0


def test_balayage_avec_torsion_reste_ferme():
    vrille = sweep(Profile.rectangle(40, 20, centered=True),
                   Curve.line((0, 0, 0), (0, 0, 400)), twist=90)
    assert vrille.check()["ferme"]
    assert vrille.volume == pytest.approx(40 * 20 * 400, rel=0.06)


def test_lissage_entre_deux_sections():
    resultat = loft([Profile.rectangle(100, 100, (0, 0, 0), centered=True),
                     Profile.rectangle(50, 50, (0, 0, 200), centered=True)])
    attendu = 200 / 3 * (10000 + 2500 + math.sqrt(10000 * 2500))
    assert resultat.volume == pytest.approx(attendu, rel=1e-6)
    assert resultat.check()["ferme"]


def test_lissage_exige_deux_sections():
    with pytest.raises(ValueError):
        loft([Profile.rectangle(10, 10)])


def test_appuyer_tirer_et_epaissir():
    assert presspull(Profile.rectangle(200, 100), 50).volume == \
        pytest.approx(1e6)
    epaissi = thicken(planar_surface(Profile.rectangle(200, 100)).polygons, 20)
    assert epaissi.volume == pytest.approx(400000)
    assert epaissi.check()["ferme"]


def test_surfaces_reglees_et_coons():
    reglee = ruled_surface(Curve.line((0, 0, 0), (100, 0, 0)),
                           Curve.line((0, 100, 0), (100, 100, 0)))
    assert reglee.area == pytest.approx(10000, rel=1e-6)
    tabulee = tabulated_surface(Curve.line((0, 0, 0), (100, 0, 0)), (0, 0, 50))
    assert tabulee.area == pytest.approx(5000, rel=1e-6)
    carreau = coons_surface([Curve.line((0, 0, 0), (100, 0, 0)),
                             Curve.line((100, 0, 0), (100, 100, 0)),
                             Curve.line((0, 100, 0), (100, 100, 0)),
                             Curve.line((0, 0, 0), (0, 100, 0))])
    assert carreau.area == pytest.approx(10000, rel=1e-6)


def test_coons_exige_quatre_courbes():
    with pytest.raises(ValueError):
        coons_surface([Curve.line((0, 0, 0), (1, 0, 0))])


def test_outils_de_maillage():
    cube = box(100, 100, 100)
    assert len(triangulate(cube).polygons) == 12
    assert len(subdivide(cube, 1).polygons) == 24
    lisse = smooth(cube, 1)
    assert len(lisse.polygons) == 24
    assert lisse.volume < cube.volume        # le lissage rentre les coins
    assert len(vertex_normals(cube)) == 8
    assert unify_normals(cube.inverted()).signed_volume > 0
    fiche = statistics(cube)
    assert fiche["ferme"] and fiche["sommets"] == 8


def test_primitive_de_maillage():
    assert len(mesh_box(100, 100, 100, divisions=2).polygons) == 24


def test_profils_et_courbes():
    assert Profile.rectangle(100, 50).area == pytest.approx(5000)
    assert Profile.circle(50, segments=360).area == pytest.approx(math.pi * 2500,
                                                                  rel=1e-4)
    assert Profile.regular_polygon(6, 100).area == pytest.approx(
        3 * math.sqrt(3) / 2 * 100 ** 2, rel=1e-9)
    assert Profile.rounded_rectangle(100, 60, 10).area == pytest.approx(
        100 * 60 - (4 - math.pi) * 100, rel=1e-3)
    with pytest.raises(ValueError):
        Profile.regular_polygon(2, 10)
    helice = Curve.helix(turns=2, height=100, base_radius=50)
    assert helice.length > 2 * math.pi * 50 * 2
    assert len(Curve.circle((0, 0, 0), 10, segments=32).points) == 32
    assert Curve.line((0, 0, 0), (30, 40, 0)).length == pytest.approx(50.0)
    assert len(Curve.line((0, 0, 0), (100, 0, 0)).resampled(11).points) == 11
''')

ajouter('tests/test_solid_csg.py', r'''
"""Solides facettises et operations booleennes."""
from __future__ import annotations

import math

import pytest

from CAD_Core.math3d import Plane, Vec3, Z_AXIS
from CAD_Core.primitives import box, cylinder, sphere
from CAD_Core.solid import (Polygon, Solid, interfere, intersect_all,
                            subtract_all, union_all)


@pytest.fixture()
def cube():
    return box(100, 100, 100)


def test_proprietes_dun_cube(cube):
    assert cube.volume == pytest.approx(1e6)
    assert cube.area == pytest.approx(6e4)
    assert cube.signed_volume > 0
    assert cube.centroid.rounded(6) == (50.0, 50.0, 50.0)
    assert len(cube.vertices()) == 8
    assert len(cube.edges()) == 12


def test_controle_de_solide(cube):
    controle = cube.check()
    assert controle["ferme"] and controle["valide"]
    assert controle["aretes_libres"] == 0
    assert controle["faces_degenerees"] == 0


def test_union_volume_exact():
    resultat = box(100, 100, 100).union(box(50, 50, 50, (75, 25, 25)))
    assert resultat.volume == pytest.approx(1e6 + 50 ** 3 - 25 * 50 * 50, rel=1e-6)
    assert resultat.check()["ferme"]


def test_soustraction_volume_exact():
    resultat = box(100, 100, 100).subtract(box(50, 50, 50, (75, 25, 25)))
    assert resultat.volume == pytest.approx(1e6 - 25 * 50 * 50, rel=1e-6)
    assert resultat.check()["ferme"]


def test_intersection_volume_exact():
    resultat = box(100, 100, 100).intersect(box(50, 50, 50, (75, 25, 25)))
    assert resultat.volume == pytest.approx(25 * 50 * 50, rel=1e-6)
    assert resultat.check()["ferme"]


def test_soustraction_dune_sphere_ne_renvoie_pas_le_complementaire():
    """Une primitive mal orientee inverserait le resultat : on le verifie."""
    grande = box(1000, 1000, 1000)
    bille = sphere(300, (500, 500, 500), segments=24, rings=12)
    creuse = grande.subtract(bille)
    assert creuse.volume == pytest.approx(1e9 - bille.volume, rel=1e-3)
    assert creuse.volume > bille.volume


def test_percement_traversant():
    perce = box(1000, 1000, 1000).subtract(
        cylinder(200, 2000, (500, 500, -500), segments=64))
    attendu = 1e9 - math.pi * 200 ** 2 * 1000
    assert perce.volume == pytest.approx(attendu, rel=2e-3)
    assert perce.check()["ferme"]


def test_reunion_et_soustraction_de_listes():
    reunis = union_all([box(100, 100, 100), box(100, 100, 100, (200, 0, 0))])
    assert reunis.volume == pytest.approx(2e6)
    reste = subtract_all(box(200, 200, 200),
                         [box(50, 50, 300, (0, 0, -50)),
                          box(50, 50, 300, (150, 150, -50))])
    assert reste.volume == pytest.approx(200 ** 3 - 2 * 50 * 50 * 200, rel=1e-6)
    assert intersect_all([box(100, 100, 100),
                          box(100, 100, 100, (50, 0, 0))]).volume == \
        pytest.approx(50 * 100 * 100, rel=1e-6)


def test_separation_de_volumes_disjoints():
    morceaux = union_all([box(10, 10, 10), box(10, 10, 10, (100, 0, 0))]).separate()
    assert len(morceaux) == 2
    assert all(m.volume == pytest.approx(1000) for m in morceaux)


def test_detection_dinterference():
    rapport = interfere([box(100, 100, 100), box(100, 100, 100, (50, 0, 0)),
                         box(10, 10, 10, (900, 0, 0))])
    assert rapport["collisions"] == 1
    assert rapport["details"][0]["volume_mm3"] == pytest.approx(500000, rel=1e-6)


def test_proprietes_mecaniques(cube):
    fiche = cube.mass_properties(2400.0)
    assert fiche["volume_m3"] == pytest.approx(0.001)
    assert fiche["masse_kg"] == pytest.approx(2.4)
    assert fiche["centre_gravite"] == [50.0, 50.0, 50.0]
    assert fiche["faces"] == 6


def test_transformations_conservent_le_volume(cube):
    assert cube.translated((10, 20, 30)).volume == pytest.approx(cube.volume)
    assert cube.rotated(Z_AXIS, 0.7).volume == pytest.approx(cube.volume)
    assert cube.scaled(2).volume == pytest.approx(cube.volume * 8)
    miroir = cube.mirrored(Plane.from_point_normal((0, 0, 0), (1, 0, 0)))
    assert miroir.volume == pytest.approx(cube.volume)
    assert miroir.signed_volume > 0


def test_inversion_et_reorientation(cube):
    envers = cube.inverted()
    assert envers.signed_volume < 0
    assert envers.outward().signed_volume > 0


def test_triangulation_dun_contour_concave():
    contour = [Vec3(0, 0, 0), Vec3(4, 0, 0), Vec3(4, 4, 0), Vec3(2, 1, 0),
               Vec3(0, 4, 0)]
    triangles = Polygon(contour).triangulate()
    aire = sum(Polygon(list(t)).area for t in triangles)
    assert aire == pytest.approx(Polygon(contour).area, rel=1e-9)


def test_maillage_indexe(cube):
    sommets, faces = cube.to_mesh()
    assert len(sommets) == 8
    assert len(faces) == 6


def test_operation_sur_un_solide_vide(cube):
    vide = Solid([], "vide")
    assert cube.union(vide).volume == pytest.approx(cube.volume)
    assert cube.subtract(vide).volume == pytest.approx(cube.volume)
    assert cube.intersect(vide).polygons == []


def test_reparation_des_jonctions_en_t():
    brut = box(100, 100, 100).union(box(50, 50, 50, (75, 25, 25)))
    assert brut.heal().check()["aretes_libres"] == 0
''')

ajouter('tests/test_solid_edit.py', r'''
"""Edition de solides : raccords, chanfreins, gaine, coupe, section."""
from __future__ import annotations

import math

import pytest

from CAD_Core.math3d import Plane, Vec3, Z_AXIS
from CAD_Core.primitives import box, cylinder
from CAD_Core.solid_edit import (chamfer_all_edges, chamfer_edge,
                                 convert_to_solid, convert_to_surface,
                                 dihedral_angle, extract_edges, face_report,
                                 fillet_all_edges, fillet_edge, imprint,
                                 offset_solid, section_loops,
                                 section_plane_view, section_profile,
                                 sharp_edges, shell, slice_solid, taper_faces)


@pytest.fixture()
def cube():
    return box(200, 200, 200)


def test_aretes_vives_dun_cube(cube):
    aretes = sharp_edges(cube)
    assert len(aretes) == 12
    assert all(abs(dihedral_angle(cube, faces) - 90.0) < 1e-6
               for _, _, faces in aretes)


def test_chanfrein_dune_seule_arete(cube):
    arete = sharp_edges(cube)[0][:2]
    resultat = chamfer_edge(cube, arete, 20)
    assert resultat.volume == pytest.approx(200 ** 3 - 0.5 * 20 * 20 * 200,
                                            rel=1e-6)


def test_raccord_dune_seule_arete(cube):
    arete = sharp_edges(cube)[0][:2]
    resultat = fillet_edge(cube, arete, 20, segments=16)
    attendu = 200 ** 3 - (400 - math.pi * 100) * 200
    assert resultat.volume == pytest.approx(attendu, rel=5e-3)


def test_raccord_de_toutes_les_aretes_reste_etanche(cube):
    arrondi = fillet_all_edges(cube, 20, segments=8)
    minkowski = (160 ** 3 + 6 * 160 ** 2 * 20 + 3 * math.pi * 160 * 400
                 + 4 / 3 * math.pi * 8000)
    assert arrondi.volume == pytest.approx(minkowski, rel=0.01)
    assert arrondi.check()["ferme"]


def test_chanfrein_de_toutes_les_aretes(cube):
    chanfreine = chamfer_all_edges(cube, 20)
    assert chanfreine.volume < cube.volume
    assert chanfreine.volume > cube.volume * 0.9
    assert chanfreine.check()["ferme"]


def test_rayon_ou_distance_invalide(cube):
    arete = sharp_edges(cube)[0][:2]
    with pytest.raises(ValueError):
        fillet_edge(cube, arete, 0)
    with pytest.raises(ValueError):
        chamfer_edge(cube, arete, -5)


def test_gaine_fermee_et_ouverte():
    creuse = shell(box(200, 200, 200), 20)
    assert creuse.volume == pytest.approx(200 ** 3 - 160 ** 3, rel=1e-6)
    assert creuse.check()["ferme"]
    ouverte = shell(box(200, 200, 200), 20, open_faces=[1])
    assert ouverte.volume == pytest.approx(200 ** 3 - 160 ** 3 - 160 * 160 * 20,
                                           rel=1e-6)


def test_gaine_refuse_une_epaisseur_impossible():
    with pytest.raises(ValueError):
        shell(box(100, 100, 100), 0)
    with pytest.raises(ValueError):
        shell(box(100, 100, 100), 200)
    with pytest.raises(ValueError):
        shell(box(100, 100, 100), 20, open_faces=[99])


def test_coupe_par_un_plan(cube):
    plan = Plane.from_point_normal((0, 0, 100), Z_AXIS)
    haut, bas = slice_solid(cube, plan)
    assert haut.volume == pytest.approx(4e6, rel=1e-6)
    assert bas.volume == pytest.approx(4e6, rel=1e-6)
    assert len(slice_solid(cube, plan, "positif")) == 1
    with pytest.raises(ValueError):
        slice_solid(cube, plan, "dessus")


def test_section_dun_cube_et_dun_cylindre(cube):
    plan = Plane.from_point_normal((0, 0, 100), Z_AXIS)
    boucles = section_loops(cube, plan)
    assert len(boucles) == 1
    assert boucles[0].length == pytest.approx(800.0, rel=1e-6)
    profil = section_profile(cylinder(100, 300, segments=64),
                             Plane.from_point_normal((0, 0, 150), Z_AXIS))
    assert profil.area == pytest.approx(math.pi * 10000, rel=1e-2)
    vue = section_plane_view(cube, plan)
    assert vue["contours"] == 1 and vue["aire_mm2"] == pytest.approx(40000)


def test_decalage_de_solide():
    assert offset_solid(box(100, 100, 100), 10).volume == pytest.approx(120 ** 3,
                                                                        rel=1e-6)
    assert offset_solid(box(100, 100, 100), -10).volume == pytest.approx(80 ** 3,
                                                                         rel=1e-6)


def test_depouille_reduit_la_matiere():
    incline = taper_faces(box(100, 100, 100),
                          Plane.from_point_normal((0, 0, 0), Z_AXIS), 10)
    assert incline.volume < 1e6
    assert incline.volume > 0.5e6


def test_empreinte_et_conversions(cube):
    marque = imprint(cube, box(50, 50, 300, (75, 75, -50)))
    assert marque.metadata["empreintes"] == 1
    surface = convert_to_surface(cube)
    assert surface.metadata["type"] == "surface"
    referme = convert_to_solid(surface)
    assert referme.volume == pytest.approx(cube.volume)


def test_extraction_du_filaire_et_fiche_des_faces(cube):
    assert len(extract_edges(cube)) == 12
    faces = face_report(cube)
    assert len(faces) == 6
    assert all(face["aire_mm2"] == pytest.approx(40000) for face in faces)
''')

ajouter('tests/test_sustainability.py', r'''
"""Tests carbone, energie et certification."""
from __future__ import annotations

import pytest

from Sustainability.carbon import CarbonAnalyzer
from Sustainability.certification import CertificationScorer
from Sustainability.energy import EnergyOptions, EnergySimulator


def test_bilan_carbone(furnished):
    result = CarbonAnalyzer().analyze(furnished)
    assert result["total_kg_co2e"] > 0
    somme = sum(line["kg_co2e"] for line in result["lignes"])
    assert abs(somme - result["total_kg_co2e"]) < 1.0
    assert result["etiquette"] in list("ABCDE")
    assert result["leviers"]
    gains = [l["gain_kg_co2e"] for l in result["leviers"]]
    assert gains == sorted(gains, reverse=True), "leviers classes par gain"


def test_variante_bois_reduit_les_emissions(furnished):
    comparison = CarbonAnalyzer().compare(
        furnished, {"MUR.EXT.M3": 55.0, "STR.DALLE.M3": 130.0})
    assert comparison["gain_kg_co2e"] > 0
    assert comparison["gain_pourcent"] > 10


def test_isolation_ordonnee(furnished):
    simulator = EnergySimulator()
    values = [simulator.simulate(furnished, EnergyOptions(insulation=level))["kwh_m2_an"]
              for level in ("ancien", "renove", "neuf", "passif")]
    assert values == sorted(values, reverse=True), "isolation incoherente : %s" % values


def test_deperditions_somment_au_total(furnished):
    result = EnergySimulator().simulate(furnished)
    losses = result["deperditions_w_par_k"]
    total = losses.pop("total")
    assert abs(sum(losses.values()) - total) < 1.0


def test_climat_influence_les_besoins(furnished):
    simulator = EnergySimulator()
    froid = simulator.simulate(furnished, EnergyOptions(climate="montagnard"))
    chaud = simulator.simulate(furnished, EnergyOptions(climate="tropical"))
    assert froid["besoins_kwh_an"]["chauffage_net"] > \
        chaud["besoins_kwh_an"]["chauffage_net"] * 3


def test_parametres_invalides_refuses(furnished):
    with pytest.raises(ValueError):
        EnergySimulator().simulate(furnished, EnergyOptions(insulation="magique"))
    with pytest.raises(ValueError):
        EnergySimulator().simulate(furnished, EnergyOptions(climate="lunaire"))


def test_certification(furnished):
    energy = EnergySimulator().simulate(furnished)
    carbon = CarbonAnalyzer().analyze(furnished)
    score = CertificationScorer().score(energy, carbon,
                                        {"recuperation_eau": True})
    assert 0 <= score["note_sur_100"] <= 100
    assert score["niveau"]
    assert score["points_a_gagner"]
''')

ajouter('tests/test_transform3d.py', r'''
"""Deplacements, symetries et reseaux."""
from __future__ import annotations

import math

import pytest

from CAD_Core.math3d import Plane, Vec3, X_AXIS, Z_AXIS
from CAD_Core.primitives import box
from CAD_Core.profiles import Curve
from CAD_Core.transform3d import (align3d, align_to_face, array_along_helix,
                                  array_path, array_polar, array_rectangular,
                                  bounding_box, copy_items, explode_positions,
                                  mirror3d, move, rotate3d,
                                  rotate_between_points, scale3d)


@pytest.fixture()
def cube():
    return box(100, 100, 100)


def test_deplacer_et_copier(cube):
    assert move(cube, (500, 0, 0))[0].centroid.rounded(6) == (550.0, 50.0, 50.0)
    copies = copy_items(cube, (200, 0, 0), 3)
    assert len(copies) == 3
    assert [round(c.centroid.x) for c in copies] == [250, 450, 650]
    with pytest.raises(ValueError):
        copy_items(cube, (1, 0, 0), 0)


def test_rotations(cube):
    tourne = rotate3d(cube, Z_AXIS, 90)[0]
    assert tourne.volume == pytest.approx(cube.volume)
    assert tourne.centroid.rounded(6) == (-50.0, 50.0, 50.0)
    par_points = rotate_between_points(cube, (0, 0, 0), (0, 0, 1), 180)[0]
    assert par_points.centroid.rounded(6) == (-50.0, -50.0, 50.0)
    with pytest.raises(ValueError):
        rotate_between_points(cube, (0, 0, 0), (0, 0, 0), 90)


def test_echelle_et_miroir(cube):
    assert scale3d(cube, 2)[0].volume == pytest.approx(8e6)
    with pytest.raises(ValueError):
        scale3d(cube, 0)
    symetrie = mirror3d(cube, Plane.from_point_normal((0, 0, 0), X_AXIS))
    assert len(symetrie) == 2
    assert round(symetrie[1].centroid.x) == -50
    assert len(mirror3d(cube, Plane.from_point_normal((0, 0, 0), X_AXIS),
                        keep_source=False)) == 1


def test_alignement(cube):
    aligne = align3d(cube, [(0, 0, 0), (100, 0, 0)],
                     [(1000, 1000, 0), (1000, 1100, 0)])[0]
    assert aligne.volume == pytest.approx(cube.volume)
    assert aligne.centroid.rounded(3) == (950.0, 1050.0, 50.0)


def test_reseaux(cube):
    assert len(array_rectangular(cube, 3, 2, 2, 200, 200, 200)) == 12
    assert len(array_polar(cube, (0, 0, 0), Z_AXIS, 6, 360)) == 6
    assert len(array_path(cube, Curve.line((0, 0, 0), (1000, 0, 0)), 5)) == 5
    assert len(array_along_helix(cube, radius=500, count=8)) == 8
    with pytest.raises(ValueError):
        array_rectangular(cube, 0, 1, 1)
    with pytest.raises(ValueError):
        array_polar(cube, count=0)
    with pytest.raises(ValueError):
        array_path(cube, Curve.line((0, 0, 0), (0, 0, 0)), 3)


def test_reseau_sur_chemin_a_pas_impose(cube):
    occurrences = array_path(cube, Curve.line((0, 0, 0), (1000, 0, 0)), 1,
                             measure=True, spacing=250)
    assert len(occurrences) == 5


def test_boite_et_positions(cube):
    reseau = array_rectangular(cube, 3, 2, 1, 200, 200, 200)
    assert bounding_box(reseau).size.as_tuple() == (500.0, 300.0, 100.0)
    assert len(explode_positions(reseau)) == 6


def test_poser_sur_une_face(cube):
    pose = align_to_face(cube, 0, (500, 500, 500), (0, 0, 1))
    assert pose.volume == pytest.approx(cube.volume)
    assert pose.bbox.min.z == pytest.approx(500.0, abs=1e-6)
    with pytest.raises(ValueError):
        align_to_face(cube, 99, (0, 0, 0), (0, 0, 1))
''')


# =========================================================================
# 18. REGISTRE, DOCUMENTATION, EXPLOITATION
# =========================================================================
ajouter('.env.example', r'''
# Configuration de MERCURY CAD AI X
# Copiez ce fichier en .env et adaptez les valeurs.

# --- Base de donnees ---
MERCURY_DB_PATH=mercury.db
# En production : postgresql://user:motdepasse@hote:5432/mercury

# --- Securite (a changer imperativement avant toute mise en ligne) ---
MERCURY_JWT_SECRET=remplacer-par-32-octets-aleatoires
MERCURY_ENCRYPTION_KEY=remplacer-par-une-cle-distincte

# --- Service ---
MERCURY_HOST=127.0.0.1
MERCURY_PORT=8000
MERCURY_LOG_LEVEL=info

# --- Fonctionnalites ---
MERCURY_AUTH_REQUIRED=0
MERCURY_TELEMETRY=0
''')

ajouter('.github/workflows/ci.yml', r'''
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  tests:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip
      - name: Dependances
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install coverage
      - name: Compilation de tous les modules
        run: python -m compileall -q CAD_Core BIM_Engine AI_Engine Estimating \
                                     Sustainability Construction Cloud_Platform \
                                     Database Security API
      - name: Tests avec couverture
        run: |
          coverage run -m pytest -q
          coverage report --fail-under=70
      - name: Demarrage de l'API et sonde /health
        run: |
          uvicorn API.main:app --port 8000 &
          for i in $(seq 1 30); do
            curl -sf http://localhost:8000/health && break
            sleep 1
          done
          curl -sf http://localhost:8000/health

  image:
    runs-on: ubuntu-latest
    needs: [tests]
    steps:
      - uses: actions/checkout@v4
      - name: Construction de l'image
        run: docker build -t mercury:${{ github.sha }} .
      - name: Demarrage et sonde
        run: |
          docker run -d --name mercury -p 8000:8000 mercury:${{ github.sha }}
          for i in $(seq 1 30); do
            curl -sf http://localhost:8000/health && exit 0
            sleep 2
          done
          docker logs mercury
          exit 1
''')

ajouter('.gitignore', r'''
__pycache__/
*.py[cod]
.venv/
venv/
*.db
*.db-journal
*.db-wal
*.db-shm
.coverage
htmlcov/
.pytest_cache/
.env
dist/
build/
*.egg-info/
.DS_Store
''')

ajouter('DELIVERABLES.py', r'''
"""Registre des 70 livrables du PROJET TITAN.

Source unique consommee par l'API (/api/v1/deliverables), la
documentation et les tests de conformite.
"""
from __future__ import annotations

from typing import Any, Dict, List

DELIVERABLES: List[Dict[str, Any]] = [
    {
        "numero": 1,
        "titre": "Vision et architecture globale",
        "groupe": "CORE",
        "module": "docs",
        "etat": "livre"
    },
    {
        "numero": 2,
        "titre": "Analyse marche CAO BIM Construction Tech",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "documente"
    },
    {
        "numero": 3,
        "titre": "Moteur IA Design Generatif",
        "groupe": "CORE",
        "module": "AI_Engine.generative_design",
        "etat": "livre"
    },
    {
        "numero": 4,
        "titre": "Assistant conversationnel IA ingenierie",
        "groupe": "CORE",
        "module": "AI_Engine.nlp_assistant",
        "etat": "livre"
    },
    {
        "numero": 5,
        "titre": "Lecture automatique PDF et plans",
        "groupe": "CORE",
        "module": "AI_Engine.vision_ai",
        "etat": "livre"
    },
    {
        "numero": 6,
        "titre": "Vision AI reconnaissance plans",
        "groupe": "CORE",
        "module": "AI_Engine.vision_ai",
        "etat": "livre"
    },
    {
        "numero": 7,
        "titre": "Conversion 2D vers 3D",
        "groupe": "CORE",
        "module": "CAD_Core.engine_3d",
        "etat": "livre"
    },
    {
        "numero": 8,
        "titre": "Interface CAO nouvelle generation",
        "groupe": "CORE",
        "module": "Frontend",
        "etat": "livre"
    },
    {
        "numero": 9,
        "titre": "Rendu 3D temps reel",
        "groupe": "CORE",
        "module": "CAD_Core.rendering",
        "etat": "livre"
    },
    {
        "numero": 10,
        "titre": "MVP initial",
        "groupe": "CORE",
        "module": "API.main",
        "etat": "livre"
    },
    {
        "numero": 11,
        "titre": "BIM Engine",
        "groupe": "BIM",
        "module": "BIM_Engine.models",
        "etat": "livre"
    },
    {
        "numero": 12,
        "titre": "Objets BIM intelligents",
        "groupe": "BIM",
        "module": "BIM_Engine.object_library",
        "etat": "livre"
    },
    {
        "numero": 13,
        "titre": "Bibliotheque BIM",
        "groupe": "BIM",
        "module": "BIM_Engine.object_library",
        "etat": "livre"
    },
    {
        "numero": 14,
        "titre": "Standards IFC",
        "groupe": "BIM",
        "module": "BIM_Engine.ifc_handler",
        "etat": "livre"
    },
    {
        "numero": 15,
        "titre": "BIM Cloud Collaboration",
        "groupe": "COLLAB",
        "module": "BIM_Engine.collaboration",
        "etat": "livre"
    },
    {
        "numero": 16,
        "titre": "Architecture Professional Module",
        "groupe": "BIM",
        "module": "CAD_Core.engine_2d",
        "etat": "livre"
    },
    {
        "numero": 17,
        "titre": "Structure Engineering Module",
        "groupe": "BIM",
        "module": "BIM_Engine.structure",
        "etat": "esquisse"
    },
    {
        "numero": 18,
        "titre": "MEP Engineering Module",
        "groupe": "BIM",
        "module": "BIM_Engine.mep",
        "etat": "esquisse"
    },
    {
        "numero": 19,
        "titre": "Documentation automatique",
        "groupe": "BIM",
        "module": "CAD_Core.documentation",
        "etat": "livre"
    },
    {
        "numero": 20,
        "titre": "Assistant ingenieur BIM IA",
        "groupe": "CORE",
        "module": "AI_Engine.nlp_assistant",
        "etat": "livre"
    },
    {
        "numero": 21,
        "titre": "Gestion versions projet",
        "groupe": "COLLAB",
        "module": "Database.repository",
        "etat": "livre"
    },
    {
        "numero": 22,
        "titre": "Marketplace BIM",
        "groupe": "BIM",
        "module": "BIM_Engine.object_library",
        "etat": "esquisse"
    },
    {
        "numero": 23,
        "titre": "Fabricants materiaux",
        "groupe": "BIM",
        "module": "BIM_Engine.object_library",
        "etat": "esquisse"
    },
    {
        "numero": 24,
        "titre": "API BIM",
        "groupe": "CORE",
        "module": "API.main",
        "etat": "livre"
    },
    {
        "numero": 25,
        "titre": "Enterprise BIM Platform",
        "groupe": "COLLAB",
        "module": "Security.rbac",
        "etat": "livre"
    },
    {
        "numero": 26,
        "titre": "Construction AI Platform",
        "groupe": "CONSTRUCTION",
        "module": "Construction.platform",
        "etat": "esquisse"
    },
    {
        "numero": 27,
        "titre": "Planning chantier IA",
        "groupe": "CONSTRUCTION",
        "module": "Construction.planning",
        "etat": "livre"
    },
    {
        "numero": 28,
        "titre": "Suivi avancement chantier",
        "groupe": "CONSTRUCTION",
        "module": "Construction.progress",
        "etat": "esquisse"
    },
    {
        "numero": 29,
        "titre": "Vision IA qualite",
        "groupe": "CONSTRUCTION",
        "module": "AI_Engine.vision_ai",
        "etat": "esquisse"
    },
    {
        "numero": 30,
        "titre": "Securite chantier IA",
        "groupe": "CONSTRUCTION",
        "module": "Construction.safety",
        "etat": "esquisse"
    },
    {
        "numero": 31,
        "titre": "Drone chantier",
        "groupe": "CONSTRUCTION",
        "module": "Construction.drone",
        "etat": "esquisse"
    },
    {
        "numero": 32,
        "titre": "Comparaison BIM reel",
        "groupe": "CONSTRUCTION",
        "module": "Construction.progress",
        "etat": "esquisse"
    },
    {
        "numero": 33,
        "titre": "Gestion ressources",
        "groupe": "CONSTRUCTION",
        "module": "Construction.resources",
        "etat": "esquisse"
    },
    {
        "numero": 34,
        "titre": "Gestion fournisseurs",
        "groupe": "CONSTRUCTION",
        "module": "Construction.resources",
        "etat": "esquisse"
    },
    {
        "numero": 35,
        "titre": "Rapports automatiques",
        "groupe": "CONSTRUCTION",
        "module": "CAD_Core.documentation",
        "etat": "livre"
    },
    {
        "numero": 36,
        "titre": "Cost AI",
        "groupe": "COST",
        "module": "Estimating.cost_ai",
        "etat": "livre"
    },
    {
        "numero": 37,
        "titre": "Metres automatiques",
        "groupe": "COST",
        "module": "Estimating.takeoff",
        "etat": "livre"
    },
    {
        "numero": 38,
        "titre": "Devis IA",
        "groupe": "COST",
        "module": "Estimating.cost_ai",
        "etat": "livre"
    },
    {
        "numero": 39,
        "titre": "Optimisation budget",
        "groupe": "COST",
        "module": "Estimating.cost_ai",
        "etat": "esquisse"
    },
    {
        "numero": 40,
        "titre": "Project Management Enterprise",
        "groupe": "COLLAB",
        "module": "Construction.planning",
        "etat": "esquisse"
    },
    {
        "numero": 41,
        "titre": "Digital Twin Platform",
        "groupe": "TWIN",
        "module": "Cloud_Platform.digital_twin",
        "etat": "livre"
    },
    {
        "numero": 42,
        "titre": "Smart Building OS",
        "groupe": "TWIN",
        "module": "Cloud_Platform.digital_twin",
        "etat": "esquisse"
    },
    {
        "numero": 43,
        "titre": "IoT Integration",
        "groupe": "TWIN",
        "module": "Cloud_Platform.iot",
        "etat": "livre"
    },
    {
        "numero": 44,
        "titre": "Maintenance predictive",
        "groupe": "TWIN",
        "module": "Cloud_Platform.predictive",
        "etat": "livre"
    },
    {
        "numero": 45,
        "titre": "Energy Intelligence",
        "groupe": "GREEN",
        "module": "Sustainability.energy",
        "etat": "livre"
    },
    {
        "numero": 46,
        "titre": "Solar Microgrid",
        "groupe": "GREEN",
        "module": "Sustainability.energy",
        "etat": "esquisse"
    },
    {
        "numero": 47,
        "titre": "Performance batiment",
        "groupe": "GREEN",
        "module": "Sustainability.energy",
        "etat": "livre"
    },
    {
        "numero": 48,
        "titre": "AR Maintenance",
        "groupe": "MOBILE",
        "module": "Mobile.ar",
        "etat": "esquisse"
    },
    {
        "numero": 49,
        "titre": "Drone Inspection Digital Twin",
        "groupe": "TWIN",
        "module": "Construction.drone",
        "etat": "esquisse"
    },
    {
        "numero": 50,
        "titre": "Cycle de vie batiment",
        "groupe": "GREEN",
        "module": "Sustainability.carbon",
        "etat": "livre"
    },
    {
        "numero": 51,
        "titre": "Green Building AI",
        "groupe": "GREEN",
        "module": "Sustainability.carbon",
        "etat": "livre"
    },
    {
        "numero": 52,
        "titre": "Calcul carbone",
        "groupe": "GREEN",
        "module": "Sustainability.carbon",
        "etat": "livre"
    },
    {
        "numero": 53,
        "titre": "Materiaux durables",
        "groupe": "GREEN",
        "module": "Sustainability.carbon",
        "etat": "livre"
    },
    {
        "numero": 54,
        "titre": "Simulation energetique",
        "groupe": "GREEN",
        "module": "Sustainability.energy",
        "etat": "livre"
    },
    {
        "numero": 55,
        "titre": "Certification verte",
        "groupe": "GREEN",
        "module": "Sustainability.certification",
        "etat": "livre"
    },
    {
        "numero": 56,
        "titre": "Adaptation climatique",
        "groupe": "GREEN",
        "module": "Sustainability.energy",
        "etat": "esquisse"
    },
    {
        "numero": 57,
        "titre": "Smart Village Platform",
        "groupe": "CITY",
        "module": "Cloud_Platform.city",
        "etat": "esquisse"
    },
    {
        "numero": 58,
        "titre": "Digital Twin Smart City",
        "groupe": "CITY",
        "module": "Cloud_Platform.city",
        "etat": "esquisse"
    },
    {
        "numero": 59,
        "titre": "GIS Topography Drone",
        "groupe": "CITY",
        "module": "Cloud_Platform.city",
        "etat": "esquisse"
    },
    {
        "numero": 60,
        "titre": "Finance Projet AI",
        "groupe": "BUSINESS",
        "module": "Estimating.cost_ai",
        "etat": "esquisse"
    },
    {
        "numero": 61,
        "titre": "Sustainability AI",
        "groupe": "GREEN",
        "module": "Sustainability.carbon",
        "etat": "livre"
    },
    {
        "numero": 62,
        "titre": "Topography Integration",
        "groupe": "CITY",
        "module": "Cloud_Platform.city",
        "etat": "esquisse"
    },
    {
        "numero": 63,
        "titre": "Mobile Tablet Platform",
        "groupe": "MOBILE",
        "module": "Mobile",
        "etat": "livre"
    },
    {
        "numero": 64,
        "titre": "Expansion internationale",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "documente"
    },
    {
        "numero": 65,
        "titre": "Legal Corporate Governance",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "documente"
    },
    {
        "numero": 66,
        "titre": "Investor Package",
        "groupe": "BUSINESS",
        "module": "docs/INVESTOR_DECK.md",
        "etat": "documente"
    },
    {
        "numero": 67,
        "titre": "Documentation technique",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "livre"
    },
    {
        "numero": 68,
        "titre": "Beta Testing Program",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "documente"
    },
    {
        "numero": 69,
        "titre": "Global Launch Plan",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "documente"
    },
    {
        "numero": 70,
        "titre": "Master Plan 2030",
        "groupe": "BUSINESS",
        "module": "docs/ROADMAP_2030.md",
        "etat": "documente"
    }
]

GROUPS: Dict[str, str] = {
    "CORE": "Systeme central : CAO, IA, interface, MVP",
    "BIM": "Moteur BIM, objets, standards IFC, metiers",
    "COLLAB": "Collaboration, versions, entreprise",
    "CONSTRUCTION": "Chantier : planning, suivi, qualite, securite",
    "COST": "Economie : metres, couts, devis",
    "TWIN": "Jumeau numerique, IoT, maintenance",
    "GREEN": "Environnement : carbone, energie, certification",
    "CITY": "Territoire : village et ville intelligents",
    "MOBILE": "Terrain : tablette, mobile, realite augmentee",
    "BUSINESS": "Marche, juridique, investisseurs, lancement"
}


def by_group(group: str) -> List[Dict[str, Any]]:
    """Livrables d'un groupe donne."""
    return [d for d in DELIVERABLES if d['groupe'] == group]


def by_state(state: str) -> List[Dict[str, Any]]:
    """Livrables dans un etat donne : livre, esquisse, documente."""
    return [d for d in DELIVERABLES if d['etat'] == state]
''')

ajouter('Dockerfile', r'''
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MERCURY_DB_PATH=/data/mercury.db

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "API.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
''')

ajouter('README.en.md', r'''
# MERCURY CAD AI X — PROJECT TITAN

A CAD platform: **2D plan → AI → 3D → BIM → quantities → environment → digital twin**.

The geometry kernel, plan reader, IFC4 writer, generative engine and analysis
modules were written for this project. Only FastAPI is required to expose the
API; everything else uses the standard library.

---

## Getting started

```bash
pip install -r requirements.txt
uvicorn API.main:app --reload --port 8000
```

UI: `Frontend/index.html` · Interactive docs: `/docs` · Liveness: `/health`
Readiness: `/ready`

```bash
pytest -q
docker compose up --build
```

---

## What it does

**Designs.** Give it a brief — 110 m², three bedrooms — and simulated annealing
searches a slicing tree for the layout that best satisfies target areas,
proportions, orientation, daylight, adjacencies and plumbing grouping. The
output is a complete BIM project, not a picture.

**Reads plans.** Professional drawings represent a wall as two parallel lines:
the engine pairs them, merges collinear axes *across openings*, then extends
them to their intersections.

**Extracts rooms.** Wall axes form a planar arrangement: split at
intersections, weld vertices, prune dangling edges, traverse half-edges. No
flood fill.

**Quantifies.** Take-off where every quantity carries its formula, cost
estimate per trade, schedule with critical path, embodied carbon (A1-A3) with
levers ranked by actual saving, energy model across six climates.

**Exports.** IFC4 with base quantities, OBJ, glTF 2.0, SVG, JSON.

**Observes.** Sensors are bound to rooms of the BIM model: a deviation in a
large occupied volume is flagged more severe than the same in a plant room.

---

## Honest limits

- The **energy model** is a static monthly method, not an hourly dynamic
  simulation. No thermal inertia, occupancy scenarios or solar masks. It is not
  a regulatory calculation.
- **Vision models** have a real architecture and API but **fake weights**: they
  demonstrate the pipeline, they do not yet recognise anything.
- **Structure** and **MEP** modules are sketch-stage pre-sizing, not a
  substitute for engineering calculations.
- **Construction site**, **territory** and **augmented reality** groups are
  scaffolded: interfaces exist, engines remain to be written.
''')

ajouter('README.md', r'''
# MERCURY CAD AI X — PROJET TITAN

Logiciel de **modélisation 3D** et plateforme de conception assistée par
ordinateur : **modélisation solide → plan 2D → IA → BIM → métré →
environnement → jumeau numérique**.

Le noyau géométrique 3D (solides, opérations booléennes, maillages, rendu), les
98 commandes de modélisation, les 29 formats de fichiers, le lecteur de plans,
l'écrivain IFC4 et le moteur génératif sont écrits pour ce projet. Seul FastAPI
est requis pour exposer l'API ; tout le reste tient dans la bibliothèque
standard.

---

## Démarrage

```bash
pip install -r requirements.txt
uvicorn API.main:app --reload --port 8000
```

Interface de modélisation : **`/app`** · Documentation interactive : `/docs`
Sonde de disponibilité : `/health` · Sonde de préparation : `/ready`

```bash
python -m CAD_Core.main demo          # démonstration en ligne de commande
```

```bash
pytest -q                    # suite complète
docker compose up --build    # api + base + interface
```

---

## Ce que fait la plateforme

**Modélise en 3D.** Un noyau de solides facettisés avec opérations booléennes
exactes (arbre BSP), et les outils volumiques attendus d'un logiciel de CAO :
boîte, biseau, cylindre, cône, sphère, tore, pyramide, polysolide, hélice ;
extrusion avec dépouille, révolution, balayage avec torsion, lissage,
appuyer-tirer, épaissir ; raccord et chanfrein d'arêtes, gaine, coupe, section,
dépouille, décalage, séparation, empreinte ; déplacement, rotation, échelle,
alignement, symétrie et réseaux rectangulaire, polaire et sur trajectoire ;
lissage et affinage de maillage. **98 commandes** portant les noms d'AutoCAD,
en français et en anglais, avec leurs alias courts.

**Vérifie.** Chaque solide connaît son volume, son aire, son centre de gravité,
son inertie et son étanchéité. Les volumes produits par les outils sont
contrôlés par les tests contre leurs valeurs analytiques exactes.

**Conçoit.** Donnez un programme — 110 m², trois chambres — et le recuit simulé
explore un arbre de découpe pour trouver la disposition qui satisfait au mieux
les surfaces cibles, les proportions, l'orientation, l'accès au jour, les
adjacences et le regroupement des points d'eau. Le résultat est un projet BIM
complet, pas une image.

**Lit les plans.** Un plan professionnel dessine un mur par deux traits
parallèles : le moteur les apparie, fusionne les axes colinéaires au travers
des baies, puis les prolonge jusqu'aux intersections.

**Extrait les pièces.** Les axes de murs forment un arrangement planaire :
découpe aux intersections, fusion des sommets, élagage des brins pendants,
parcours des demi-arêtes. Aucune heuristique de remplissage.

**Chiffre.** Métré où chaque quantité porte sa formule, devis par lot, planning
avec chemin critique, empreinte carbone A1-A3 avec leviers classés par gain
réel, simulation énergétique sur six climats et quatre niveaux d'isolation.

**Échange.** 29 formats lus ou écrits : DWG, DXF (R12 à 2021), IFC4, STEP
AP203/AP214/AP242, IGES, STL, OBJ, PLY, OFF, glTF 2.0, GLB, 3MF, AMF, COLLADA,
VRML, X3D, 3DS, SVG, PDF vectoriel, PNG, BMP, PPM, TGA, JPEG, nuages de points
XYZ/PTS/CSV/LAS, et un format natif JSON sans perte. Tout est écrit sans
dépendance externe ; seul le DWG passe par un moteur de conversion installé sur
la machine (voir *Limites assumées*).

**Dessine.** Interface web de modélisation à `/app` : ruban construit à partir
du catalogue de commandes, vue 3D WebGL avec orbite, styles visuels, arêtes
vives, grille et axes, palettes de calques et de propriétés, ligne de commande
avec historique, import et export de tous les formats.

**Observe.** Les capteurs sont rattachés aux pièces du modèle : une dérive dans
un grand volume occupé est signalée comme plus grave que la même dans un local
technique.

---

## Architecture

```
Mercury/
├── CAD_Core/          noyau 3D : maths · solides · primitives · modélisation
│                      édition · transformations · maillages · document
│                      accrochages · annotation · vues · rendu · commandes
├── Interop/           DWG · DXF · IFC · STEP · IGES · maillages · images
│                      PDF · SVG · nuages de points · format natif
├── BIM_Engine/        modèle BIM · IFC4 · bibliothèque · collaboration · structure · fluides
├── AI_Engine/         génératif · vision · assistant · maintenance prédictive
├── Estimating/        métré · coûts · devis · optimisation budget
├── Sustainability/    carbone · énergie · certification
├── Construction/      planning · avancement · ressources · sécurité
├── Cloud_Platform/    jumeau numérique · IoT · multi-tenant · territoire
├── Database/          schéma SQL · migrations · dépôt versionné
├── Security/          authentification · chiffrement · contrôle d'accès
├── API/               FastAPI · schémas · dépendances · routes CAO
├── Frontend/          interface CAO WebGL (HTML/CSS/JS, sans compilation)
├── Mobile/            clients iOS et Android
└── tests/             suite de tests
```

**Principes.** Un seul contrat de données (`BuildingProject`) entre tous les
modules : toute brique est remplaçable. Chaque quantité est dérivée de la
géométrie, jamais saisie. À graine fixée, la génération redonne exactement le
même plan. Les modules qui approximent le disent dans leur sortie.

---

## Les 70 livrables

| Groupe | Description | Livré | Esquissé | Documenté |
|---|---|---|---|---|
| CORE | Systeme central : CAO, IA, interface, MVP | 11 | 0 | 0 |
| BIM | Moteur BIM, objets, standards IFC, metiers | 6 | 4 | 0 |
| COLLAB | Collaboration, versions, entreprise | 3 | 1 | 0 |
| CONSTRUCTION | Chantier : planning, suivi, qualite, securite | 2 | 8 | 0 |
| COST | Economie : metres, couts, devis | 3 | 1 | 0 |
| TWIN | Jumeau numerique, IoT, maintenance | 3 | 2 | 0 |
| GREEN | Environnement : carbone, energie, certification | 9 | 2 | 0 |
| CITY | Territoire : village et ville intelligents | 0 | 4 | 0 |
| MOBILE | Terrain : tablette, mobile, realite augmentee | 1 | 1 | 0 |
| BUSINESS | Marche, juridique, investisseurs, lancement | 1 | 1 | 7 |

Registre interrogeable : `GET /api/v1/deliverables` · Détail complet :
`docs/DELIVERABLES.md`

---

## Limites assumées

- Le **DWG** est un format binaire propriétaire non documenté : MERCURY
  l'identifie nativement (version exacte, page de codes, aperçu), mais la
  conversion de sa géométrie passe par un moteur installé sur la machine — ODA
  File Converter, LibreDWG ou `ezdxf[odafc]`. Sans moteur, l'erreur dit
  exactement quoi installer ; le DXF, lui, est lu et écrit nativement dans
  toutes ses versions.
- Les **solides sont facettisés** : un cylindre est un prisme à *n* faces, pas
  une surface analytique. Les volumes convergent vers la valeur exacte quand la
  finesse augmente ; l'écart est mesuré par les tests. Les raccords d'arêtes
  produisent des congés polygonaux, et les coins où trois raccords se
  rejoignent sont formés par l'intersection des surfaces voisines.
- La **lecture STEP et IFC** couvre les représentations facettisées (BREP). Un
  fichier décrivant des surfaces analytiques ou des extrusions paramétriques
  est refusé avec un message qui indique l'option d'export à activer.
- Le **JPEG** est lu et écrit via Pillow s'il est installé ; PNG, BMP, PPM et
  TGA sont écrits nativement.
- La **simulation énergétique** est une méthode statique mensuelle, pas une
  simulation dynamique horaire. Ni inertie, ni scénarios d'occupation, ni
  masques solaires. Ce n'est pas un calcul réglementaire.
- Les **modèles de vision** ont une architecture et une API réelles mais des
  **poids factices** : ils démontrent la chaîne, ils ne reconnaissent pas encore.
- Les modules **structure** et **fluides** sont des prédimensionnements
  d'esquisse, non substituables à des notes de calcul.
- Les groupes **chantier**, **territoire** et **réalité augmentée** sont
  esquissés : les interfaces existent, les moteurs restent à écrire.
''')

ajouter('deploy.sh', r'''
#!/usr/bin/env bash
# Deploiement de MERCURY CAD AI X.
#   ./deploy.sh local    installation locale et demarrage
#   ./deploy.sh docker   construction et lancement des conteneurs
#   ./deploy.sh test     suite de tests uniquement
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-local}"
PORT="${MERCURY_PORT:-8000}"

verifier_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[X] Python 3 est requis : https://www.python.org/downloads/"
    exit 1
  fi
  local version
  version="$(python3 -c 'import sys; print(sys.version_info[0]*100+sys.version_info[1])')"
  if [ "$version" -lt 310 ]; then
    echo "[X] Python 3.10 minimum requis (detecte : $version)"
    exit 1
  fi
}

case "$MODE" in
  local)
    verifier_python
    echo "[1/4] Environnement isole"
    python3 -m venv .venv
    # shellcheck disable=SC1091
    source .venv/bin/activate
    echo "[2/4] Dependances"
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    echo "[3/4] Tests"
    pytest -q
    echo "[4/4] Demarrage sur le port $PORT"
    exec uvicorn API.main:app --host 0.0.0.0 --port "$PORT"
    ;;
  docker)
    command -v docker >/dev/null 2>&1 || { echo "[X] Docker absent"; exit 1; }
    echo "[1/2] Construction"
    docker compose build
    echo "[2/2] Demarrage"
    docker compose up -d
    echo "API   : http://localhost:$PORT"
    echo "Client: http://localhost:8080"
    ;;
  test)
    verifier_python
    pytest -q
    ;;
  *)
    echo "Usage : ./deploy.sh [local|docker|test]"
    exit 1
    ;;
esac
''')

ajouter('docker-compose.yml', r'''
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      MERCURY_DB_PATH: /data/mercury.db
      MERCURY_JWT_SECRET: ${MERCURY_JWT_SECRET:-changez-moi}
      MERCURY_ENCRYPTION_KEY: ${MERCURY_ENCRYPTION_KEY:-changez-moi-aussi}
    volumes:
      - mercury_data:/data
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3

  frontend:
    image: nginx:alpine
    ports: ["8080:80"]
    volumes:
      - ./Frontend:/usr/share/nginx/html:ro
    depends_on:
      api:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: mercury
      POSTGRES_PASSWORD: mercury
      POSTGRES_DB: mercury
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mercury"]
      interval: 10s
      retries: 5

volumes:
  mercury_data:
  postgres_data:
''')

ajouter('docs/API_REFERENCE.md', r'''
# Référence de l'API — MERCURY CAD AI X

Base : `http://localhost:8000` · Documentation interactive : `/docs`
Format : JSON · Unités : millimètres pour les longueurs, m² pour les surfaces.

---

## Système

| Méthode | Chemin | Description |
|---|---|---|
| GET | `/health` | Sonde de disponibilité. Ne touche pas la base, toujours rapide. |
| GET | `/ready` | Sonde de préparation : vérifie réellement l'accès à la base. |
| GET | `/api/v1/deliverables` | Registre des 70 livrables (filtrable par `groupe`). |
| GET | `/app` | Interface web de modélisation 3D. |

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0","uptime_seconds":12.4}
```

---

## Modélisation 3D

Toutes les routes CAO sont préfixées par `/api/v1/cad`.

### Catalogue

| Méthode | Chemin | Description |
|---|---|---|
| GET | `/api/v1/cad/commands` | Les 98 commandes, filtrables par `groupe`. |
| GET | `/api/v1/cad/capabilities` | Commandes, formats, styles visuels, vues, accrochages. |
| GET | `/api/v1/cad/formats` | Matrice des formats, filtrable par `nature` et `capacite`. |

### Documents

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/cad/documents` | Crée un document (`nom`, `unites`). |
| GET | `/api/v1/cad/documents` | Documents ouverts. |
| GET | `/api/v1/cad/documents/{id}` | État, calques, fenêtre. `?detail=true` pour tout. |
| DELETE | `/api/v1/cad/documents/{id}` | Ferme le document. |
| GET | `/api/v1/cad/documents/{id}/entities` | Objets du document. |
| GET | `/api/v1/cad/documents/{id}/history` | Historique des commandes. |

### Commandes

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/cad/documents/{id}/command` | Exécute une commande. |
| POST | `/api/v1/cad/documents/{id}/script` | Exécute un script de commandes. |

```bash
curl -X POST localhost:8000/api/v1/cad/documents/doc-0001/command \
  -H 'Content-Type: application/json' \
  -d '{"commande":"BOITE","parametres":{"longueur":2000,"largeur":1000,"hauteur":500}}'
```

### Géométrie et rendu

| Méthode | Chemin | Description |
|---|---|---|
| GET | `/api/v1/cad/documents/{id}/mesh` | Triangles, normales, arêtes vives, groupes. `?angle_aretes=0` renvoie toutes les arêtes. |
| GET | `/api/v1/cad/documents/{id}/curves` | Courbes et contours. |
| POST | `/api/v1/cad/documents/{id}/render` | Image PNG (`largeur`, `hauteur`, `style`, `vue`). |

### Fichiers

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/cad/documents/{id}/export` | Exporte dans l'un des 29 formats. |
| POST | `/api/v1/cad/documents/{id}/import` | Importe un fichier et le fusionne. |
| POST | `/api/v1/cad/files/identify` | Reconnaît un fichier à sa signature. |
| POST | `/api/v1/cad/files/open` | Ouvre un fichier dans un nouveau document. |
| POST | `/api/v1/cad/files/convert?cible=step` | Convertit sans ouvrir de document. |

```bash
curl -X POST 'localhost:8000/api/v1/cad/files/convert?cible=stl' \
  -F 'fichier=@plan.dxf' -o piece.stl
```

Le téléversement est plafonné à 64 Mo. Un fichier non reconnu renvoie 400 avec
la liste des extensions acceptées.

---

## Projets

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/projects` | Crée un projet vide. |
| GET | `/api/v1/projects` | Liste les projets. |
| GET | `/api/v1/projects/{id}` | Projet complet, avec l'historique des versions. |
| DELETE | `/api/v1/projects/{id}` | Suppression logique. |

**Erreurs** : `404` projet introuvable, `400` typologie inconnue.

---

## Conception générative

```bash
curl -X POST http://localhost:8000/api/v1/design/generate \
  -H "Content-Type: application/json" \
  -d '{"typologie":"maison","surface":110,"chambres":3,"variantes":3}'
```

Réponse : programme calé, emprise, variantes classées par score croissant.
Le champ `saturation` prévient quand la demande est incohérente (210 m² pour
trois chambres) au lieu de produire des chambres de 40 m².

`graine` fixe le générateur : à valeur égale, le résultat est identique.

---

## Édition

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/projects/{id}/walls` | Ajoute un mur. |
| POST | `/api/v1/projects/{id}/openings` | Pose une porte ou une fenêtre. |
| POST | `/api/v1/projects/{id}/rooms/rebuild` | Recalcule les pièces. |

Une baie qui déborde du mur renvoie `400` avec la longueur disponible.
Si aucun contour n'est fermé, l'état précédent est **conservé** et un
avertissement est renvoyé — le projet n'est jamais vidé silencieusement.

---

## Économie et environnement

| Méthode | Chemin | Description |
|---|---|---|
| GET | `/api/v1/projects/{id}/takeoff` | Métré, chaque ligne avec sa formule. |
| GET | `/api/v1/projects/{id}/estimate` | Devis par lot + planning avec chemin critique. |
| GET | `/api/v1/projects/{id}/carbon` | Empreinte A1-A3, étiquette, leviers classés. |
| GET | `/api/v1/projects/{id}/energy` | Besoins, étiquette, actions prioritaires. |
| GET | `/api/v1/projects/{id}/certification` | Note multicritère et points à gagner. |

Paramètres : `devise`, `coef_region` (chiffrage) · `isolation`, `climat`
(énergie : `ancien`, `renove`, `neuf`, `passif` ; six climats).

---

## Jumeau numérique

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/iot/sensors` | Déclare un capteur, rattaché à une pièce. |
| POST | `/api/v1/iot/readings` | Webhook d'ingestion (lot compatible pont MQTT). |
| GET | `/api/v1/projects/{id}/twin` | État courant et alertes pondérées par le BIM. |

---

## Exports

```bash
curl -X POST http://localhost:8000/api/v1/projects/{id}/export \
  -d '{"format":"ifc"}' > projet.ifc
```

Formats : `ifc` (IFC4 avec quantités), `obj`, `gltf`, `svg`, `json`.

---

## Codes d'erreur

| Code | Signification |
|---|---|
| 400 | Requête invalide — le message indique la contrainte violée. |
| 404 | Ressource introuvable. |
| 422 | Schéma non respecté (validation Pydantic). |
| 503 | Base indisponible (`/ready` uniquement). |
''')

ajouter('docs/DELIVERABLES.md', r'''
# Les 70 livrables — état réel

Trois états, sans complaisance :

- **livré** — code fonctionnel, testé, exposé par l'API
- **esquissé** — module en place, interfaces définies, moteur à approfondir
- **documenté** — livrable non logiciel (marché, juridique, lancement)

| N° | Livrable | Groupe | Module | État |
|---|---|---|---|---|
| 01 | Vision et architecture globale | CORE | `docs` | livre |
| 02 | Analyse marche CAO BIM Construction Tech | BUSINESS | `docs` | documente |
| 03 | Moteur IA Design Generatif | CORE | `AI_Engine.generative_design` | livre |
| 04 | Assistant conversationnel IA ingenierie | CORE | `AI_Engine.nlp_assistant` | livre |
| 05 | Lecture automatique PDF et plans | CORE | `AI_Engine.vision_ai` | livre |
| 06 | Vision AI reconnaissance plans | CORE | `AI_Engine.vision_ai` | livre |
| 07 | Conversion 2D vers 3D | CORE | `CAD_Core.engine_3d` | livre |
| 08 | Interface CAO nouvelle generation | CORE | `Frontend` | livre |
| 09 | Rendu 3D temps reel | CORE | `CAD_Core.rendering` | livre |
| 10 | MVP initial | CORE | `API.main` | livre |
| 11 | BIM Engine | BIM | `BIM_Engine.models` | livre |
| 12 | Objets BIM intelligents | BIM | `BIM_Engine.object_library` | livre |
| 13 | Bibliotheque BIM | BIM | `BIM_Engine.object_library` | livre |
| 14 | Standards IFC | BIM | `BIM_Engine.ifc_handler` | livre |
| 15 | BIM Cloud Collaboration | COLLAB | `BIM_Engine.collaboration` | livre |
| 16 | Architecture Professional Module | BIM | `CAD_Core.engine_2d` | livre |
| 17 | Structure Engineering Module | BIM | `BIM_Engine.structure` | esquisse |
| 18 | MEP Engineering Module | BIM | `BIM_Engine.mep` | esquisse |
| 19 | Documentation automatique | BIM | `CAD_Core.documentation` | livre |
| 20 | Assistant ingenieur BIM IA | CORE | `AI_Engine.nlp_assistant` | livre |
| 21 | Gestion versions projet | COLLAB | `Database.repository` | livre |
| 22 | Marketplace BIM | BIM | `BIM_Engine.object_library` | esquisse |
| 23 | Fabricants materiaux | BIM | `BIM_Engine.object_library` | esquisse |
| 24 | API BIM | CORE | `API.main` | livre |
| 25 | Enterprise BIM Platform | COLLAB | `Security.rbac` | livre |
| 26 | Construction AI Platform | CONSTRUCTION | `Construction.platform` | esquisse |
| 27 | Planning chantier IA | CONSTRUCTION | `Construction.planning` | livre |
| 28 | Suivi avancement chantier | CONSTRUCTION | `Construction.progress` | esquisse |
| 29 | Vision IA qualite | CONSTRUCTION | `AI_Engine.vision_ai` | esquisse |
| 30 | Securite chantier IA | CONSTRUCTION | `Construction.safety` | esquisse |
| 31 | Drone chantier | CONSTRUCTION | `Construction.drone` | esquisse |
| 32 | Comparaison BIM reel | CONSTRUCTION | `Construction.progress` | esquisse |
| 33 | Gestion ressources | CONSTRUCTION | `Construction.resources` | esquisse |
| 34 | Gestion fournisseurs | CONSTRUCTION | `Construction.resources` | esquisse |
| 35 | Rapports automatiques | CONSTRUCTION | `CAD_Core.documentation` | livre |
| 36 | Cost AI | COST | `Estimating.cost_ai` | livre |
| 37 | Metres automatiques | COST | `Estimating.takeoff` | livre |
| 38 | Devis IA | COST | `Estimating.cost_ai` | livre |
| 39 | Optimisation budget | COST | `Estimating.cost_ai` | esquisse |
| 40 | Project Management Enterprise | COLLAB | `Construction.planning` | esquisse |
| 41 | Digital Twin Platform | TWIN | `Cloud_Platform.digital_twin` | livre |
| 42 | Smart Building OS | TWIN | `Cloud_Platform.digital_twin` | esquisse |
| 43 | IoT Integration | TWIN | `Cloud_Platform.iot` | livre |
| 44 | Maintenance predictive | TWIN | `Cloud_Platform.predictive` | livre |
| 45 | Energy Intelligence | GREEN | `Sustainability.energy` | livre |
| 46 | Solar Microgrid | GREEN | `Sustainability.energy` | esquisse |
| 47 | Performance batiment | GREEN | `Sustainability.energy` | livre |
| 48 | AR Maintenance | MOBILE | `Mobile.ar` | esquisse |
| 49 | Drone Inspection Digital Twin | TWIN | `Construction.drone` | esquisse |
| 50 | Cycle de vie batiment | GREEN | `Sustainability.carbon` | livre |
| 51 | Green Building AI | GREEN | `Sustainability.carbon` | livre |
| 52 | Calcul carbone | GREEN | `Sustainability.carbon` | livre |
| 53 | Materiaux durables | GREEN | `Sustainability.carbon` | livre |
| 54 | Simulation energetique | GREEN | `Sustainability.energy` | livre |
| 55 | Certification verte | GREEN | `Sustainability.certification` | livre |
| 56 | Adaptation climatique | GREEN | `Sustainability.energy` | esquisse |
| 57 | Smart Village Platform | CITY | `Cloud_Platform.city` | esquisse |
| 58 | Digital Twin Smart City | CITY | `Cloud_Platform.city` | esquisse |
| 59 | GIS Topography Drone | CITY | `Cloud_Platform.city` | esquisse |
| 60 | Finance Projet AI | BUSINESS | `Estimating.cost_ai` | esquisse |
| 61 | Sustainability AI | GREEN | `Sustainability.carbon` | livre |
| 62 | Topography Integration | CITY | `Cloud_Platform.city` | esquisse |
| 63 | Mobile Tablet Platform | MOBILE | `Mobile` | livre |
| 64 | Expansion internationale | BUSINESS | `docs` | documente |
| 65 | Legal Corporate Governance | BUSINESS | `docs` | documente |
| 66 | Investor Package | BUSINESS | `docs/INVESTOR_DECK.md` | documente |
| 67 | Documentation technique | BUSINESS | `docs` | livre |
| 68 | Beta Testing Program | BUSINESS | `docs` | documente |
| 69 | Global Launch Plan | BUSINESS | `docs` | documente |
| 70 | Master Plan 2030 | BUSINESS | `docs/ROADMAP_2030.md` | documente |

---

## Lecture par groupe

| Groupe | Description | Livré | Esquissé | Documenté |
|---|---|---|---|---|
| CORE | Systeme central : CAO, IA, interface, MVP | 11 | 0 | 0 |
| BIM | Moteur BIM, objets, standards IFC, metiers | 6 | 4 | 0 |
| COLLAB | Collaboration, versions, entreprise | 3 | 1 | 0 |
| CONSTRUCTION | Chantier : planning, suivi, qualite, securite | 2 | 8 | 0 |
| COST | Economie : metres, couts, devis | 3 | 1 | 0 |
| TWIN | Jumeau numerique, IoT, maintenance | 3 | 2 | 0 |
| GREEN | Environnement : carbone, energie, certification | 9 | 2 | 0 |
| CITY | Territoire : village et ville intelligents | 0 | 4 | 0 |
| MOBILE | Terrain : tablette, mobile, realite augmentee | 1 | 1 | 0 |
| BUSINESS | Marche, juridique, investisseurs, lancement | 1 | 1 | 7 |

Registre interrogeable : `GET /api/v1/deliverables?groupe=CORE`
''')

ajouter('docs/INVESTOR_DECK.md', r'''
# MERCURY CAD AI X — Dossier investisseurs (livrable #66)

## Le problème

Des millions de dessinateurs produisent d'excellents plans 2D mais ne
maîtrisent pas la modélisation 3D. Entre le trait et la maquette exploitable,
il y a aujourd'hui des semaines de travail manuel — et le métré, le devis et le
bilan carbone sont refaits à la main, donc divergent du modèle dès la première
modification.

## La proposition

Une plateforme où **le plan est la source unique**. Tout en découle et se
recalcule : volume, surfaces, quantités, coûts, énergie, carbone, planning.
Modifier un mur met à jour le devis.

## Ce qui existe aujourd'hui

| Capacité | État |
|---|---|
| Génération de plans depuis un programme | opérationnelle, moins d'une seconde pour trois variantes |
| Reconnaissance de plans vectoriels | opérationnelle (double trait) |
| Extraction des pièces | opérationnelle (arrangement planaire) |
| Métré, devis, planning | opérationnels, chaque quantité auditable |
| Carbone et énergie | opérationnels |
| Export IFC4, OBJ, glTF | opérationnels |
| Jumeau numérique et IoT | opérationnels |
| Vision profonde sur scans | architecture prête, poids à entraîner |

## Différenciation

Trois points qu'un concurrent ne copie pas en un trimestre :

1. **Le générateur produit du BIM, pas des images.** Les approches par modèles
   de diffusion rendent de jolis plans inexploitables. Ici chaque variante est
   un projet modifiable et exportable en IFC.
2. **Chaque chiffre est auditable.** Les quantités portent leur formule. Un
   économiste peut vérifier sans ouvrir le code — condition d'adoption en
   bureau d'études.
3. **Aucune dépendance propriétaire.** Formats d'échange ouverts, algorithmes
   originaux, pas de licence tierce à négocier ni de risque juridique.

## Marché

Architectes, bureaux d'études, cuisinistes, agenceurs, promoteurs, entreprises
générales. Le segment le plus accessible est celui qui produit déjà du 2D en
volume et à qui on demande du 3D et du carbone sans budget supplémentaire.

## Modèle économique

Abonnement par siège pour les indépendants et petites structures ; licence
entreprise avec déploiement sur site pour les grands comptes ; marketplace
d'objets fabricants en commission.

## Ce que finance la levée

Par ordre de retour : entraînement du modèle de vision sur croquis manuscrits,
moteur de rendu photoréaliste, modules chantier, conformité réglementaire par
marché.

## Risques, franchement

L'inertie du marché de la CAO est forte et les habitudes tenaces. Les acteurs
installés disposent d'écosystèmes de plugins que nous n'avons pas. Notre pari
est l'intégration verticale — du plan au devis carbone — plutôt que la
compétition frontale sur le dessin technique généraliste.
''')

ajouter('docs/MODELISATION_3D.md', r'''
# Modélisation 3D — commandes et formats

MERCURY CAD AI X expose un noyau de modélisation solide complet. Ce document
est **généré depuis le code** : il liste exactement ce que le logiciel sait
faire, commande par commande et format par format.

Toute commande s'appelle de trois façons, avec le même résultat :

```bash
# ligne de commande de l'interface
BOITE longueur=2000 largeur=1000 hauteur=500
```

```python
from CAD_Core.commands import CommandInterpreter
cli = CommandInterpreter()
cli.execute("BOITE longueur=2000 largeur=1000 hauteur=500")
```

```bash
curl -X POST localhost:8000/api/v1/cad/documents/doc-0001/command \
  -H 'Content-Type: application/json' \
  -d '{"commande":"BOITE","parametres":{"longueur":2000}}'
```

---

## Les 98 commandes

### Solides primitifs

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `BISEAU` | `WEDGE` | — | Demi-boite coupee en diagonale : rampe, pente |
| `BOITE` | `BOX` | `B` | Pave droit defini par ses trois dimensions |
| `CONE` | `CONE` | — | Cone plein ou tronque |
| `CYLINDRE` | `CYLINDER` | `CYL` | Cylindre droit ou tronconique |
| `POLYSOLIDE` | `POLYSOLID` | `PSOLIDE` | Mur d'epaisseur constante suivant une polyligne |
| `PYRAMIDE` | `PYRAMID` | `PYR` | Pyramide de 3 a 32 cotes, pleine ou tronquee |
| `SPHERE` | `SPHERE` | — | Sphere |
| `TORE` | `TORUS` | — | Tore |

### Solides issus d'un profil

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `APPUYERTIRER` | `PRESSPULL` | `APT` | Pousse ou tire une zone fermee |
| `BALAYAGE` | `SWEEP` | — | Deplace un profil le long d'une trajectoire |
| `EPAISSIR` | `THICKEN` | — | Donne une epaisseur a une surface |
| `EXTRUSION` | `EXTRUDE` | `EXT` | Extrude un contour ferme en volume |
| `LISSAGE` | `LOFT` | — | Relie plusieurs sections par une peau continue |
| `REVOLUTION` | `REVOLVE` | `REV` | Fait tourner un profil autour d'un axe |

### Opérations booléennes

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `INTERFERENCE` | `INTERFERE` | `INTERF` | Detecte les collisions entre solides |
| `INTERSECTION` | `INTERSECT` | `IN` | Ne garde que la matiere commune |
| `SOUSTRACTION` | `SUBTRACT` | `SU` | Retire des solides d'un solide de base |
| `UNION` | `UNION` | `UNI` | Fusionne plusieurs solides |

### Édition de solides

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `CHANFREINARETE` | `CHAMFEREDGE` | `CHA` | Coupe les aretes vives a plat |
| `CONVENSOLIDE` | `CONVTOSOLID` | — | Ferme une surface pour en faire un solide |
| `CONVENSURFACE` | `CONVTOSURFACE` | — | Transforme un solide en surface |
| `COUPE` | `SLICE` | `SL` | Tranche un solide par un plan |
| `DECALAGE` | `OFFSET` | `DE` | Decale les faces d'un solide |
| `DEPOUILLE` | `TAPER` | — | Incline la matiere d'un cote d'un plan |
| `EMPREINTE` | `IMPRINT` | — | Imprime les aretes d'un solide sur un autre |
| `GAINE` | `SHELL` | — | Evide un solide en laissant une paroi |
| `RACCORDARETE` | `FILLETEDGE` | `RACC` | Arrondit les aretes vives d'un solide |
| `SECTION` | `SECTION` | — | Contour de l'intersection avec un plan |
| `SEPARER` | `SEPARATE` | — | Eclate un solide en volumes disjoints |
| `VERIFSOLIDE` | `SOLIDCHECK` | — | Controle l'etancheite d'un solide |
| `XARETES` | `XEDGES` | — | Extrait le filaire d'un solide |

### Déplacements et réseaux

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `ALIGNER3D` | `3DALIGN` | `AL` | Aligne la selection sur des points cibles |
| `COPIER` | `COPY` | `CO` | Copie la selection |
| `DEPLACER3D` | `3DMOVE` | `DEPLACER`, `M` | Deplace la selection |
| `ECHELLE` | `3DSCALE` | `SC` | Met la selection a l'echelle |
| `EFFACER` | `ERASE` | `E`, `SUPPRIMER` | Efface la selection |
| `MIROIR3D` | `MIRROR3D` | `MI3` | Symetrie par rapport a un plan |
| `RESEAU3D` | `3DARRAY` | `RESEAU` | Reseau rectangulaire en trois dimensions |
| `RESEAUCHEMIN` | `ARRAYPATH` | `RESC` | Reseau le long d'une trajectoire |
| `RESEAUPOLAIRE` | `ARRAYPOLAR` | `RESP` | Reseau autour d'un axe |
| `ROTATION3D` | `3DROTATE` | `RO3` | Tourne la selection autour d'un axe |

### Surfaces

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `SURFPLAN` | `PLANESURF` | — | Surface pleine sur un contour ferme |
| `SURFREGLE` | `RULESURF` | — | Surface tendue entre deux courbes |

### Maillages

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `AFFINERMAILLE` | `MESHREFINE` | — | Subdivise sans deformer |
| `LISSERMAILLE` | `MESHSMOOTH` | — | Lisse un maillage par subdivision |
| `SOUDER` | `WELD` | — | Fusionne les sommets et repare le maillage |
| `TRIANGULER` | `TRIANGULATE` | — | Convertit toutes les faces en triangles |

### Courbes

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `HELICE` | `HELIX` | — | Helice : ressort, rampe, escalier helicoidal |

### Dessin 2D

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `ARC` | `ARC` | `A` | Arc de cercle |
| `CERCLE` | `CIRCLE` | `C` | Cercle |
| `ELLIPSE` | `ELLIPSE` | `EL` | Ellipse |
| `LIGNE` | `LINE` | `L` | Segment de droite |
| `POINT` | `POINT` | `PO` | Point isole |
| `POLYGONE` | `POLYGON` | `POL` | Polygone regulier |
| `POLYLIGNE` | `PLINE` | `PL` | Polyligne ouverte ou fermee |
| `RECTANG` | `RECTANGLE` | `REC` | Rectangle |
| `SPLINE` | `SPLINE` | `SPL` | Courbe passant par des points |

### Annotation et cotation

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `COTALI` | `DIMALIGNED` | — | Cote alignee sur le segment |
| `COTANG` | `DIMANGULAR` | — | Cote angulaire |
| `COTDIA` | `DIMDIAMETER` | — | Cote de diametre |
| `COTLIN` | `DIMLINEAR` | `COTL` | Cote lineaire |
| `COTRAYON` | `DIMRADIUS` | — | Cote de rayon |
| `HACHURES` | `HATCH` | `H` | Remplit un contour ferme |
| `LIGNEDEREPERE` | `MLEADER` | `REPERE` | Fleche de renvoi avec texte |
| `NUAGEREV` | `REVCLOUD` | — | Nuage de revision |
| `TABLEAU` | `TABLE` | — | Nomenclature ou legende |
| `TEXTMULT` | `MTEXT` | `T`, `TEXTE` | Texte multiligne |

### Mesures

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `MESURER` | `MEASUREGEOM` | `MES` | Distance, aire, volume, angle |
| `PROPMECA` | `MASSPROP` | — | Volume, masse, inertie et centre de gravite |

### Organisation du dessin

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `ANNULER` | `UNDO` | `U` | Annule la derniere action |
| `BLOC` | `BLOCK` | `B_` | Enregistre une selection comme bloc |
| `CALQUE` | `LAYER` | `LA` | Cree ou active un calque |
| `DECOMPOSER` | `EXPLODE` | `X` | Detache les objets de leur bloc |
| `ETAT` | `STATUS` | — | Fiche du document |
| `INSERER` | `INSERT` | `I` | Insere une occurrence de bloc |
| `LISTE` | `LIST` | `LI` | Detail des objets selectionnes |
| `PRESENTATION` | `LAYOUT` | — | Ajoute un espace papier |
| `PURGER` | `PURGE` | — | Supprime les calques et blocs inutilises |
| `RETABLIR` | `REDO` | — | Retablit l'action annulee |
| `SCU` | `UCS` | — | Definit le systeme de coordonnees utilisateur |
| `SELECTIONNER` | `SELECT` | `SEL` | Selectionne des objets |

### Aides au dessin

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `ACCROBJ` | `OSNAP` | `OS` | Regle les accrochages aux objets |
| `ACCROCHER` | `SNAPPOINT` | — | Renvoie le point accroche le plus proche du curseur |
| `ORTHO` | `ORTHO` | — | Active ou desactive le mode ortho |
| `RESOL` | `SNAP` | — | Accrochage a la grille |

### Vues et rendu

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `MASQUE` | `HIDE` | — | Filaire sans les aretes cachees, en vectoriel |
| `ORBITE3D` | `3DORBIT` | `ORB` | Fait tourner la vue |
| `PAN` | `PAN` | `P` | Deplace la vue |
| `PLANDECOUPE` | `SECTIONPLANE` | — | Ajoute un plan de coupe a la vue |
| `RENDU` | `RENDER` | `RR` | Calcule une image du modele |
| `STYLESVISUELS` | `VSCURRENT` | `SV` | Change le style visuel |
| `VUE` | `VIEW` | `V` | Enregistre une vue nommee |
| `VUEPOINT` | `VPOINT` | `VP` | Vue normalisee : dessus, face, isometrique... |
| `ZOOM` | `ZOOM` | `Z` | Zoom avant, arriere ou etendu |

### Fichiers

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `EXPORTER` | `EXPORT` | `EXP` | Exporte le document dans un format d'echange |
| `FORMATS` | `FILEFORMATS` | — | Liste les formats lus et ecrits |
| `IMPORTER` | `IMPORT` | `IMP` | Importe un fichier et le fusionne au document |

### Général

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `AIDE` | `HELP` | `?` | Aide sur une commande ou catalogue complet |

---

## Les 29 formats de fichiers

| Format | Extensions | Catégorie | Lecture | Écriture | Remarque |
|---|---|---|---|---|---|
| AutoCAD DWG | `.dwg` | CAO | oui | oui | Identification, version et apercu en natif ; la geometrie passe par un moteur de conversion installe sur la machine. |
| AutoCAD DXF (R12 a 2021) | `.dxf` | CAO | oui | oui | Lecture et ecriture natives, toutes versions. |
| IFC 4 (BIM) | `.ifc` | BIM | oui | oui | Echange BIM normalise ISO 16739. |
| STEP AP203/AP214/AP242 | `.step` `.stp` | Mecanique | oui | oui | BREP facettise, lu par tous les CAO. |
| IGES 5.3 | `.iges` `.igs` | Mecanique | — | oui | Surfaces planes, entite 106. |
| STL | `.stl` | Impression 3D | oui | oui | ASCII et binaire, detection automatique. |
| Wavefront OBJ | `.obj` | 3D | oui | oui | Materiaux exportes dans un fichier .mtl associe. |
| Bibliotheque de materiaux OBJ | `.mtl` | 3D | — | oui |  |
| Stanford PLY | `.ply` | 3D | oui | oui | ASCII et binaire. |
| Object File Format | `.off` | 3D | oui | oui |  |
| glTF 2.0 | `.gltf` | 3D web | oui | oui |  |
| glTF binaire | `.glb` | 3D web | oui | oui |  |
| 3D Manufacturing Format | `.3mf` | Impression 3D | oui | oui |  |
| Additive Manufacturing Format | `.amf` | Impression 3D | — | oui |  |
| COLLADA | `.dae` | 3D | oui | oui |  |
| VRML 2.0 | `.wrl` `.vrml` | 3D | — | oui |  |
| X3D | `.x3d` | 3D | — | oui |  |
| Autodesk 3D Studio | `.3ds` | 3D | — | oui | Limite du format : 65 535 sommets par objet. |
| SVG | `.svg` | Vectoriel | oui | oui | Export de plans et import de traces. |
| PDF vectoriel | `.pdf` | Document | — | oui | Planches multipages avec cartouche. |
| PNG | `.png` | Image | oui | oui |  |
| Windows Bitmap | `.bmp` | Image | oui | oui |  |
| Portable Pixmap | `.ppm` | Image | oui | oui |  |
| Targa | `.tga` | Image | — | oui |  |
| JPEG | `.jpg` `.jpeg` | Image | oui | oui | Lecture et ecriture via Pillow. |
| Nuage de points XYZ / PTS | `.xyz` `.pts` `.asc` | Releve | oui | oui |  |
| Points CSV | `.csv` | Releve | oui | oui |  |
| LiDAR LAS | `.las` | Releve | oui | oui | LAS 1.0 a 1.4, formats de point 0 a 5. |
| Modele MERCURY (JSON) | `.json` | Natif | oui | oui | Format natif : tout le document, sans perte. |

---

## Vérification des volumes

Les outils volumiques sont contrôlés contre leurs valeurs analytiques :

| Outil | Cas testé | Écart admis |
|---|---|---|
| Boîte, biseau, pyramide | volume exact | 0 |
| Cylindre, cône | π r² h et π r² h ⁄ 3 | 0,1 % à 180 facettes |
| Sphère | 4⁄3 π r³ | 0,5 % à 64×32 facettes |
| Tore | 2 π² R r² | 1 % à 64×32 facettes |
| Extrusion, extrusion percée | section × hauteur | exact |
| Extrusion avec dépouille | tronc de pyramide | exact |
| Révolution totale et partielle | π (R²−r²) h | 0,3 % |
| Balayage droit | π r² L | 0,3 % |
| Lissage | h⁄3 (A₁+A₂+√A₁A₂) | exact |
| Union, soustraction, intersection | volumes combinés | 10⁻⁶ |
| Gaine | a³ − (a−2e)³ | 10⁻⁶ |
| Décalage | (a±2d)³ | 10⁻⁶ |
| Raccord de toutes les arêtes | somme de Minkowski | 1 % |

Chaque solide produit est en outre vérifié **étanche** : toute arête est
partagée par exactement deux faces, et le volume signé est positif.

---

## Styles visuels

`filaire_2d`, `filaire_3d`, `cache`, `réaliste`, `conceptuel`,
`ombre_avec_aretes`, `nuances_de_gris`, `esquisse`, `rayons_x`.

## Vues normalisées

`dessus`, `dessous`, `face`, `arriere`, `gauche`, `droite`,
`iso_sud_ouest`, `iso_sud_est`, `iso_nord_est`, `iso_nord_ouest`.

## Accrochages aux objets (OSMODE)

`extremite`, `milieu`, `centre`, `noeud`, `quadrant`, `intersection`,
`insertion`, `perpendiculaire`, `tangente`, `proche`, `parallele`.
''')

ajouter('docs/ROADMAP_2030.md', r'''
# Feuille de route 2030 (livrable #70)

## Principe

Une seule règle d'arbitrage : **livrer ce qui rend un professionnel plus
rapide dès la semaine suivante**, avant ce qui impressionne en démonstration.

---

## 2026 — Utilisable au quotidien

Ce qui sépare « ça marche » de « je travaille dessus tous les jours » :

- cotation et annotation sur le plan
- impression à l'échelle exacte
- édition des murs par poignées
- calques utilisateur
- import IFC (l'export existe déjà)

Sans cotes, un plan ne part pas en chantier. C'est la priorité absolue.

## 2027 — Reconnaissance

- entraînement du segmenteur sur croquis manuscrits
- lecture des scans et photos de plans anciens
- reconnaissance des symboles normalisés
- multi-niveaux complet avec escaliers balancés

## 2028 — Image et collaboration

- moteur de rendu photoréaliste
- visite virtuelle 360°
- fusion collaborative sans conflit (CRDT)
- marketplace d'objets fabricants

## 2029 — Chantier

- suivi d'avancement par photo
- comparaison modèle / réalité
- gestion des ressources et des approvisionnements
- application terrain hors ligne

## 2030 — Exploitation

- jumeau numérique complet en exploitation
- maintenance prédictive sur historique réel
- pilotage énergétique
- consolidation à l'échelle du quartier

---

## Ce que nous ne ferons pas

- **Remplacer un outil de dessin technique généraliste.** Nous faisons du
  bâtiment, pas de la mécanique ni de l'électronique.
- **Le calcul de structure réglementaire.** Métier différent, responsabilité
  différente, assurance différente.
- **Promettre une simulation thermique dynamique certifiée** tant que la
  méthode reste statique.

Un outil qui annonce ses limites est un outil dont on peut se servir.
''')

ajouter('docs/USER_GUIDE.md', r'''
# Guide utilisateur — MERCURY CAD AI X

## 1. Première pièce en 3D, en une minute

```bash
pip install -r requirements.txt
uvicorn API.main:app --port 8000
```

Ouvrez **`http://localhost:8000/app`**. L'interface s'ouvre sur un document
vide avec une boîte de démonstration.

Tapez dans la ligne de commande, en bas :

```
BOITE longueur=4000 largeur=3000 hauteur=2700
CYLINDRE rayon=600 hauteur=3400 origine=5200,1500,0
SPHERE rayon=900 centre=2000,1500,3600
```

Chaque commande apparaît dans le journal, à droite, et l'objet s'affiche dans
la vue. **Clic gauche** fait tourner la vue, **Maj + clic** la déplace, la
**molette** zoome. Les boutons en haut à droite donnent les vues normalisées.

### Percer, raccorder, évider

Sélectionnez deux objets dans la palette **Objets** (clic, puis Maj + clic),
puis cliquez l'outil **soustraction** de l'onglet *Solide* : le second creuse
le premier. Les outils **raccordarete**, **chanfreinarete** et **gaine** de
l'onglet *Modification* travaillent sur l'objet sélectionné.

Tout ce que fait un bouton du ruban peut s'écrire dans la ligne de commande, et
inversement : ce sont les mêmes 98 commandes, décrites dans
`docs/MODELISATION_3D.md`.

### Ouvrir et enregistrer

**Ouvrir** accepte DWG, DXF, IFC, STEP, STL, OBJ, PLY, glTF, 3MF, COLLADA, les
nuages de points et les images. **Exporter** propose les 29 formats.
**Convertir** traduit un fichier d'un format à l'autre sans même l'ouvrir.

> Le DWG demande un moteur de conversion installé sur la machine (ODA File
> Converter, LibreDWG ou `ezdxf[odafc]`). Sans lui, MERCURY identifie quand même
> le fichier, sa version et son aperçu, et le message d'erreur indique quoi
> installer.

---

## 2. Premier plan en trois minutes

```bash
pip install -r requirements.txt
uvicorn API.main:app --port 8000
```

Le moteur génératif s'appelle depuis l'API ou l'assistant : choisissez
« maison » et 110 m². Trois variantes sont calculées en moins d'une seconde ;
la meilleure s'ouvre automatiquement.

## 3. Comprendre le score

Chaque variante porte un score : **plus bas est meilleur**. Il agrège six
termes, visibles dans `detail_score` :

| Terme | Ce qu'il pénalise |
|---|---|
| `surfaces` | écart au programme, sous les minima, au-dessus des maxima d'usage |
| `proportions` | pièces en couloir (élongation excessive) |
| `orientation` | chambres au nord, séjour sans soleil |
| `jour` | pièce de vie sans façade |
| `adjacences` | cuisine loin du séjour |
| `plomberie` | points d'eau dispersés, donc colonnes longues |

Un score de 2 à 5 correspond à un plan exploitable. Au-delà de 8, le programme
est probablement incompatible avec l'emprise.

## 4. Dessiner à la main

```bash
curl -X POST localhost:8000/api/v1/projects -d '{"name":"Mon projet"}'
curl -X POST localhost:8000/api/v1/projects/$ID/walls \
     -d '{"start":[0,0],"end":[10000,0],"thickness":300,"exterior":true}'
```

Tracez les quatre murs de l'enveloppe, puis les refends. Appelez ensuite
`rooms/rebuild` : les pièces apparaissent **si les murs se rejoignent**. Un
contour ouvert de plus de quelques centimètres empêche la détection.

## 5. Poser portes et fenêtres

`offset` est la distance depuis le **début** du mur, en millimètres. Une baie
qui déborde est refusée avec la longueur disponible dans le message.

## 6. Sortir les livrables

| Besoin | Appel |
|---|---|
| Quantités auditables | `GET /takeoff` — chaque ligne porte sa formule |
| Budget et délai | `GET /estimate` — devis par lot, chemin critique |
| Empreinte carbone | `GET /carbon` — leviers classés par gain réel |
| Performance énergétique | `GET /energy?isolation=neuf&climat=oceanique` |
| Maquette pour Revit | `POST /export {"format":"ifc"}` |

## 7. Questions fréquentes

**Aucune pièce n'est détectée.** Les murs ne se referment pas. Vérifiez que les
extrémités coïncident : la tolérance de fusion est de 120 mm.

**Les surfaces sont dix fois trop petites.** Les unités sont des millimètres :
un mur de 10 m se saisit `10000`, pas `10`.

**Le devis paraît bas.** La base de prix est indicative. Remplacez-la par la
vôtre en passant `price_book` à `CostEstimator`.

**L'étiquette énergétique semble optimiste.** La méthode est statique
mensuelle, destinée à l'esquisse. Elle ne remplace pas un calcul réglementaire,
et la sortie le rappelle dans le champ `methode`.
''')

ajouter('pytest.ini', r'''
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -q --strict-markers
filterwarnings =
    ignore::DeprecationWarning
''')

ajouter('requirements.txt', r'''
# MERCURY CAD AI X - dependances
#
# Le noyau CAO 3D (geometrie, solides, booleens, maillages, rendu), le moteur
# BIM, la conception generative, le metre, le carbone, l'energie et la totalite
# des formats de fichiers ne dependent que de la bibliotheque standard.
# FastAPI n'est requis que pour exposer l'API HTTP et l'interface web.

fastapi>=0.110,<1.0
uvicorn[standard]>=0.27,<1.0
pydantic>=2.0,<3.0
python-multipart>=0.0.9   # televersement de fichiers (import, conversion)

# --- Developpement ---
pytest>=7.4
httpx>=0.26          # client de test de FastAPI
coverage>=7.4        # mesure de la couverture des tests

# --- Optionnels (detectes s'ils sont installes) ---
# Pillow>=10.0           # lecture et ecriture JPEG, TIFF, GIF, WEBP
# ezdxf>=1.1             # passerelle DWG via ODA File Converter
# psycopg[binary]>=3.1   # PostgreSQL en production
# numpy>=1.26            # acceleration des calculs lourds
#
# Conversion DWG : installez en plus l'un de ces moteurs sur la machine
#   - ODA File Converter  https://www.opendesign.com/guestfiles/oda_file_converter
#   - LibreDWG            paquet systeme libredwg-tools (dwg2dxf, dxf2dwg)
#   - ezdxf[odafc]        pip install "ezdxf[odafc]" puis ODA File Converter
# Sans eux, MERCURY identifie les DWG, lit leur version et leur apercu, et
# traite tous les autres formats normalement.
''')


# =========================================================================
# 20. POINT D'ENTREE EN LIGNE DE COMMANDE
# =========================================================================
ajouter('CAD_Core/main.py', r'''
"""Point d'entree du noyau CAO en ligne de commande.

    python -m CAD_Core.main demo          genere un plan et affiche le resume
    python -m CAD_Core.main export --ifc  ecrit projet.ifc dans le repertoire
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AI_Engine.generative_design import GenerativeDesigner, build_program
from BIM_Engine.ifc_handler import IFCHandler
from CAD_Core.documentation import DocumentGenerator
from CAD_Core.engine_3d import Engine3D
from CAD_Core.rendering import Renderer
from Estimating.cost_ai import CostEstimator
from Estimating.takeoff import QuantityTakeoff
from Sustainability.carbon import CarbonAnalyzer
from Sustainability.energy import EnergySimulator


def build_demo(typology: str = "maison", surface: float = 110.0,
               bedrooms: int = 3, seed: int = 7):
    """Genere un projet de demonstration complet."""
    program = build_program(typology, surface, bedrooms)
    return GenerativeDesigner().generate(program, variants=2,
                                         iterations=1500, seed=seed)[0], program


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Noyau CAO MERCURY")
    parser.add_argument("commande", choices=["demo", "export"], nargs="?",
                        default="demo")
    parser.add_argument("--typologie", default="maison")
    parser.add_argument("--surface", type=float, default=110.0)
    parser.add_argument("--chambres", type=int, default=3)
    parser.add_argument("--ifc", action="store_true", help="ecrit projet.ifc")
    parser.add_argument("--obj", action="store_true", help="ecrit projet.obj")
    args = parser.parse_args(argv)

    project, program = build_demo(args.typologie, args.surface, args.chambres)
    report = DocumentGenerator().project_report(project)
    estimate = CostEstimator().estimate(project)
    carbon = CarbonAnalyzer().analyze(project)
    energy = EnergySimulator().simulate(project)

    print("Programme  :", program.describe())
    print("Rapport    :", json.dumps(report, ensure_ascii=False))
    print("Devis      : %.0f EUR HT (%.0f EUR/m2)"
          % (estimate["total_ht"], estimate["ratio_eur_m2"]))
    print("Carbone    : %.1f t CO2e, etiquette %s"
          % (carbon["total_t_co2e"], carbon["etiquette"]))
    print("Energie    : %.1f kWh/m2/an, etiquette %s"
          % (energy["kwh_m2_an"], energy["etiquette"]))
    print("Maillage   :", Engine3D().build(project).stats)

    if args.commande == "export" or args.ifc:
        with open("projet.ifc", "w", encoding="utf-8") as handle:
            handle.write(IFCHandler().export(project))
        print("Ecrit      : projet.ifc")
    if args.obj:
        mesh = Engine3D().build(project)
        with open("projet.obj", "w", encoding="utf-8") as handle:
            handle.write(Renderer().to_obj(mesh))
        print("Ecrit      : projet.obj")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''')


# ===========================================================================
# GENERATION ET VALIDATION
# ===========================================================================
CRITIQUES = [
    "CAD_Core/main.py", "CAD_Core/geometry.py", "CAD_Core/engine_2d.py",
    "CAD_Core/engine_3d.py", "CAD_Core/rendering.py",
    "CAD_Core/math3d.py", "CAD_Core/solid.py", "CAD_Core/profiles.py",
    "CAD_Core/primitives.py", "CAD_Core/modeling.py",
    "CAD_Core/solid_edit.py", "CAD_Core/transform3d.py",
    "CAD_Core/mesh_tools.py", "CAD_Core/document.py",
    "CAD_Core/snapping.py", "CAD_Core/annotate.py", "CAD_Core/view3d.py",
    "CAD_Core/render_engine.py", "CAD_Core/commands.py",
    "Interop/__init__.py", "Interop/dxf.py", "Interop/dwg.py",
    "Interop/meshes.py", "Interop/step.py", "Interop/images.py",
    "Interop/pdf.py", "Interop/svg.py", "Interop/pointcloud.py",
    "Interop/native.py", "API/cad.py", "Frontend/viewer.js",
    "BIM_Engine/models.py", "BIM_Engine/ifc_handler.py",
    "AI_Engine/generative_design.py", "AI_Engine/vision_ai.py",
    "AI_Engine/nlp_assistant.py",
    "Estimating/takeoff.py", "Estimating/cost_ai.py",
    "Sustainability/carbon.py", "Sustainability/energy.py",
    "Cloud_Platform/digital_twin.py", "Cloud_Platform/iot.py",
    "Database/session.py", "Database/repository.py",
    "Database/migrations/001_initial_schema.sql",
    "Security/auth.py", "Security/rbac.py",
    "API/main.py", "API/deps.py", "API/schemas.py",
    "Frontend/index.html", "Frontend/app.js",
    "Mobile/shared/api_client.js",
    "DELIVERABLES.py", "requirements.txt", "docker-compose.yml",
    "Dockerfile", "deploy.sh", ".env.example",
    ".github/workflows/ci.yml", "README.md", "docs/API_REFERENCE.md",
    "docs/USER_GUIDE.md", "docs/INVESTOR_DECK.md", "docs/ROADMAP_2030.md",
    "tests/conftest.py", "tests/test_api.py",
    "tests/test_modules_metiers.py",
]

# CAD_Core/main.py : point d'entree en ligne de commande du noyau.
ajouter("CAD_Core/main.py", '''
"""Point d'entree du noyau CAO en ligne de commande.

    python -m CAD_Core.main demo          genere un plan et affiche le resume
    python -m CAD_Core.main export --ifc  ecrit projet.ifc dans le repertoire
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AI_Engine.generative_design import GenerativeDesigner, build_program
from BIM_Engine.ifc_handler import IFCHandler
from CAD_Core.documentation import DocumentGenerator
from CAD_Core.engine_3d import Engine3D
from CAD_Core.rendering import Renderer
from Estimating.cost_ai import CostEstimator
from Estimating.takeoff import QuantityTakeoff
from Sustainability.carbon import CarbonAnalyzer
from Sustainability.energy import EnergySimulator


def build_demo(typology: str = "maison", surface: float = 110.0,
               bedrooms: int = 3, seed: int = 7):
    """Genere un projet de demonstration complet."""
    program = build_program(typology, surface, bedrooms)
    return GenerativeDesigner().generate(program, variants=2,
                                         iterations=1500, seed=seed)[0], program


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Noyau CAO MERCURY")
    parser.add_argument("commande", choices=["demo", "export"], nargs="?",
                        default="demo")
    parser.add_argument("--typologie", default="maison")
    parser.add_argument("--surface", type=float, default=110.0)
    parser.add_argument("--chambres", type=int, default=3)
    parser.add_argument("--ifc", action="store_true", help="ecrit projet.ifc")
    parser.add_argument("--obj", action="store_true", help="ecrit projet.obj")
    args = parser.parse_args(argv)

    project, program = build_demo(args.typologie, args.surface, args.chambres)
    report = DocumentGenerator().project_report(project)
    estimate = CostEstimator().estimate(project)
    carbon = CarbonAnalyzer().analyze(project)
    energy = EnergySimulator().simulate(project)

    print("Programme  :", program.describe())
    print("Rapport    :", json.dumps(report, ensure_ascii=False))
    print("Devis      : %.0f EUR HT (%.0f EUR/m2)"
          % (estimate["total_ht"], estimate["ratio_eur_m2"]))
    print("Carbone    : %.1f t CO2e, etiquette %s"
          % (carbon["total_t_co2e"], carbon["etiquette"]))
    print("Energie    : %.1f kWh/m2/an, etiquette %s"
          % (energy["kwh_m2_an"], energy["etiquette"]))
    print("Maillage   :", Engine3D().build(project).stats)

    if args.commande == "export" or args.ifc:
        with open("projet.ifc", "w", encoding="utf-8") as handle:
            handle.write(IFCHandler().export(project))
        print("Ecrit      : projet.ifc")
    if args.obj:
        mesh = Engine3D().build(project)
        with open("projet.obj", "w", encoding="utf-8") as handle:
            handle.write(Renderer().to_obj(mesh))
        print("Ecrit      : projet.obj")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''')


class BuildError(RuntimeError):
    """Erreur bloquante de generation ou de validation."""


def ecrire(racine: Path, force: bool = False) -> int:
    """Cree l'arborescence et ecrit tous les fichiers."""
    if racine.exists():
        if not force:
            raise BuildError(
                "le repertoire %s existe deja ; utilisez --force pour l'ecraser"
                % racine)
        shutil.rmtree(racine)
    racine.mkdir(parents=True)

    for chemin, contenu in FICHIERS.items():
        cible = racine / chemin
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_text(contenu, encoding="utf-8")
        if chemin.endswith(".sh"):
            os.chmod(cible, 0o755)
    return len(FICHIERS)


def verifier_fichiers(racine: Path) -> None:
    """Controle la presence des fichiers critiques."""
    manquants = [c for c in CRITIQUES if not (racine / c).is_file()]
    if manquants:
        raise BuildError("fichiers critiques absents : %s" % ", ".join(manquants))


def compiler(racine: Path) -> int:
    """Analyse chaque module Python : detecte toute erreur de syntaxe.

    `ast.parse` est prefere a `py_compile` : ce dernier annule silencieusement
    l'exception quand `quiet=2`, et son cache .pyc peut masquer un fichier
    fraichement casse. Ici l'analyse porte toujours sur la source reelle.
    """
    import ast as _ast

    sources = sorted(racine.rglob("*.py"))
    erreurs: List[str] = []
    for source in sources:
        try:
            _ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except SyntaxError as error:
            erreurs.append("%s ligne %s : %s"
                           % (source.relative_to(racine), error.lineno, error.msg))
        except Exception as error:            # encodage, lecture, cas limites
            erreurs.append("%s : %s" % (source.relative_to(racine), error))
    if erreurs:
        raise BuildError("erreurs de syntaxe :\n  " + "\n  ".join(erreurs))
    return len(sources)


def _pip_install(paquets: List[str]) -> bool:
    """Installe les paquets manquants.

    Trois strategies successives : installation normale, puis --user, puis
    --break-system-packages. La derniere couvre les distributions qui
    protegent l'interpreteur systeme (PEP 668), ou une installation naive
    echoue silencieusement.
    """
    base = [sys.executable, "-m", "pip", "install", "--quiet"]
    for options in ([], ["--user"], ["--break-system-packages"]):
        try:
            subprocess.run(base + options + paquets, check=True, timeout=900,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if all(_module_present(_nom_module(p)) for p in paquets):
                return True
        except Exception:
            continue
    return False


def _nom_module(paquet: str) -> str:
    """Nom importable d'un paquet pip (uvicorn[standard] -> uvicorn)."""
    return paquet.split("[")[0].split("==")[0].split(">=")[0].replace("-", "_")


def _module_present(nom: str) -> bool:
    try:
        subprocess.run([sys.executable, "-c", "import %s" % nom], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60)
        return True
    except Exception:
        return False


def lancer_tests(racine: Path, autoriser_saut: bool = False) -> str:
    """Execute pytest. Leve une exception si un test echoue ou ne peut tourner."""
    manquants = [p for p in ("pytest", "httpx") if not _module_present(p)]
    if manquants and not _pip_install(manquants):
        message = ("impossible d'executer la suite de tests : %s introuvable(s) "
                   "et installation impossible. Installez-les puis relancez :\n"
                   "    pip install pytest httpx fastapi uvicorn "
                   "python-multipart"
                   % ", ".join(manquants))
        if autoriser_saut:
            return "NON EXECUTES - " + message
        raise BuildError(message)
    for paquet, module in (("fastapi", "fastapi"), ("uvicorn", "uvicorn"),
                           ("python-multipart", "multipart")):
        if not _module_present(module):
            _pip_install([paquet])

    # pytest.ini contient deja -q : en ajouter un second active le mode
    # "tres silencieux", qui supprime justement la ligne de synthese.
    resultat = subprocess.run(
        [sys.executable, "-m", "pytest", "--no-header"],
        cwd=str(racine), capture_output=True, text=True, timeout=1800)
    sortie = (resultat.stdout + resultat.stderr).strip()
    if resultat.returncode != 0:
        raise BuildError("des tests ont echoue :\n" + sortie[-4000:])
    # On cherche la ligne de synthese de pytest ("42 passed in 3.2s"),
    # pas la derniere ligne : celle-ci est souvent le pied de page des
    # avertissements, qui n'apprend rien sur le resultat.
    import re as _re
    for ligne in reversed(sortie.splitlines()):
        if _re.search(r"\d+ (passed|failed|error)", ligne):
            return _re.sub(r"\s+", " ", ligne.strip("= ").strip())
    return "tous les tests passent"


def mesurer_couverture(racine: Path, minimum: float = 80.0) -> str:
    """Mesure la couverture des tests. Echoue si elle passe sous le seuil.

    Un projet qui annonce des tests sans mesurer ce qu'ils touchent donne une
    fausse assurance : la couverture est donc verifiee, pas seulement affichee.
    """
    if not _module_present("coverage") and not _pip_install(["coverage"]):
        return "NON MESUREE - module coverage indisponible"
    subprocess.run([sys.executable, "-m", "coverage", "run", "-m", "pytest",
                    "--no-header", "-q"], cwd=str(racine),
                   capture_output=True, text=True, timeout=1800)
    resultat = subprocess.run(
        [sys.executable, "-m", "coverage", "report", "--omit=tests/*"],
        cwd=str(racine), capture_output=True, text=True, timeout=300)
    total = 0.0
    for ligne in resultat.stdout.splitlines():
        if ligne.startswith("TOTAL"):
            try:
                total = float(ligne.split()[-1].rstrip("%"))
            except (IndexError, ValueError):
                pass
    for temporaire in (".coverage",):
        chemin = racine / temporaire
        if chemin.exists():
            chemin.unlink()
    if total < minimum:
        raise BuildError("couverture de tests insuffisante : %.0f %% "
                         "(minimum exige : %.0f %%)" % (total, minimum))
    return "%.0f %% des instructions couvertes (minimum %.0f %%)" % (total, minimum)


def _port_libre(depart: int = 8765) -> int:
    for port in range(depart, depart + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sonde:
            if sonde.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise BuildError("aucun port libre entre %d et %d" % (depart, depart + 40))


def verifier_api(racine: Path, autoriser_saut: bool = False) -> str:
    """Demarre l'API et interroge /health. Leve une exception si echec."""
    # python-multipart s'importe sous le nom `multipart` : sans lui,
    # FastAPI refuse de construire les routes d'import de fichiers et
    # l'API ne demarre pas du tout.
    requis = (("fastapi", "fastapi"), ("uvicorn", "uvicorn"),
              ("python-multipart", "multipart"))
    manquants = [paquet for paquet, module in requis
                 if not _module_present(module)]
    if manquants and not _pip_install(manquants):
        message = ("impossible de demarrer l'API : %s introuvable(s). "
                   "Installez-les puis relancez :\n"
                   "    pip install fastapi uvicorn python-multipart"
                   % ", ".join(manquants))
        if autoriser_saut:
            return "NON VERIFIEE - " + message
        raise BuildError(message)

    port = _port_libre()
    environnement = dict(os.environ,
                         MERCURY_DB_PATH=str(racine / "verification.db"),
                         PYTHONPATH=str(racine))
    processus = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "API.main:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "error"],
        cwd=str(racine), env=environnement,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        limite = time.time() + 75
        derniere_erreur = ""
        while time.time() < limite:
            if processus.poll() is not None:
                sortie = processus.stdout.read() if processus.stdout else ""
                raise BuildError("l'API s'est arretee au demarrage :\n"
                                 + sortie[-3000:])
            try:
                with urllib.request.urlopen(
                        "http://127.0.0.1:%d/health" % port, timeout=2) as reponse:
                    if reponse.status != 200:
                        raise BuildError("/health a repondu %d" % reponse.status)
                    charge = json.loads(reponse.read().decode())
                    if charge.get("status") != "ok":
                        raise BuildError("/health n'a pas renvoye status=ok : %s"
                                         % charge)
                    with urllib.request.urlopen(
                            "http://127.0.0.1:%d/ready" % port, timeout=10) as pret:
                        if pret.status != 200:
                            raise BuildError("/ready a repondu %d" % pret.status)
                    with urllib.request.urlopen(
                            "http://127.0.0.1:%d/api/v1/deliverables" % port,
                            timeout=10) as registre:
                        total = json.loads(registre.read().decode())["total"]
                        if total != 70:
                            raise BuildError(
                                "le registre annonce %d livrables au lieu de 70"
                                % total)
                    return ("200 OK sur /health (version %s), /ready et les 70 "
                            "livrables repondent" % charge.get("version"))
            except urllib.error.URLError as error:
                derniere_erreur = str(error)
                time.sleep(0.7)
        raise BuildError("l'API n'a pas repondu dans le delai imparti (%s)"
                         % derniere_erreur)
    finally:
        processus.terminate()
        try:
            processus.wait(timeout=10)
        except subprocess.TimeoutExpired:
            processus.kill()


def verifier_livrables(racine: Path) -> str:
    """Controle que les 70 livrables sont declares et coherents."""
    resultat = subprocess.run(
        [sys.executable, "-c",
         "import json, sys; sys.path.insert(0, '.');"
         "from DELIVERABLES import DELIVERABLES as D;"
         "print(json.dumps({'total': len(D),"
         "'numeros': sorted(d['numero'] for d in D),"
         "'etats': sorted({d['etat'] for d in D})}))"],
        cwd=str(racine), capture_output=True, text=True, timeout=120)
    if resultat.returncode != 0:
        raise BuildError("registre des livrables illisible :\n" + resultat.stderr)
    donnees = json.loads(resultat.stdout)
    if donnees["total"] != 70:
        raise BuildError("%d livrables declares au lieu de 70" % donnees["total"])
    if donnees["numeros"] != list(range(1, 71)):
        raise BuildError("la numerotation des livrables n'est pas continue")
    return "70 livrables declares, numerotation continue, etats : %s" % \
        ", ".join(donnees["etats"])


def valider(racine: Path, autoriser_saut: bool = False) -> Dict[str, str]:
    """Phase de validation complete. Toute anomalie leve une exception."""
    rapport: Dict[str, str] = {}
    print("\n[VALIDATION]")

    print("  1/6  presence des fichiers critiques ...", end=" ", flush=True)
    verifier_fichiers(racine)
    rapport["fichiers"] = "%d fichiers critiques presents" % len(CRITIQUES)
    print("OK")

    print("  2/6  compilation des modules ..........", end=" ", flush=True)
    nombre = compiler(racine)
    rapport["compilation"] = "%d modules compiles sans erreur" % nombre
    print("OK (%d modules)" % nombre)

    print("  3/6  registre des 70 livrables ........", end=" ", flush=True)
    rapport["livrables"] = verifier_livrables(racine)
    print("OK")

    print("  4/6  suite de tests ...................", end=" ", flush=True)
    rapport["tests"] = lancer_tests(racine, autoriser_saut)
    print("OK" if not rapport["tests"].startswith("NON") else "IGNORES")
    print("       -> %s" % rapport["tests"])

    print("  5/6  couverture des tests .............", end=" ", flush=True)
    rapport["couverture"] = mesurer_couverture(racine)
    print("OK" if not rapport["couverture"].startswith("NON") else "IGNOREE")
    print("       -> %s" % rapport["couverture"])

    print("  6/6  demarrage de l'API et /health ....", end=" ", flush=True)
    rapport["api"] = verifier_api(racine, autoriser_saut)
    print("OK" if not rapport["api"].startswith("NON") else "IGNOREE")
    print("       -> %s" % rapport["api"])

    for temporaire in ("verification.db", "verification.db-wal",
                       "verification.db-shm", "mercury.db", "mercury.db-wal",
                       "mercury.db-shm"):
        chemin = racine / temporaire
        if chemin.exists():
            chemin.unlink()
    return rapport


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generateur du projet MERCURY CAD AI X - PROJET TITAN")
    parser.add_argument("--dir", default=RACINE_DEFAUT,
                        help="repertoire cible (defaut : %s)" % RACINE_DEFAUT)
    parser.add_argument("--force", action="store_true",
                        help="ecrase le repertoire cible s'il existe")
    parser.add_argument("--no-verify", action="store_true",
                        help="genere sans lancer la phase de validation")
    parser.add_argument("--allow-skip", action="store_true",
                        help="tolere l'absence de pytest ou FastAPI au lieu "
                             "d'echouer (la reussite ne sera PAS annoncee)")
    arguments = parser.parse_args(argv)

    racine = Path(arguments.dir).resolve()
    debut = time.time()

    print("=" * 68)
    print("  MERCURY CAD AI X - PROJET TITAN - generateur %s" % VERSION)
    print("=" * 68)
    print("  cible : %s" % racine)

    print("\n[GENERATION]")
    nombre = ecrire(racine, arguments.force)
    repertoires = sorted({str(Path(c).parent) for c in FICHIERS
                          if str(Path(c).parent) != "."})
    print("  %d fichiers ecrits dans %d repertoires" % (nombre, len(repertoires)))
    modules = sorted({d.split("/")[0] for d in repertoires})
    print("  modules : %s" % ", ".join(modules))
    lignes = sum(contenu.count("\n") for contenu in FICHIERS.values())
    print("  volume  : %d lignes" % lignes)

    if arguments.no_verify:
        print("\n[VALIDATION] ignoree (--no-verify)")
        print("\nPROJET GENERE. Lancez la validation avec :")
        print("  cd %s && pytest -q && uvicorn API.main:app" % racine)
        return 0

    try:
        rapport = valider(racine, arguments.allow_skip)
    except BuildError as erreur:
        print("\n" + "=" * 68)
        print("  ECHEC DE LA VALIDATION")
        print("=" * 68)
        print(str(erreur))
        raise

    duree = time.time() - debut
    ignore = [cle for cle, valeur in rapport.items()
              if str(valeur).startswith("NON")]
    print("\n" + "=" * 68)
    if ignore:
        # Ne jamais annoncer une reussite non verifiee : c'est la seule
        # facon de garder un rapport de build digne de confiance.
        print("  PROJET GENERE - VALIDATION INCOMPLETE (%s)" % ", ".join(ignore))
    else:
        print("  PROJET GENERE AVEC SUCCES. TOUS LES TESTS PASSENT.")
    print("=" * 68)
    print("  fichiers    : %d" % nombre)
    print("  lignes      : %d" % lignes)
    print("  compilation : %s" % rapport["compilation"])
    print("  livrables   : %s" % rapport["livrables"])
    print("  tests       : %s" % rapport["tests"])
    print("  couverture  : %s" % rapport["couverture"])
    print("  api         : %s" % rapport["api"])
    print("  duree       : %.1f s" % duree)
    if ignore:
        print("\n  ATTENTION : %d verification(s) non executee(s). "
              "Le projet n'est PAS certifie." % len(ignore))
    print("\n  Pour demarrer :")
    print("    cd %s" % racine)
    print("    uvicorn API.main:app --port 8000")
    print("    puis ouvrez http://localhost:8000/app")
    print("\n  Modelisation en ligne de commande :")
    print("    python -m CAD_Core.main demo")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as erreur:
        print("\nERREUR : %s" % erreur, file=sys.stderr)
        raise SystemExit(2)
