"""Tests du metre, du chiffrage et du planning."""
from __future__ import annotations

import pytest

from Construction.planning import ConstructionPlanner
from Estimating.cost_ai import CostEstimator
from Estimating.takeoff import QuantityTakeoff


def test_metre_porte_ses_formules(furnished):
    lines = QuantityTakeoff().compute(furnished)
    assert lines, "le metre ne doit pas etre vide"
    codes = {line.code for line in lines}
    assert "MUR.EXT.ML" in codes and "FIN.SOL.M2" in codes
    assert all(line.formula for line in lines), "chaque ligne porte sa formule"
    assert all(line.quantity >= 0 for line in lines)


def test_devis_coherent(furnished):
    estimate = CostEstimator().estimate(furnished)
    assert estimate["sous_total"] > 0
    assert estimate["total_ht"] > estimate["sous_total"]
    assert estimate["total_ttc"] > estimate["total_ht"]
    assert abs(sum(estimate["par_lot"].values()) - estimate["sous_total"]) < 1.0
    assert estimate["ratio_eur_m2"] > 0


def test_taux_invalides_refuses(furnished):
    """Les taux et coefficients absurdes doivent etre refuses a la source."""
    with pytest.raises(ValueError):
        CostEstimator(contingency=1.5)
    with pytest.raises(ValueError):
        CostEstimator(overhead=-0.1)
    with pytest.raises(ValueError):
        CostEstimator(tax=1.0)
    with pytest.raises(ValueError):
        CostEstimator().estimate(furnished, region_factor=0)
    with pytest.raises(ValueError):
        CostEstimator().schedule({"lignes": []}, crews=0)


def test_planning_et_chemin_critique(furnished):
    estimator = CostEstimator()
    estimate = estimator.estimate(furnished)
    schedule = estimator.schedule(estimate)
    assert schedule, "le planning ne doit pas etre vide"
    plan = ConstructionPlanner().plan(schedule)
    assert plan["duree_totale_jours"] > 0
    assert plan["chemin_critique"]
    for task in plan["taches"]:
        assert task["fin_jour"] > task["debut_jour"]


def test_optimisation_budget(furnished):
    estimator = CostEstimator()
    base = estimator.estimate(furnished)["total_ht"]
    result = estimator.optimize(furnished, target=base * 0.7)
    assert result["actions"], "des leviers doivent etre proposes"
    assert result["cible"] < result["total_ht"]
