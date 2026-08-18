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
