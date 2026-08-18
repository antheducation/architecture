"""Simulation energetique (livrables #45, #47, #54, #56).

Methode statique mensuelle par degres-jours : deperditions de l'enveloppe
et du renouvellement d'air, moins les apports solaires par orientation et
les apports internes. C'est la methode des bureaux d'etudes en phase
esquisse : assez juste pour arbitrer une orientation ou une epaisseur
d'isolant, assez rapide pour tourner a chaque modification.

Ce n'est pas une simulation dynamique horaire : inerties, scenarios
d'occupation et masques solaires ne sont pas traites. La sortie le declare.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

INSULATION = {
    "ancien": {"mur": 2.00, "toiture": 1.60, "plancher": 1.50, "vitrage": 4.50,
               "porte": 3.50, "ponts": 0.55, "air": 0.90},
    "renove": {"mur": 0.45, "toiture": 0.28, "plancher": 0.40, "vitrage": 1.80,
               "porte": 1.80, "ponts": 0.25, "air": 0.60},
    "neuf": {"mur": 0.22, "toiture": 0.15, "plancher": 0.20, "vitrage": 1.30,
             "porte": 1.40, "ponts": 0.12, "air": 0.45},
    "passif": {"mur": 0.13, "toiture": 0.10, "plancher": 0.13, "vitrage": 0.80,
               "porte": 0.80, "ponts": 0.05, "air": 0.25},
}

CLIMATES = {
    "mediterraneen": {"dju": 1300, "djr": 420, "irradiation": 62, "mois": 4.5},
    "oceanique": {"dju": 2200, "djr": 90, "irradiation": 38, "mois": 6.5},
    "continental": {"dju": 2900, "djr": 160, "irradiation": 34, "mois": 7.0},
    "montagnard": {"dju": 3800, "djr": 40, "irradiation": 40, "mois": 8.0},
    "tropical": {"dju": 120, "djr": 900, "irradiation": 70, "mois": 0.8},
    "desertique": {"dju": 800, "djr": 1100, "irradiation": 80, "mois": 2.5},
}

ORIENTATION_FACTOR = {"sud": 1.0, "est": 0.55, "ouest": 0.58, "nord": 0.22}
LABELS = [(50, "A"), (90, "B"), (150, "C"), (230, "D"), (330, "E"),
          (450, "F"), (float("inf"), "G")]


@dataclass
class EnergyOptions:
    insulation: str = "neuf"
    climate: str = "oceanique"
    internal_gains_w_m2: float = 4.5
    glazing_factor: float = 0.55
    heating_efficiency: float = 0.92
    cooling_cop: float = 3.2
    price_kwh: float = 0.21


class EnergySimulator:
    """Besoins de chauffage et de froid, etiquette et actions prioritaires."""

    def simulate(self, project, options: Optional[EnergyOptions] = None
                 ) -> Dict[str, object]:
        options = options or EnergyOptions()
        if options.insulation not in INSULATION:
            raise ValueError("niveau d'isolation inconnu : %s" % sorted(INSULATION))
        if options.climate not in CLIMATES:
            raise ValueError("climat inconnu : %s" % sorted(CLIMATES))
        u = INSULATION[options.insulation]
        climate = CLIMATES[options.climate]

        surface = max(1.0, sum(r.area_m2 for r in project.rooms))
        height = project.levels[0].height / 1000.0
        volume = surface * height

        facades = {"sud": 0.0, "nord": 0.0, "est": 0.0, "ouest": 0.0}
        glazing = {"sud": 0.0, "nord": 0.0, "est": 0.0, "ouest": 0.0}
        doors = 0.0
        for wall in project.walls:
            if not wall.exterior:
                continue
            key = self._orientation(wall)
            facades[key] += wall.gross_area_m2
            for opening in wall.openings:
                if opening.type == "porte":
                    doors += opening.area_m2
                else:
                    glazing[key] += opening.area_m2

        glazed = sum(glazing.values())
        opaque = max(0.0, sum(facades.values()) - glazed - doors)
        losses = {
            "murs": opaque * u["mur"],
            "toiture": surface * u["toiture"],
            "plancher": surface * u["plancher"],
            "vitrages": glazed * u["vitrage"],
            "portes": doors * u["porte"],
            "ponts_thermiques": (opaque + surface) * u["ponts"] * 0.25,
            "renouvellement_air": volume * u["air"] * 0.34,
        }
        total_loss = sum(losses.values())

        gross_need = total_loss * climate["dju"] * 24 / 1000.0
        solar = sum(glazing[k] * ORIENTATION_FACTOR[k] for k in glazing) \
            * climate["irradiation"] * climate["mois"] * options.glazing_factor
        internal = options.internal_gains_w_m2 * surface * climate["mois"] * 30 * 24 / 1000.0
        gains = solar + internal
        utilisation = min(0.95, 0.85 * (1 - math.exp(-gross_need / max(gains, 1.0))))
        net_need = max(0.0, gross_need - gains * utilisation)
        cooling = max(0.0, total_loss * climate["djr"] * 24 / 1000.0 * 0.35
                      + solar * 0.12)

        heating_consumption = net_need / options.heating_efficiency
        cooling_consumption = cooling / options.cooling_cop
        total = heating_consumption + cooling_consumption
        per_m2 = total / surface
        label = next(l for threshold, l in LABELS if per_m2 <= threshold)

        return {
            "methode": "statique mensuelle (degres-jours), phase esquisse, "
                       "non reglementaire",
            "hypotheses": {"isolation": options.insulation,
                           "climat": options.climate, "dju": climate["dju"]},
            "geometrie": {
                "surface_m2": round(surface, 1), "volume_m3": round(volume, 1),
                "facades_m2": {k: round(v, 1) for k, v in facades.items()},
                "vitrage_m2": {k: round(v, 1) for k, v in glazing.items()},
                "taux_vitrage_pourcent": round(
                    glazed / max(sum(facades.values()), 1.0) * 100, 1),
            },
            "deperditions_w_par_k": {**{k: round(v, 1) for k, v in losses.items()},
                                     "total": round(total_loss, 1)},
            "repartition_pourcent": {
                k: round(v / max(total_loss, 1e-6) * 100, 1)
                for k, v in losses.items()},
            "apports_kwh_an": {"solaires": round(solar),
                               "internes": round(internal),
                               "taux_utilisation": round(utilisation, 2)},
            "besoins_kwh_an": {"chauffage_brut": round(gross_need),
                               "chauffage_net": round(net_need),
                               "refroidissement": round(cooling)},
            "consommation_kwh_an": {"chauffage": round(heating_consumption),
                                    "refroidissement": round(cooling_consumption),
                                    "total": round(total)},
            "kwh_m2_an": round(per_m2, 1),
            "etiquette": label,
            "cout_annuel_estime": round(total * options.price_kwh),
            "recommandations": self._advice(losses, total_loss, glazing, options),
        }

    @staticmethod
    def _orientation(wall) -> str:
        dx = wall.end[0] - wall.start[0]
        dy = wall.end[1] - wall.start[1]
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length
        angle = math.degrees(math.atan2(ny, nx)) % 360.0
        if 45 <= angle < 135:
            return "nord"
        if 135 <= angle < 225:
            return "ouest"
        if 225 <= angle < 315:
            return "sud"
        return "est"

    @staticmethod
    def _advice(losses: Dict[str, float], total: float,
                glazing: Dict[str, float],
                options: EnergyOptions) -> List[Dict[str, object]]:
        advice: List[Dict[str, object]] = []
        if options.insulation != "passif":
            nxt = {"ancien": "renove", "renove": "neuf", "neuf": "passif"}[
                options.insulation]
            ratio = INSULATION[nxt]["mur"] / INSULATION[options.insulation]["mur"]
            gain = losses["murs"] * (1 - ratio) / max(total, 1e-6) * 100
            advice.append({"action": "passer l'isolation au niveau %s" % nxt,
                           "gain_deperditions_pourcent": round(gain, 1),
                           "cout": "moyen a eleve",
                           "priorite": 1 if gain > 12 else 3})
        if glazing["nord"] > glazing["sud"] * 1.15:
            advice.append({
                "action": "redistribuer les vitrages du nord vers le sud",
                "gain_deperditions_pourcent": round(
                    (glazing["nord"] - glazing["sud"])
                    / max(sum(glazing.values()), 1.0) * 12, 1),
                "cout": "nul en phase esquisse", "priorite": 1})
        if losses["renouvellement_air"] / max(total, 1e-6) > 0.20:
            advice.append({
                "action": "ventilation double flux avec recuperation",
                "gain_deperditions_pourcent": round(
                    losses["renouvellement_air"] / total * 65, 1),
                "cout": "moyen", "priorite": 2})
        advice.sort(key=lambda a: (a["priorite"],
                                   -float(a["gain_deperditions_pourcent"])))
        return advice

    def compare_orientations(self, project,
                             options: Optional[EnergyOptions] = None
                             ) -> Dict[str, object]:
        """Effet d'une rotation du batiment : l'arbitrage le moins cher."""
        import copy
        options = options or EnergyOptions()
        results = {"0": self.simulate(project, options)["kwh_m2_an"]}
        for angle in (90, 180, 270):
            rotated = copy.deepcopy(project)
            radians = math.radians(angle)
            c, s = math.cos(radians), math.sin(radians)
            for wall in rotated.walls:
                wall.start = (wall.start[0] * c - wall.start[1] * s,
                              wall.start[0] * s + wall.start[1] * c)
                wall.end = (wall.end[0] * c - wall.end[1] * s,
                            wall.end[0] * s + wall.end[1] * c)
            results[str(angle)] = self.simulate(rotated, options)["kwh_m2_an"]
        best = min(results, key=lambda k: results[k])
        return {"par_rotation_kwh_m2_an": results,
                "meilleure_rotation_deg": int(best),
                "gain_kwh_m2_an": round(results["0"] - results[best], 1)}
