"""Tests des modules metiers restes dans l'ombre.

Ces modules etaient importes mais jamais executes : c'est exactement la ou
les erreurs survivent. Chaque test verifie un comportement observable, pas
seulement l'absence d'exception.
"""
from __future__ import annotations

import pytest

from BIM_Engine.mep import MEPPlanner
from BIM_Engine.object_library import CatalogItem, ObjectLibrary
from BIM_Engine.structure import StructureAnalyzer
from Cloud_Platform.city import CityPlatform
from Construction.progress import ProgressTracker
from Construction.resources import ResourceManager
from Construction.safety import SafetyAnalyzer


# ----------------------------- bibliotheque -----------------------------
def test_bibliotheque_recherche_et_categories():
    library = ObjectLibrary()
    assert library.all()
    assert "cuisine" in library.categories()
    assert library.get("bed_double").name == "Lit double"
    assert library.get("inexistant") is None
    assert all(i.category == "chambre" for i in library.search(category="chambre"))
    assert library.search("lit")
    assert len(library.search(limit=3)) == 3


def test_objet_redimensionne_conserve_ses_attributs():
    item = ObjectLibrary().get("kitchen_run")
    grand = item.scaled(width=4200)
    assert grand.size[0] == 4200
    assert grand.size[1] == item.size[1]
    assert grand.unit_cost == item.unit_cost
    assert grand.anchor == item.anchor


def test_pack_fabricant(tmp_path):
    import json
    pack = tmp_path / "pack.json"
    pack.write_text(json.dumps({
        "manufacturer": "ACME",
        "items": [{"id": "acme_ilot", "name": "Ilot ACME", "category": "cuisine",
                   "size": [2400, 900, 900], "unit_cost": 2600}],
    }), encoding="utf-8")
    library = ObjectLibrary()
    assert library.load_pack(str(pack)) == 1
    ajoute = library.get("acme_ilot")
    assert ajoute.manufacturer == "ACME" and ajoute.unit_cost == 2600
    with pytest.raises(FileNotFoundError):
        library.load_pack(str(tmp_path / "absent.json"))
    invalide = tmp_path / "invalide.json"
    invalide.write_text('{"manufacturer": "X"}', encoding="utf-8")
    with pytest.raises(ValueError):
        library.load_pack(str(invalide))


# ------------------------------ structure ------------------------------
def test_descente_de_charges(furnished):
    # sans dalle, le poids propre du plancher resterait a zero et
    # l'assertion de somme serait vide de sens
    from BIM_Engine.models import Slab
    for room in furnished.rooms:
        furnished.slabs.append(Slab(outline=room.outline, thickness=200.0))
    result = StructureAnalyzer().analyze(furnished, "habitation")
    assert result["poids_dalles_kn"] > 0, "le poids des dalles doit etre compte"
    assert result["charge_totale_kn"] > 0
    somme = (result["charge_exploitation_kn"] + result["poids_dalles_kn"]
             + result["poids_murs_kn"])
    assert abs(somme - result["charge_totale_kn"]) < 1.0
    assert result["murs_porteurs"] >= 1
    assert result["charge_lineique_kn_m"] > 0
    assert "predimensionnement" in result["avertissement"]
    commerce = StructureAnalyzer().analyze(furnished, "commerce")
    assert commerce["charge_exploitation_kn"] > result["charge_exploitation_kn"]
    with pytest.raises(ValueError):
        StructureAnalyzer().analyze(furnished, "piscine_olympique")


# -------------------------------- fluides --------------------------------
def test_preciblage_des_reseaux(furnished):
    result = MEPPlanner().plan(furnished)
    assert result["detail"]
    totaux = result["totaux"]
    assert totaux["prises"] > 0 and totaux["luminaires"] > 0
    assert sum(l["prises"] for l in result["detail"]) == totaux["prises"]
    assert "esquisse" in result["avertissement"]


def test_piece_humide_recoit_des_points_d_eau():
    from BIM_Engine.models import BuildingProject, Room
    project = BuildingProject(name="Test", building_type="maison")
    project.rooms = [Room(name="Cuisine", kind="cuisine", area_m2=12.0),
                     Room(name="Chambre", kind="chambre", area_m2=12.0)]
    detail = {l["piece"]: l for l in MEPPlanner().plan(project)["detail"]}
    assert detail["Cuisine"]["points_eau"] > 0
    assert detail["Chambre"]["points_eau"] == 0
    assert detail["Cuisine"]["debit_m3h"] > 0


# ------------------------------- chantier -------------------------------
@pytest.fixture()
def planning(furnished):
    from Construction.planning import ConstructionPlanner
    from Estimating.cost_ai import CostEstimator
    estimator = CostEstimator()
    return ConstructionPlanner().plan(
        estimator.schedule(estimator.estimate(furnished)))


def test_avancement_detecte_le_retard(planning):
    taches = planning["taches"]
    milieu = taches[len(taches) // 2]
    jour = int((milieu["debut_jour"] + milieu["fin_jour"]) / 2)
    # tout le monde a zero : retard garanti sur les lots commences
    result = ProgressTracker().assess(planning, {}, jour)
    assert result["lots_en_retard"] >= 1
    en_retard = [l for l in result["lignes"] if l["statut"] == "en retard"]
    assert en_retard and all(l["ecart_points"] < 0 for l in en_retard)
    # tout le monde a 100 % : personne en retard
    parfait = ProgressTracker().assess(
        planning, {t["lot"]: 1.0 for t in taches}, jour)
    assert parfait["lots_en_retard"] == 0
    assert "aucun retard" in parfait["alerte"]


def test_avancement_attendu_borne(planning):
    tache = planning["taches"][0]
    avant = ProgressTracker().assess(planning, {}, tache["debut_jour"])
    ligne = next(l for l in avant["lignes"] if l["lot"] == tache["lot"])
    assert ligne["avancement_attendu"] == 0.0
    apres = ProgressTracker().assess(planning, {}, tache["fin_jour"] + 10)
    ligne = next(l for l in apres["lignes"] if l["lot"] == tache["lot"])
    assert ligne["avancement_attendu"] == 100.0


def test_ressources_et_approvisionnements(planning):
    result = ResourceManager().plan(planning["taches"])
    assert result["jours_homme_total"] > 0
    assert result["effectif_pointe"] >= 2
    commandes = result["approvisionnements"]
    jours = [c["commander_le_jour"] for c in commandes]
    assert jours == sorted(jours), "les commandes doivent etre triees"
    # les lots a long delai doivent etre commandes avant leur demarrage
    for commande in commandes:
        tache = next(t for t in planning["taches"] if t["lot"] == commande["lot"])
        assert commande["commander_le_jour"] <= tache["debut_jour"]


def test_securite_chantier(furnished):
    result = SafetyAnalyzer().analyze(furnished, "Gros oeuvre")
    assert result["nombre"] > 0
    graves = [r for r in result["risques"] if r["gravite"] == "haute"]
    assert graves, "une phase de gros oeuvre comporte des risques graves"
    assert result["risques"][0]["gravite"] == "haute", "tri par gravite"
    assert any("ouvertures" in r["origine"] for r in result["risques"])
    assert "SPS" in result["avertissement"]
    peinture = SafetyAnalyzer().analyze(furnished, "Peinture")
    assert any("solvants" in r["risque"] for r in peinture["risques"])


# ------------------------------ territoire ------------------------------
def test_consolidation_territoriale(furnished):
    from BIM_Engine.models import BuildingProject
    second = BuildingProject(name="Voisin", building_type="bureau")
    second.rooms = list(furnished.rooms)
    second.walls = list(furnished.walls)
    platform = CityPlatform()
    result = platform.aggregate(
        [furnished, second],
        energy_by_project={furnished.id: 8000.0, second.id: 12000.0},
        carbon_by_project={furnished.id: 25000.0, second.id: 40000.0},
        plot_area_m2=400.0)
    assert result["batiments"] == 2
    assert result["energie_totale_kwh_an"] == 20000.0
    assert result["carbone_total_t_co2e"] == 65.0
    assert result["coefficient_emprise"] > 0
    assert result["energie_moyenne_kwh_m2"] > 0
    assert set(result["par_typologie"]) == {"maison", "bureau"}


def test_export_geojson(furnished):
    data = CityPlatform().to_geojson([furnished])
    assert data["type"] == "FeatureCollection"
    assert data["features"], "un projet avec murs exterieurs doit produire une emprise"
    geometry = data["features"][0]["geometry"]
    assert geometry["type"] == "Polygon"
    anneau = geometry["coordinates"][0]
    assert anneau[0] == anneau[-1], "l'anneau doit etre ferme"
    assert data["features"][0]["properties"]["surface_m2"] > 0


def test_geojson_ignore_les_projets_sans_enveloppe():
    from BIM_Engine.models import BuildingProject
    vide = BuildingProject(name="Vide", building_type="maison")
    assert CityPlatform().to_geojson([vide])["features"] == []


# ------------------------------- registre -------------------------------
def test_registre_des_livrables():
    from DELIVERABLES import DELIVERABLES, GROUPS, by_group, by_state
    assert len(DELIVERABLES) == 70
    assert sorted(d["numero"] for d in DELIVERABLES) == list(range(1, 71))
    assert set(d["groupe"] for d in DELIVERABLES) <= set(GROUPS)
    livres = by_state("livre")
    assert livres and all(d["etat"] == "livre" for d in livres)
    coeur = by_group("CORE")
    assert coeur and all(d["groupe"] == "CORE" for d in coeur)
    total = sum(len(by_group(g)) for g in GROUPS)
    assert total == 70, "chaque livrable appartient a un groupe et un seul"
