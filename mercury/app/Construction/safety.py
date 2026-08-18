"""Securite chantier (livrable #30).

Identifie les risques a partir de la geometrie du projet et de la phase en
cours. Une analyse geometrique ne remplace pas un coordonnateur SPS, et le
module le dit.
"""
from __future__ import annotations

from typing import Dict, List

PHASE_RISKS = {
    "Structure": ["chute de hauteur", "manutention lourde", "engins de levage"],
    "Gros oeuvre": ["chute de hauteur", "effondrement", "poussieres"],
    "Couverture": ["chute de hauteur", "intemperies"],
    "Cloisons": ["poussieres", "coupures"],
    "Menuiseries": ["manutention vitrage", "coupures"],
    "Revetements": ["produits chimiques", "postures"],
    "Peinture": ["solvants", "ventilation insuffisante"],
    "Equipements": ["electricite", "co-activite"],
}


class SafetyAnalyzer:
    """Analyse des risques par phase et par geometrie."""

    def analyze(self, project, phase: str = "Gros oeuvre") -> Dict[str, object]:
        risks: List[Dict[str, object]] = []
        for label in PHASE_RISKS.get(phase, []):
            risks.append({"risque": label, "origine": "phase " + phase,
                          "gravite": "haute" if "chute" in label else "moyenne"})

        height = max((w.height for w in project.walls), default=0.0)
        if height > 3000:
            risks.append({"risque": "travail en hauteur superieur a 3 m",
                          "origine": "geometrie (%.1f m)" % (height / 1000.0),
                          "gravite": "haute"})
        large = [r for r in project.rooms if r.area_m2 > 60]
        if large:
            risks.append({"risque": "grande portee : etaiement a verifier",
                          "origine": "%d piece(s) de plus de 60 m2" % len(large),
                          "gravite": "moyenne"})
        openings = sum(len(w.openings) for w in project.walls)
        if openings:
            risks.append({"risque": "tremies et baies non protegees",
                          "origine": "%d ouvertures" % openings,
                          "gravite": "haute"})
        return {
            "phase": phase,
            "risques": sorted(risks, key=lambda r: 0 if r["gravite"] == "haute" else 1),
            "nombre": len(risks),
            "avertissement": "analyse indicative : ne remplace pas le plan general "
                             "de coordination ni le coordonnateur SPS",
        }
