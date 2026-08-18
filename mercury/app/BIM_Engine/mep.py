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
