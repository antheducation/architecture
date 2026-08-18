"""Passerelle IoT (livrable #43).

Ingestion par webhook, compatible avec un pont MQTT qui deverse ses lots.
Les capteurs sont rattaches aux pieces du modele BIM : une mesure n'est pas
un nombre isole, c'est la mesure d'un espace dont on connait la surface.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

QUANTITIES: Dict[str, tuple] = {
    "temperature": (19.0, 26.0, "C"),
    "humidite": (30.0, 60.0, "%"),
    "co2": (0.0, 1000.0, "ppm"),
    "cov": (0.0, 300.0, "ug/m3"),
    "luminosite": (200.0, 5000.0, "lux"),
    "presence": (0.0, 1.0, "bool"),
    "consommation": (0.0, 1e9, "kWh"),
}
RETENTION = 500


@dataclass
class Sensor:
    id: str
    quantity: str
    project_id: str
    room_id: Optional[str] = None
    name: str = ""
    unit: str = ""
    readings: List[tuple] = field(default_factory=list)
    last_seen: float = 0.0

    def push(self, value: float, timestamp: Optional[float] = None) -> None:
        stamp = timestamp or time.time()
        self.readings.append((stamp, value))
        if len(self.readings) > RETENTION:
            del self.readings[: len(self.readings) - RETENTION]
        self.last_seen = stamp

    @property
    def value(self) -> Optional[float]:
        return self.readings[-1][1] if self.readings else None

    def stats(self) -> Dict[str, float]:
        values = [v for _, v in self.readings]
        if not values:
            return {}
        return {"n": len(values), "min": min(values), "max": max(values),
                "moyenne": round(statistics.fmean(values), 2),
                "dernier": values[-1]}

    def as_dict(self) -> Dict[str, object]:
        return {"id": self.id, "nom": self.name, "grandeur": self.quantity,
                "unite": self.unit, "piece": self.room_id, "valeur": self.value,
                "derniere_vue": self.last_seen, "statistiques": self.stats()}


class SensorRegistry:
    """Annuaire des capteurs declares."""

    def __init__(self) -> None:
        self._sensors: Dict[str, Sensor] = {}

    def declare(self, sensor_id: str, quantity: str, project_id: str,
                room_id: Optional[str] = None, name: str = "") -> Sensor:
        if quantity not in QUANTITIES:
            raise ValueError("grandeur inconnue : %s" % sorted(QUANTITIES))
        if len(sensor_id) < 2:
            raise ValueError("identifiant de capteur trop court")
        sensor = Sensor(sensor_id, quantity, project_id, room_id,
                        name or sensor_id, QUANTITIES[quantity][2])
        self._sensors[sensor_id] = sensor
        return sensor

    def get(self, sensor_id: str) -> Optional[Sensor]:
        return self._sensors.get(sensor_id)

    def remove(self, sensor_id: str) -> bool:
        return self._sensors.pop(sensor_id, None) is not None

    def for_project(self, project_id: str) -> List[Sensor]:
        return [s for s in self._sensors.values() if s.project_id == project_id]

    def all(self) -> List[Sensor]:
        return list(self._sensors.values())


class IoTGateway:
    """Reception des mesures : une par une ou par lots."""

    def __init__(self, registry: Optional[SensorRegistry] = None) -> None:
        self.registry = registry or SensorRegistry()

    def ingest(self, batch: List[Dict[str, object]]) -> Dict[str, object]:
        accepted, unknown = 0, []
        for entry in batch:
            sensor = self.registry.get(str(entry.get("capteur", "")))
            if sensor is None:
                unknown.append(str(entry.get("capteur", "")))
                continue
            sensor.push(float(entry["valeur"]), entry.get("horodatage"))
            accepted += 1
        return {"acceptees": accepted, "capteurs_inconnus": sorted(set(unknown))}
