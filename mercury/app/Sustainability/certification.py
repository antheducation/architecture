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
