"""Tests des modeles IA : vision, assistant, maintenance predictive."""
from __future__ import annotations

import time

import pytest

from AI_Engine.nlp_assistant import ConversationalAssistant
from AI_Engine.predictive import PredictiveMaintenance
from AI_Engine.vision_ai import FakeWeights, PlanReader, PlanVisionModel


def test_poids_factices_deterministes():
    a, b = FakeWeights("graine"), FakeWeights("graine")
    assert a.checksum == b.checksum
    assert FakeWeights("autre").checksum != a.checksum


def test_modele_de_vision_api_correcte():
    model = PlanVisionModel()
    info = model.info()
    assert "classes" in info and "mur" in info["classes"]
    meta = model.preprocess(1600, 900)
    assert meta["resized"][0] == 640
    with pytest.raises(ValueError):
        model.preprocess(0, 100)
    detections = model.predict(1600, 900, seed="plan-1")
    assert isinstance(detections, list)
    for detection in detections:
        assert detection.confidence >= model.confidence_threshold
        assert detection.label in info["classes"]
        assert detection.width > 0 and detection.height > 0


def test_suppression_des_non_maxima():
    from AI_Engine.vision_ai import Detection
    model = PlanVisionModel()
    a = Detection("mur", 0.9, 0, 0, 100, 100)
    b = Detection("mur", 0.8, 5, 5, 100, 100)      # recouvre largement a
    c = Detection("mur", 0.7, 500, 500, 100, 100)  # isole
    kept = model.non_max_suppression([a, b, c])
    assert len(kept) == 2
    assert kept[0].confidence == 0.9


def test_lecture_de_plan_double_trait():
    """Deux traits paralleles distants de 200 mm forment un mur."""
    segments = [(0, 0, 6000, 0), (0, 200, 6000, 200)]
    walls = PlanReader().detect_walls(segments)
    assert len(walls) == 1
    assert abs(walls[0].thickness - 200) < 1
    assert walls[0].length > 5000
    assert walls[0].confidence > 0.5


def test_assistant_reconnait_les_commandes():
    assistant = ConversationalAssistant()
    assert assistant.parse("change le style en moderne").action == "set_style"
    assert assistant.parse("genere une maison de 120 m2").params["surface"] == 120
    assert assistant.parse("exporte en ifc").params["format"] == "ifc"
    assert assistant.parse("blablabla incomprehensible").action == "unknown"


def test_assistant_execute_les_handlers():
    assistant = ConversationalAssistant()
    assistant.register("set_style", lambda params: "style %s" % params["style"])
    result = assistant.execute("change le style en luxe")
    assert result["execute"] and "luxe" in result["resultat"]
    echec = assistant.execute("phrase sans commande")
    assert not echec["execute"]


def test_maintenance_predictive_detecte_une_derive():
    now = time.time()
    readings = [(now + i * 86400, 20.0 + i * 0.5) for i in range(10)]
    result = PredictiveMaintenance().assess(readings, threshold=30.0, rising=True)
    assert result["statut"] == "derive detectee"
    assert result["jours_avant_seuil"] > 0
    assert result["r2"] > 0.99
    stable = PredictiveMaintenance().assess(
        [(now + i * 86400, 20.0) for i in range(10)], threshold=30.0)
    assert stable["statut"] == "stable"
    court = PredictiveMaintenance().assess([(now, 20.0)], threshold=30.0)
    assert court["statut"] == "historique insuffisant"
