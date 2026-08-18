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
