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
