"""Tests des moteurs 2D et 3D : detection des pieces et extrusion."""
from __future__ import annotations

import pytest

from CAD_Core.engine_3d import Engine3D
from CAD_Core.geometry import polygon_area


def test_detection_des_pieces(state, project):
    """Un rectangle coupe en T doit donner trois pieces."""
    faces = state.engine_2d.detect_rooms(project.walls)
    assert len(faces) == 3, "attendu 3 pieces, obtenu %d" % len(faces)
    total = sum(abs(polygon_area(f)) for f in faces) / 1e6
    assert 75 < total < 82, "surface totale incoherente : %.1f m2" % total


def test_metrics_de_piece(state, project):
    faces = state.engine_2d.detect_rooms(project.walls)
    metrics = state.engine_2d.room_metrics(faces[0], 150.0)
    assert metrics["area_m2"] > 0
    assert metrics["perimeter_m"] > 0
    assert len(metrics["outline"]) >= 3


def test_extrusion_perce_les_baies(furnished):
    mesh = Engine3D().build(furnished)
    stats = mesh.stats
    assert stats["vertices"] > 100
    assert stats["faces"] > 60
    assert stats["groups"] >= len(furnished.walls)
    # un mur perce produit plus de faces qu'un mur plein
    groups = [g for g in mesh.groups if g.name.startswith("mur_")]
    assert groups, "aucun groupe de mur dans le maillage"
    assert all(g.count > 0 for g in groups)


def test_maillage_indices_valides(furnished):
    mesh = Engine3D().build(furnished)
    count = len(mesh.vertices)
    for face in mesh.faces:
        assert all(0 <= index < count for index in face), "indice hors bornes"
