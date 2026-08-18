"""Territoire (livrables #57, #58, #59, #62).

Agrege plusieurs batiments a l'echelle d'un quartier ou d'un village :
surfaces, consommations, emissions, densite. Les donnees topographiques et
les releves par drone sont attendus au format GeoJSON.
"""
from __future__ import annotations

from typing import Dict, List, Optional


class CityPlatform:
    """Consolidation territoriale d'un portefeuille de projets."""

    def aggregate(self, projects: List[object],
                  energy_by_project: Optional[Dict[str, float]] = None,
                  carbon_by_project: Optional[Dict[str, float]] = None,
                  plot_area_m2: float = 0.0) -> Dict[str, object]:
        energy_by_project = energy_by_project or {}
        carbon_by_project = carbon_by_project or {}
        surface = sum(sum(r.area_m2 for r in p.rooms) for p in projects)
        energy = sum(energy_by_project.get(p.id, 0.0) for p in projects)
        carbon = sum(carbon_by_project.get(p.id, 0.0) for p in projects)
        by_type: Dict[str, int] = {}
        for project in projects:
            by_type[project.building_type] = by_type.get(project.building_type, 0) + 1
        density = (surface / plot_area_m2) if plot_area_m2 > 0 else 0.0
        return {
            "batiments": len(projects),
            "surface_totale_m2": round(surface, 2),
            "par_typologie": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
            "energie_totale_kwh_an": round(energy, 1),
            "carbone_total_t_co2e": round(carbon / 1000.0, 2),
            "coefficient_emprise": round(density, 3),
            "energie_moyenne_kwh_m2": round(energy / surface, 1) if surface else 0.0,
        }

    @staticmethod
    def to_geojson(projects: List[object]) -> Dict[str, object]:
        """Exporte les emprises au format GeoJSON pour un SIG."""
        features = []
        for project in projects:
            points = [w.start for w in project.walls if w.exterior]
            if len(points) < 3:
                continue
            ring = [[float(p[0]), float(p[1])] for p in points]
            ring.append(ring[0])
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {"id": project.id, "nom": project.name,
                               "type": project.building_type,
                               "surface_m2": sum(r.area_m2 for r in project.rooms)},
            })
        return {"type": "FeatureCollection", "features": features}
