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
