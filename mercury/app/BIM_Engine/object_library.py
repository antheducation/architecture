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
