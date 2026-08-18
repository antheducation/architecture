"""Tests plateforme : base, securite, multi-tenant, jumeau, collaboration."""
from __future__ import annotations

import pytest

from BIM_Engine.collaboration import CollaborationHub
from Cloud_Platform.digital_twin import DigitalTwin
from Cloud_Platform.iot import IoTGateway, SensorRegistry
from Cloud_Platform.multi_tenant import TenantManager
from Security.auth import AuthService
from Security.encryption import Encryptor
from Security.rbac import AccessControl


def test_base_migrations_et_versions(state, project):
    version = state.repository.save(project)
    assert version >= 1
    project.name = "Renomme"
    second = state.repository.save(project)
    assert second > version
    loaded = state.repository.load(project.id)
    assert loaded.name == "Renomme"
    assert len(state.repository.versions(project.id)) >= 2
    ancienne = state.repository.load(project.id, version)
    assert ancienne.version == version


def test_projet_inconnu(state):
    with pytest.raises(KeyError):
        state.repository.load("inexistant")


def test_mots_de_passe_et_jetons():
    auth = AuthService(secret="test-secret")
    stored = auth.hash_password("motdepasse123")
    assert auth.verify_password("motdepasse123", stored)
    assert not auth.verify_password("mauvais", stored)
    with pytest.raises(ValueError):
        auth.hash_password("court")
    token = auth.create_token("usr_1", {"role": "admin"})
    payload = auth.decode_token(token)
    assert payload["sub"] == "usr_1" and payload["role"] == "admin"
    with pytest.raises(ValueError):
        auth.decode_token(token + "altere")


def test_chiffrement():
    encryptor = Encryptor("cle-de-test")
    secret = "donnee confidentielle"
    token = encryptor.encrypt(secret)
    assert token != secret
    assert encryptor.decrypt(token) == secret
    with pytest.raises(ValueError):
        Encryptor("autre-cle").decrypt(token)


def test_controle_acces():
    access = AccessControl()
    access.grant("prj_1", "usr_1", "editeur")
    assert access.can("prj_1", "usr_1", "projet.modifier")
    assert not access.can("prj_1", "usr_1", "projet.supprimer")
    assert not access.can("prj_1", "usr_2", "projet.lire")
    with pytest.raises(PermissionError):
        access.require("prj_1", "usr_1", "projet.supprimer")
    access.set_global_role("usr_admin", "admin")
    assert access.can("prj_1", "usr_admin", "projet.supprimer")


def test_multi_tenant_isole_les_projets():
    manager = TenantManager()
    manager.create("acme", "ACME", "essai")
    manager.add_project("acme", "prj_1")
    assert manager.owns("acme", "prj_1")
    assert not manager.owns("acme", "prj_2")
    with pytest.raises(PermissionError):
        manager.assert_access("acme", "prj_2")
    for index in range(2):
        manager.add_project("acme", "prj_%d" % (index + 10))
    with pytest.raises(ValueError):
        manager.add_project("acme", "prj_trop")     # quota de l'offre essai


def test_jumeau_numerique_pondere_les_alertes(furnished):
    registry = SensorRegistry()
    gateway = IoTGateway(registry)
    grande = max(furnished.rooms, key=lambda r: r.area_m2)
    registry.declare("t1", "temperature", furnished.id, grande.id, "Sonde")
    result = gateway.ingest([{"capteur": "t1", "valeur": 31.5},
                             {"capteur": "inconnu", "valeur": 1}])
    assert result["acceptees"] == 1 and result["capteurs_inconnus"] == ["inconnu"]
    state = DigitalTwin(registry).state(furnished)
    alerte = next(a for a in state["alertes"] if a["capteur"] == "t1")
    assert alerte["type"] == "hors consigne"
    assert alerte["gravite"] == ("haute" if grande.area_m2 > 20 else "moyenne")


def test_collaboration():
    hub = CollaborationHub()
    assert hub.join("prj_1", "usr_1") == 1
    assert hub.join("prj_1", "usr_2") == 2
    hub.publish("prj_1", "usr_1", "modification", {"mur": "wal_1"})
    assert len(hub.events("prj_1")) >= 3
    assert hub.leave("prj_1", "usr_2") == 1
    with pytest.raises(ValueError):
        hub.publish("prj_1", "usr_1", "sabotage", {})
