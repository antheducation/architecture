"""Routes CAO de l'API : documents, commandes, geometrie, fichiers."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from API.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture()
def document(client):
    reponse = client.post("/api/v1/cad/documents", json={"nom": "Essai"})
    assert reponse.status_code == 200
    return reponse.json()["document"]


def commande(client, document, nom, **parametres):
    return client.post("/api/v1/cad/documents/%s/command" % document,
                       json={"commande": nom, "parametres": parametres})


def test_racine_annonce_le_module_cao(client):
    charge = client.get("/").json()
    assert charge["commandes_cao"] >= 90
    assert charge["formats_fichiers"] >= 25
    assert charge["interface"] == "/app"


def test_interface_est_servie(client):
    page = client.get("/app/")
    assert page.status_code == 200
    assert "MERCURY" in page.text
    assert client.get("/app/style.css").status_code == 200
    assert client.get("/app/viewer.js").status_code == 200
    assert client.get("/app/app.js").status_code == 200
    assert client.get("/app/secret.env").status_code == 404


def test_catalogue_et_capacites(client):
    catalogue = client.get("/api/v1/cad/commands").json()
    assert catalogue["total"] >= 90
    assert "solides_primitifs" in catalogue["groupes"]
    filtre = client.get("/api/v1/cad/commands?groupe=booleens").json()
    assert all(c["groupe"] == "booleens" for c in filtre["commandes"])
    capacites = client.get("/api/v1/cad/capabilities").json()
    assert capacites["commandes"] >= 90
    assert "realiste" in capacites["styles_visuels"]
    assert "iso_sud_ouest" in capacites["vues_normalisees"]
    formats = client.get("/api/v1/cad/formats").json()
    assert formats["total"] >= 25
    assert "installation" in formats["dwg"]


def test_cycle_de_vie_dun_document(client):
    cree = client.post("/api/v1/cad/documents",
                       json={"nom": "Villa", "unites": "mm"}).json()
    identifiant = cree["document"]
    assert client.get("/api/v1/cad/documents").json()["total"] >= 1
    detail = client.get("/api/v1/cad/documents/%s" % identifiant).json()
    assert detail["etat"]["nom"] == "Villa"
    assert client.get("/api/v1/cad/documents/%s?detail=true"
                      % identifiant).json()["contenu"]["document"] == "Villa"
    assert client.delete("/api/v1/cad/documents/%s" % identifiant).json()["ferme"]
    assert client.get("/api/v1/cad/documents/%s" % identifiant).status_code == 404


def test_unite_invalide_refusee(client):
    assert client.post("/api/v1/cad/documents",
                       json={"nom": "X", "unites": "lieues"}).status_code == 422


def test_execution_de_commandes(client, document):
    reponse = commande(client, document, "BOITE", longueur=2000, largeur=1000,
                       hauteur=500)
    assert reponse.status_code == 200
    charge = reponse.json()
    assert charge["etat"]["objets"] == 1
    assert charge["resultat"]["groupe"] == "solides_primitifs"
    assert commande(client, document, "CYLINDRE", rayon=200,
                    hauteur=800).status_code == 200
    erreur = commande(client, document, "COMMANDE_INEXISTANTE")
    assert erreur.status_code == 400
    assert "inconnue" in erreur.json()["detail"]


def test_script_et_historique(client, document):
    reponse = client.post("/api/v1/cad/documents/%s/script" % document,
                          json={"script": "BOITE longueur=100 largeur=100 "
                                          "hauteur=100\nCERCLE rayon=50"})
    assert reponse.json()["commandes"] == 2
    historique = client.get("/api/v1/cad/documents/%s/history" % document).json()
    assert historique["total"] >= 2
    mauvais = client.post("/api/v1/cad/documents/%s/script" % document,
                          json={"script": "PASUNECOMMANDE"})
    assert mauvais.status_code == 400


def test_geometrie_pour_la_visionneuse(client, document):
    commande(client, document, "BOITE", longueur=1000, largeur=1000,
             hauteur=1000)
    commande(client, document, "CERCLE", rayon=400)
    maillage = client.get("/api/v1/cad/documents/%s/mesh" % document).json()
    assert maillage["sommets"] == 36           # 12 triangles pour un cube
    assert len(maillage["positions"]) == maillage["sommets"] * 3
    assert len(maillage["normales"]) == len(maillage["positions"])
    assert len(maillage["groupes"]) == 1
    # La boite est celle du document entier : elle englobe aussi le cercle,
    # puisque c'est elle qui cadre le zoom etendu de l'interface.
    assert maillage["boite"]["taille"] == [1400.0, 1400.0, 1000.0]
    courbes = client.get("/api/v1/cad/documents/%s/curves" % document).json()
    assert courbes["total"] == 1
    toutes = client.get("/api/v1/cad/documents/%s/mesh?angle_aretes=0"
                        % document).json()
    assert len(toutes["aretes"]) >= len(maillage["aretes"])


def test_aretes_vives_filtrent_les_facettes(client, document):
    commande(client, document, "SPHERE", rayon=500, segments=24, anneaux=12)
    vives = client.get("/api/v1/cad/documents/%s/mesh?angle_aretes=25"
                       % document).json()
    toutes = client.get("/api/v1/cad/documents/%s/mesh?angle_aretes=0"
                        % document).json()
    assert len(vives["aretes"]) < len(toutes["aretes"])


def test_rendu_png(client, document):
    commande(client, document, "BOITE", longueur=1000, largeur=1000,
             hauteur=1000)
    image = client.post("/api/v1/cad/documents/%s/render" % document,
                        json={"largeur": 160, "hauteur": 120,
                              "style": "conceptuel"})
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.post("/api/v1/cad/documents/%s/render" % document,
                       json={"style": "aquarelle"}).status_code == 400
    assert client.post("/api/v1/cad/documents/%s/render" % document,
                       json={"largeur": 99999}).status_code == 422


@pytest.mark.parametrize("format_cible", ["dxf", "step", "stl", "obj", "gltf",
                                          "glb", "ply", "3mf", "ifc", "pdf",
                                          "svg", "json", "png", "xyz", "las"])
def test_export_dans_chaque_format(client, document, format_cible):
    commande(client, document, "BOITE", longueur=1000, largeur=1000,
             hauteur=1000)
    reponse = client.post("/api/v1/cad/documents/%s/export" % document,
                          json={"format": format_cible, "options": {}})
    assert reponse.status_code == 200
    assert len(reponse.content) > 0
    assert "attachment" in reponse.headers["content-disposition"]


def test_export_dans_un_format_inconnu(client, document):
    reponse = client.post("/api/v1/cad/documents/%s/export" % document,
                          json={"format": "zzz"})
    assert reponse.status_code == 400


def test_identification_import_et_conversion(client, document):
    commande(client, document, "BOITE", longueur=1000, largeur=500, hauteur=300)
    export = client.post("/api/v1/cad/documents/%s/export" % document,
                         json={"format": "stl"})
    contenu = export.content

    identite = client.post("/api/v1/cad/files/identify",
                           files={"fichier": ("piece.stl", contenu,
                                              "application/octet-stream")})
    assert identite.json()["identification"]["format"] == "stl"

    ouvert = client.post("/api/v1/cad/files/open",
                         files={"fichier": ("piece.stl", contenu,
                                            "application/octet-stream")})
    assert ouvert.status_code == 200
    assert ouvert.json()["etat"]["objets"] == 1

    fusionne = client.post("/api/v1/cad/documents/%s/import" % document,
                           files={"fichier": ("piece.stl", contenu,
                                              "application/octet-stream")})
    assert fusionne.json()["objets_ajoutes"] == 1

    converti = client.post("/api/v1/cad/files/convert?cible=step",
                           files={"fichier": ("piece.stl", contenu,
                                              "application/octet-stream")})
    assert converti.status_code == 200
    assert b"ISO-10303-21" in converti.content


def test_fichier_illisible_est_refuse(client):
    reponse = client.post("/api/v1/cad/files/open",
                          files={"fichier": ("x.bin", b"\x01\x02\x03\x04",
                                             "application/octet-stream")})
    assert reponse.status_code == 400


def test_document_inconnu(client):
    assert commande(client, "doc-9999", "BOITE").status_code == 404
    assert client.get("/api/v1/cad/documents/doc-9999/mesh").status_code == 404
