"""Tests d'integration de l'API : chaine complete du client au stockage."""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient    # noqa: E402

from API.main import app                     # noqa: E402


@pytest.fixture(scope="module")
def client(request):
    import os
    import tempfile
    from API.deps import reset_state
    directory = tempfile.mkdtemp(prefix="mercury_api_")
    reset_state(os.path.join(directory, "api.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_health_et_ready(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert client.get("/ready").json()["ready"] is True


def test_registre_des_livrables(client):
    data = client.get("/api/v1/deliverables").json()
    assert data["total"] == 70
    numeros = sorted(d["numero"] for d in data["livrables"])
    assert numeros == list(range(1, 71))


def test_cycle_de_vie_projet(client):
    created = client.post("/api/v1/projects",
                          json={"name": "Test API", "building_type": "maison"})
    assert created.status_code == 200
    project_id = created.json()["projet"]["id"]

    wall = client.post("/api/v1/projects/%s/walls" % project_id,
                       json={"start": [0, 0], "end": [6000, 0],
                             "thickness": 300, "height": 2700,
                             "exterior": True})
    assert wall.status_code == 200
    wall_id = wall.json()["mur"]["id"]

    opening = client.post("/api/v1/projects/%s/openings" % project_id,
                          json={"wall_id": wall_id, "type": "fenetre",
                                "offset": 3000, "width": 1200,
                                "height": 1400, "sill": 900})
    assert opening.status_code == 200

    hors = client.post("/api/v1/projects/%s/openings" % project_id,
                       json={"wall_id": wall_id, "type": "porte",
                             "offset": 5900, "width": 900, "height": 2100})
    assert hors.status_code == 400, "une baie hors du mur doit etre refusee"

    assert client.get("/api/v1/projects/%s" % project_id).status_code == 200
    assert client.get("/api/v1/projects/inconnu").status_code == 404


def test_generation_et_analyses(client):
    response = client.post("/api/v1/design/generate",
                           json={"typologie": "maison", "surface": 105,
                                 "chambres": 3, "variantes": 2,
                                 "iterations": 900})
    assert response.status_code == 200
    data = response.json()
    assert len(data["variantes"]) == 2
    project_id = data["meilleure"]

    takeoff = client.get("/api/v1/projects/%s/takeoff" % project_id).json()
    assert takeoff["resume"]["surface_utile_m2"] > 50
    assert takeoff["metre"]

    estimate = client.get("/api/v1/projects/%s/estimate" % project_id).json()
    assert estimate["devis"]["total_ht"] > 0
    assert estimate["planning"]["duree_totale_jours"] > 0

    carbon = client.get("/api/v1/projects/%s/carbon" % project_id).json()
    assert carbon["etiquette"] in list("ABCDE")

    energy = client.get("/api/v1/projects/%s/energy" % project_id).json()
    assert energy["kwh_m2_an"] > 0

    mauvais = client.get("/api/v1/projects/%s/energy?isolation=magique" % project_id)
    assert mauvais.status_code == 400


def test_exports(client):
    project_id = client.post("/api/v1/design/generate",
                             json={"typologie": "maison", "surface": 90,
                                   "variantes": 1, "iterations": 600}
                             ).json()["meilleure"]
    ifc = client.post("/api/v1/projects/%s/export" % project_id,
                      json={"format": "ifc"})
    assert ifc.status_code == 200
    assert ifc.text.startswith("ISO-10303-21;")
    assert "IFCWALLSTANDARDCASE" in ifc.text

    for fmt in ("obj", "gltf", "svg", "json"):
        response = client.post("/api/v1/projects/%s/export" % project_id,
                               json={"format": fmt})
        assert response.status_code == 200, fmt
        assert len(response.content) > 50, fmt

    assert client.post("/api/v1/projects/%s/export" % project_id,
                       json={"format": "dwg"}).status_code == 400


def test_jumeau_numerique(client):
    project_id = client.post("/api/v1/design/generate",
                             json={"typologie": "maison", "surface": 95,
                                   "variantes": 1, "iterations": 600}
                             ).json()["meilleure"]
    rooms = client.get("/api/v1/projects/%s" % project_id).json()["modele"]["rooms"]
    declared = client.post("/api/v1/iot/sensors",
                           json={"id": "sonde-1", "grandeur": "temperature",
                                 "projet": project_id, "piece": rooms[0]["id"]})
    assert declared.status_code == 200
    assert client.post("/api/v1/iot/sensors",
                       json={"id": "sonde-2", "grandeur": "gravite",
                             "projet": project_id}).status_code == 400
    client.post("/api/v1/iot/readings",
                json={"mesures": [{"capteur": "sonde-1", "valeur": 32.0}]})
    twin = client.get("/api/v1/projects/%s/twin" % project_id).json()
    assert twin["capteurs_total"] >= 1
    assert twin["alertes"]


def test_assistant_et_bibliotheque(client):
    response = client.post("/api/v1/assistant",
                           json={"message": "genere une maison de 130 m2"})
    assert response.json()["commande"]["action"] == "generate"
    library = client.get("/api/v1/library?limit=5").json()
    assert library["total"] <= 5 and library["objets"]
