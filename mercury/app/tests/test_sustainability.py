"""Tests carbone, energie et certification."""
from __future__ import annotations

import pytest

from Sustainability.carbon import CarbonAnalyzer
from Sustainability.certification import CertificationScorer
from Sustainability.energy import EnergyOptions, EnergySimulator


def test_bilan_carbone(furnished):
    result = CarbonAnalyzer().analyze(furnished)
    assert result["total_kg_co2e"] > 0
    somme = sum(line["kg_co2e"] for line in result["lignes"])
    assert abs(somme - result["total_kg_co2e"]) < 1.0
    assert result["etiquette"] in list("ABCDE")
    assert result["leviers"]
    gains = [l["gain_kg_co2e"] for l in result["leviers"]]
    assert gains == sorted(gains, reverse=True), "leviers classes par gain"


def test_variante_bois_reduit_les_emissions(furnished):
    comparison = CarbonAnalyzer().compare(
        furnished, {"MUR.EXT.M3": 55.0, "STR.DALLE.M3": 130.0})
    assert comparison["gain_kg_co2e"] > 0
    assert comparison["gain_pourcent"] > 10


def test_isolation_ordonnee(furnished):
    simulator = EnergySimulator()
    values = [simulator.simulate(furnished, EnergyOptions(insulation=level))["kwh_m2_an"]
              for level in ("ancien", "renove", "neuf", "passif")]
    assert values == sorted(values, reverse=True), "isolation incoherente : %s" % values


def test_deperditions_somment_au_total(furnished):
    result = EnergySimulator().simulate(furnished)
    losses = result["deperditions_w_par_k"]
    total = losses.pop("total")
    assert abs(sum(losses.values()) - total) < 1.0


def test_climat_influence_les_besoins(furnished):
    simulator = EnergySimulator()
    froid = simulator.simulate(furnished, EnergyOptions(climate="montagnard"))
    chaud = simulator.simulate(furnished, EnergyOptions(climate="tropical"))
    assert froid["besoins_kwh_an"]["chauffage_net"] > \
        chaud["besoins_kwh_an"]["chauffage_net"] * 3


def test_parametres_invalides_refuses(furnished):
    with pytest.raises(ValueError):
        EnergySimulator().simulate(furnished, EnergyOptions(insulation="magique"))
    with pytest.raises(ValueError):
        EnergySimulator().simulate(furnished, EnergyOptions(climate="lunaire"))


def test_certification(furnished):
    energy = EnergySimulator().simulate(furnished)
    carbon = CarbonAnalyzer().analyze(furnished)
    score = CertificationScorer().score(energy, carbon,
                                        {"recuperation_eau": True})
    assert 0 <= score["note_sur_100"] <= 100
    assert score["niveau"]
    assert score["points_a_gagner"]
