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
