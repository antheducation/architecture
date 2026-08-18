"""Documentation automatique (livrables #19 et #35).

Les nomenclatures et rapports sont derives du modele : ils ne peuvent pas
diverger de la geometrie, puisqu'ils en sont extraits a chaque appel.
"""
from __future__ import annotations

from typing import Dict, List


class DocumentGenerator:
    """Produit nomenclatures et rapports de projet."""

    @staticmethod
    def room_schedule(project) -> List[Dict[str, object]]:
        return [
            {
                "id": room.id,
                "nom": room.name,
                "type": room.kind,
                "surface_m2": room.area_m2,
                "perimetre_m": room.perimeter_m,
                "volume_m3": round(room.area_m2 * room.height / 1000.0, 2),
            }
            for room in sorted(project.rooms, key=lambda r: -r.area_m2)
        ]

    @staticmethod
    def project_report(project) -> Dict[str, object]:
        openings = [o for w in project.walls for o in w.openings]
        return {
            "projet": project.name,
            "type_batiment": project.building_type,
            "version": project.version,
            "surface_utile_m2": round(sum(r.area_m2 for r in project.rooms), 2),
            "nb_pieces": len(project.rooms),
            "nb_murs": len(project.walls),
            "lineaire_murs_m": round(sum(w.length for w in project.walls) / 1000.0, 2),
            "nb_portes": sum(1 for o in openings if o.type == "porte"),
            "nb_fenetres": sum(1 for o in openings if o.type != "porte"),
            "nb_objets": len(project.furniture),
        }
