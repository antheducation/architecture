"""Empreinte carbone (livrables #50, #51, #52, #53, #61).

Analyse de cycle de vie A1-A3 calculee sur le metre : chaque quantite est
multipliee par son facteur d'emission, donc rien ne peut diverger du
modele. Les facteurs sont indicatifs et remplacables par la base d'un
bureau d'etudes.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from Estimating.takeoff import QuantityTakeoff

FACTORS: Dict[str, Tuple[float, str, str]] = {
    "MUR.EXT.M3": (280.0, "m3", "Gros oeuvre"),
    "MUR.INT.M3": (190.0, "m3", "Cloisons"),
    "STR.DALLE.M3": (310.0, "m3", "Structure"),
    "MEN.PORTE": (55.0, "u", "Menuiseries"),
    "MEN.FEN.M2": (95.0, "m2", "Menuiseries"),
    "FIN.SOL.M2": (18.0, "m2", "Revetements"),
    "FIN.MUR.M2": (4.5, "m2", "Peinture"),
    "FIN.PLAF.M2": (9.0, "m2", "Plafonds"),
}

ALTERNATIVES: Dict[str, List[Tuple[str, float, float]]] = {
    "MUR.EXT.M3": [("beton bas carbone (CEM III)", 190.0, 6.0),
                   ("brique terre cuite", 145.0, 9.0),
                   ("ossature bois + isolant biosource", 55.0, 14.0)],
    "STR.DALLE.M3": [("beton bas carbone", 215.0, 7.0),
                     ("plancher bois-beton", 130.0, 18.0)],
    "MUR.INT.M3": [("carreaux de platre", 120.0, 3.0),
                   ("ossature bois", 60.0, 8.0)],
}

LABELS = [(500.0, "A", "exemplaire"), (750.0, "B", "performant"),
          (950.0, "C", "courant"), (1200.0, "D", "ameliorable"),
          (float("inf"), "E", "fortement emetteur")]


class CarbonAnalyzer:
    """Calcule l'empreinte et classe les leviers par gain reel."""

    def __init__(self, factors: Optional[Dict[str, Tuple[float, str, str]]] = None,
                 name: str = "indicative") -> None:
        self.factors = dict(factors or FACTORS)
        self.name = name

    def analyze(self, project) -> Dict[str, object]:
        quantities = QuantityTakeoff().compute(project)
        surface = max(1.0, sum(r.area_m2 for r in project.rooms))
        lines: List[Dict[str, object]] = []
        total = 0.0
        by_lot: Dict[str, float] = {}
        for line in quantities:
            entry = self.factors.get(line.code)
            if entry is None:
                continue
            factor, unit, lot = entry
            emission = line.quantity * factor
            total += emission
            by_lot[lot] = round(by_lot.get(lot, 0.0) + emission, 1)
            lines.append({"code": line.code, "designation": line.label,
                          "lot": lot, "quantite": round(line.quantity, 2),
                          "unite": unit, "facteur_kgco2e": factor,
                          "kg_co2e": round(emission, 1)})
        per_m2 = total / surface
        label, mention = next((l, m) for threshold, l, m in LABELS
                              if per_m2 <= threshold)
        return {
            "perimetre": "A1-A3 (production des materiaux)",
            "base_facteurs": self.name,
            "surface_m2": round(surface, 2),
            "total_kg_co2e": round(total, 1),
            "total_t_co2e": round(total / 1000.0, 2),
            "kg_co2e_par_m2": round(per_m2, 1),
            "etiquette": label,
            "mention": mention,
            "par_lot": dict(sorted(by_lot.items(), key=lambda kv: -kv[1])),
            "lignes": lines,
            "leviers": self.levers(lines),
            "equivalences": {
                "km_voiture": round(total / 0.193),
                "arbres_an": round(total / 25.0),
            },
        }

    @staticmethod
    def levers(lines: List[Dict[str, object]]) -> List[Dict[str, object]]:
        result: List[Dict[str, object]] = []
        for line in lines:
            for name, factor, extra_cost in ALTERNATIVES.get(str(line["code"]), []):
                current = float(line["facteur_kgco2e"])
                if factor >= current:
                    continue
                gain = float(line["quantite"]) * (current - factor)
                result.append({
                    "poste": line["designation"], "code": line["code"],
                    "solution": name, "gain_kg_co2e": round(gain, 1),
                    "gain_pourcent_poste": round((current - factor) / current * 100, 1),
                    "surcout_estime_pourcent": extra_cost,
                })
        return sorted(result, key=lambda d: -float(d["gain_kg_co2e"]))[:8]

    def compare(self, project, substitutions: Dict[str, float]) -> Dict[str, object]:
        reference = self.analyze(project)
        variant_factors = dict(self.factors)
        for code, factor in substitutions.items():
            if code in variant_factors:
                old = variant_factors[code]
                variant_factors[code] = (factor, old[1], old[2])
        variant = CarbonAnalyzer(variant_factors, "variante").analyze(project)
        gain = float(reference["total_kg_co2e"]) - float(variant["total_kg_co2e"])
        return {
            "reference_kg_co2e": reference["total_kg_co2e"],
            "variante_kg_co2e": variant["total_kg_co2e"],
            "gain_kg_co2e": round(gain, 1),
            "gain_pourcent": round(
                gain / max(float(reference["total_kg_co2e"]), 1.0) * 100, 1),
        }
