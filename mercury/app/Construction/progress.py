"""Suivi d'avancement (livrables #28 et #32).

Compare l'avance declaree ou constatee au planning, et signale les derives
avant qu'elles ne deviennent des retards de livraison.
"""
from __future__ import annotations

from typing import Dict, List


class ProgressTracker:
    """Confronte l'avancement reel au planning previsionnel."""

    def assess(self, plan: Dict[str, object],
               reported: Dict[str, float], today: int) -> Dict[str, object]:
        lines: List[Dict[str, object]] = []
        delayed = 0
        for task in plan.get("taches", []):
            lot = str(task["lot"])
            expected = self._expected(task, today)
            actual = max(0.0, min(1.0, reported.get(lot, 0.0)))
            drift = actual - expected
            status = ("en avance" if drift > 0.05 else
                      "conforme" if drift >= -0.05 else "en retard")
            if status == "en retard":
                delayed += 1
            lines.append({
                "lot": lot,
                "avancement_attendu": round(expected * 100, 1),
                "avancement_reel": round(actual * 100, 1),
                "ecart_points": round(drift * 100, 1),
                "statut": status,
                "critique": bool(task.get("critique")),
            })
        critical_late = [l for l in lines
                         if l["statut"] == "en retard" and l["critique"]]
        return {
            "jour": today,
            "lignes": lines,
            "lots_en_retard": delayed,
            "retard_sur_chemin_critique": len(critical_late),
            "alerte": ("le retard touche le chemin critique : la date de "
                       "livraison est menacee" if critical_late else
                       "aucun retard sur le chemin critique"),
        }

    @staticmethod
    def _expected(task: Dict[str, object], today: int) -> float:
        start = float(task["debut_jour"])
        end = float(task["fin_jour"])
        if today <= start:
            return 0.0
        if today >= end:
            return 1.0
        return (today - start) / max(1.0, end - start)
