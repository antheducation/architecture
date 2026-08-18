"""Tests de la conception generative (livrable #03)."""
from __future__ import annotations

import pytest

from AI_Engine.generative_design import (
    GenerativeDesigner, build_program, slice_rects,
)


def test_programme_cale_sur_la_surface():
    for surface in (75.0, 110.0, 150.0):
        program = build_program("maison", surface, bedrooms=3)
        assert abs(program.target_area - surface) / surface < 0.06
        assert not program.saturation


def test_programme_signale_la_saturation():
    """210 m2 pour 3 chambres : les pieces butent sur leur taille d'usage."""
    program = build_program("maison", 210.0, bedrooms=3)
    assert program.saturation, "la saturation doit etre signalee"
    assert program.target_area < 210.0
    large = build_program("maison", 210.0, bedrooms=5, bathrooms=2)
    assert abs(large.target_area - 210.0) / 210.0 < 0.10


def test_decoupe_couvre_toute_l_emprise():
    rects = slice_rects(12000, 9000, [0, 1, 0], [0.4, 0.6, 0.5], [0, 0, 1])
    assert len(rects) == 4
    aire = sum(w * h for _, _, w, h in rects)
    assert abs(aire - 12000 * 9000) < 1.0, "la decoupe ne doit rien perdre"


def test_plan_genere_est_un_batiment_complet():
    program = build_program("maison", 110, bedrooms=3)
    projects = GenerativeDesigner().generate(program, variants=2,
                                             iterations=1200, seed=3)
    assert len(projects) == 2
    project = projects[0]
    assert len(project.rooms) == len(program.rooms)
    assert len(project.walls) >= 6
    assert any(w.exterior for w in project.walls)
    assert any(not w.exterior for w in project.walls)
    openings = [o for w in project.walls for o in w.openings]
    assert len(openings) >= 5
    assert any(o.type == "porte" for o in openings)
    assert any(o.type == "fenetre" for o in openings)
    for wall in project.walls:
        for opening in wall.openings:
            assert 0 <= opening.offset <= wall.length


def test_variantes_classees_et_deterministes():
    program = build_program("maison", 120, bedrooms=3)
    first = GenerativeDesigner().search(program, variants=3, iterations=600, seed=42)
    program2 = build_program("maison", 120, bedrooms=3)
    second = GenerativeDesigner().search(program2, variants=3, iterations=600, seed=42)
    assert [round(c.cost, 6) for c in first] == [round(c.cost, 6) for c in second]
    assert first[0].cost <= first[-1].cost


def test_conformite_au_programme():
    program = build_program("restaurant", 240, covers=70)
    project = GenerativeDesigner().generate(program, variants=3,
                                            iterations=1800, seed=11)[0]
    targets = {spec.name: spec.target_m2 for spec in program.rooms}
    gaps = [abs(r.area_m2 - targets[r.name]) / targets[r.name]
            for r in project.rooms if r.name in targets]
    assert sum(gaps) / len(gaps) < 0.40
