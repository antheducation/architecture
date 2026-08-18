"""Tests du modele BIM : validation, quantites, serialisation."""
from __future__ import annotations

import pytest

from BIM_Engine.models import BuildingProject, Opening, Room, Wall


def test_mur_calcule_ses_quantites():
    wall = Wall(start=(0, 0), end=(5000, 0), thickness=200, height=2700)
    assert abs(wall.length - 5000) < 1e-9
    assert abs(wall.gross_area_m2 - 13.5) < 1e-6
    wall.add_opening(Opening(type="porte", offset=2500, width=900, height=2100))
    assert wall.net_area_m2 < wall.gross_area_m2
    assert abs(wall.gross_area_m2 - wall.net_area_m2 - 1.89) < 1e-6


def test_validations_refusent_les_valeurs_absurdes():
    with pytest.raises(ValueError):
        Wall(start=(0, 0), end=(1000, 0), thickness=0)
    with pytest.raises(ValueError):
        Wall(start=(0, 0), end=(1000, 0), height=-1)
    with pytest.raises(ValueError):
        Opening(type="trappe")
    with pytest.raises(ValueError):
        BuildingProject(building_type="chateau_fort")


def test_baie_hors_du_mur_est_refusee():
    wall = Wall(start=(0, 0), end=(2000, 0))
    with pytest.raises(ValueError) as error:
        wall.add_opening(Opening(offset=1900, width=900))
    assert "deborde" in str(error.value)


def test_serialisation_sans_perte():
    project = BuildingProject(name="Test", building_type="villa")
    wall = project.add_wall(Wall(start=(0, 0), end=(4000, 0), exterior=True))
    wall.add_opening(Opening(type="fenetre", offset=2000, width=1200,
                             height=1400, sill=900))
    project.rooms.append(Room(name="Sejour", area_m2=25.4,
                              outline=[(0, 0), (5000, 0), (5000, 5000)]))
    restored = BuildingProject.from_dict(project.to_dict())
    assert restored.name == project.name
    assert restored.building_type == project.building_type
    assert len(restored.walls) == 1
    assert len(restored.walls[0].openings) == 1
    assert restored.walls[0].openings[0].type == "fenetre"
    assert restored.rooms[0].area_m2 == 25.4


def test_versionnage():
    project = BuildingProject()
    assert project.version == 1
    project.bump().bump()
    assert project.version == 3
