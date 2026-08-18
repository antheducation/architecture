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
