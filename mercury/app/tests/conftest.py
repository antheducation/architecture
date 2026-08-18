"""Configuration partagee des tests.

Chaque session utilise une base temporaire : les tests ne laissent aucune
trace et peuvent tourner en parallele de l'application.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def db_path():
    directory = tempfile.mkdtemp(prefix="mercury_tests_")
    return os.path.join(directory, "test.db")


@pytest.fixture(scope="session")
def state(db_path):
    from API.deps import reset_state
    return reset_state(db_path)


@pytest.fixture()
def project():
    """Projet de reference : rectangle 10 x 8 m avec une cloison en T."""
    from BIM_Engine.models import BuildingProject, Opening, Wall
    project = BuildingProject(name="Reference", building_type="maison")
    walls = [
        ((0, 0), (10000, 0), 300, True),
        ((10000, 0), (10000, 8000), 300, True),
        ((10000, 8000), (0, 8000), 300, True),
        ((0, 8000), (0, 0), 300, True),
        ((5000, 0), (5000, 8000), 100, False),
        ((5000, 4000), (10000, 4000), 100, False),
    ]
    for start, end, thickness, exterior in walls:
        project.add_wall(Wall(start=start, end=end, thickness=thickness,
                              height=2700, exterior=exterior))
    project.walls[0].add_opening(Opening(type="fenetre", offset=2500,
                                         width=1600, height=1400, sill=900))
    project.walls[0].add_opening(Opening(type="fenetre", offset=7500,
                                         width=1600, height=1400, sill=900))
    project.walls[3].add_opening(Opening(type="porte", offset=4000,
                                         width=1000, height=2100))
    project.walls[4].add_opening(Opening(type="porte", offset=2000,
                                         width=900, height=2100))
    return project


@pytest.fixture()
def furnished(project, state):
    """Projet de reference avec ses pieces calculees."""
    from BIM_Engine.models import Room
    faces = state.engine_2d.detect_rooms(project.walls)
    project.rooms = []
    for index, face in enumerate(faces):
        metrics = state.engine_2d.room_metrics(face, 150.0)
        project.rooms.append(Room(name="Piece %d" % (index + 1), **metrics,
                                  height=2700, level_id=project.levels[0].id))
    return project
