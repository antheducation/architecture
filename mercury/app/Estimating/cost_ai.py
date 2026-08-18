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
