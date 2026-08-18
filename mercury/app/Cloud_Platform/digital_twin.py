"""Jumeau numerique (livrables #41 et #42).

Confronte les mesures au modele BIM. Le lien avec la geometrie distingue
ce module d'une base de mesures : une derive dans un grand volume occupe
est plus grave que la meme derive dans un local technique.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from .iot import QUANTITIES, IoTGateway, SensorRegistry


class DigitalTwin:
    """Etat courant du batiment, alertes ponderees par le modele."""

    def __init__(self, registry: Optional[SensorRegistry] = None) -> None:
        self.registry = registry or SensorRegistry()

    def state(self, project, silence_seconds: float = 900.0) -> Dict[str, object]:
        sensors = self.registry.for_project(project.id)
        now = time.time()
        rooms: List[Dict[str, object]] = []
        alerts: List[Dict[str, object]] = []

        for room in project.rooms:
            linked = [s for s in sensors if s.room_id == room.id]
            measures: Dict[str, object] = {}
            for sensor in linked:
                if sensor.value is None:
                    continue
                measures[sensor.quantity] = {"valeur": sensor.value,
                                             "unite": sensor.unit}
                low, high, unit = QUANTITIES[sensor.quantity]
                if now - sensor.last_seen > silence_seconds:
                    alerts.append({
                        "gravite": "moyenne", "type": "capteur muet",
                        "piece": room.name, "capteur": sensor.id,
                        "detail": "aucune mesure depuis %d min"
                                  % int((now - sensor.last_seen) / 60)})
                elif sensor.value < low or sensor.value > high:
                    alerts.append({
                        "gravite": "haute" if room.area_m2 > 20 else "moyenne",
                        "type": "hors consigne", "piece": room.name,
                        "capteur": sensor.id, "grandeur": sensor.quantity,
                        "valeur": sensor.value,
                        "attendu": "%s-%s %s" % (low, high, unit),
                        "detail": "%s a %s %s dans %s (%.2f m2)"
                                  % (sensor.quantity, sensor.value, unit,
                                     room.name, room.area_m2)})
            rooms.append({"id": room.id, "nom": room.name,
                          "surface_m2": room.area_m2,
                          "capteurs": len(linked), "mesures": measures})

        covered = sum(1 for r in rooms if r["capteurs"]) / max(1, len(rooms))
        return {
            "projet": project.id, "nom": project.name, "horodatage": now,
            "couverture_pieces": round(covered, 2),
            "capteurs_total": len(sensors),
            "pieces": rooms,
            "alertes": sorted(alerts,
                              key=lambda a: 0 if a["gravite"] == "haute" else 1),
            "note": "les consignes sont ponderees par la geometrie du modele BIM",
        }

    def energy_gap(self, project, simulated_kwh: float) -> Dict[str, object]:
        """Compare la consommation mesuree a la consommation simulee."""
        meters = [s for s in self.registry.for_project(project.id)
                  if s.quantity == "consommation"]
        measured = sum(s.value or 0.0 for s in meters)
        gap = ((measured - simulated_kwh) / simulated_kwh * 100
               if simulated_kwh else 0.0)
        return {
            "consommation_mesuree_kwh": round(measured, 1),
            "consommation_simulee_kwh_an": round(simulated_kwh, 1),
            "ecart_pourcent": round(gap, 1),
            "compteurs": len(meters),
            "lecture": "un ecart positif important signale une enveloppe moins "
                       "performante que prevue ou une occupation superieure "
                       "aux hypotheses",
        }
