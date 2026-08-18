"""Module structure (livrable #17) - descente de charges simplifiee.

Perimetre assume : predimensionnement en phase esquisse. Ce n'est pas une
note de calcul reglementaire ; le module le declare dans sa sortie plutot
que de laisser croire a une verification Eurocode.
"""
from __future__ import annotations

from typing import Dict, List

CHARGES_KN_M2 = {
    "habitation": 1.5, "bureau": 2.5, "commerce": 5.0,
    "entrepot": 7.5, "parking": 2.5,
}
POIDS_PROPRE_DALLE_KN_M3 = 25.0


class StructureAnalyzer:
    """Descente de charges verticale, hors vent et seisme."""

    def analyze(self, project, usage: str = "habitation") -> Dict[str, object]:
        if usage not in CHARGES_KN_M2:
            raise ValueError("usage inconnu : %s" % sorted(CHARGES_KN_M2))
        surface = sum(r.area_m2 for r in project.rooms)
        exploitation = surface * CHARGES_KN_M2[usage]
        dalles = sum(
            abs(_area(s.outline)) / 1e6 * s.thickness / 1000.0
            for s in project.slabs
        ) * POIDS_PROPRE_DALLE_KN_M3
        murs = sum(
            w.net_area_m2 * w.thickness / 1000.0 * 18.0 for w in project.walls
        )
        total = exploitation + dalles + murs
        porteurs = [w for w in project.walls if w.exterior or w.thickness >= 200]
        lineaire = sum(w.length for w in porteurs) / 1000.0
        return {
            "usage": usage,
            "surface_m2": round(surface, 2),
            "charge_exploitation_kn": round(exploitation, 1),
            "poids_dalles_kn": round(dalles, 1),
            "poids_murs_kn": round(murs, 1),
            "charge_totale_kn": round(total, 1),
            "murs_porteurs": len(porteurs),
            "lineaire_porteur_m": round(lineaire, 2),
            "charge_lineique_kn_m": round(total / lineaire, 2) if lineaire else 0.0,
            "avertissement": "predimensionnement d'esquisse, hors vent et seisme, "
                             "non substituable a une note de calcul",
        }


def _area(outline: List) -> float:
    if len(outline) < 3:
        return 0.0
    total = 0.0
    for i, p in enumerate(outline):
        q = outline[(i + 1) % len(outline)]
        total += p[0] * q[1] - q[0] * p[1]
    return total / 2.0
