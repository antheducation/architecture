"""Dependances partagees de l'API : etat applicatif unique.

Un seul point d'entree pour la base, le depot, les moteurs et les services.
Les routes ne construisent rien elles-memes : elles demandent, ce qui rend
les tests d'integration triviaux.
"""
from __future__ import annotations

import os
from typing import Optional

from AI_Engine.generative_design import GenerativeDesigner
from AI_Engine.nlp_assistant import ConversationalAssistant
from AI_Engine.predictive import PredictiveMaintenance
from AI_Engine.vision_ai import PlanReader, PlanVisionModel
from BIM_Engine.collaboration import CollaborationHub
from BIM_Engine.ifc_handler import IFCHandler
from BIM_Engine.object_library import ObjectLibrary
from CAD_Core.documentation import DocumentGenerator
from CAD_Core.engine_2d import Engine2D
from CAD_Core.engine_3d import Engine3D
from CAD_Core.rendering import Renderer
from Cloud_Platform.digital_twin import DigitalTwin
from Cloud_Platform.iot import IoTGateway, SensorRegistry
from Cloud_Platform.multi_tenant import TenantManager
from Construction.planning import ConstructionPlanner
from Database.repository import ProjectRepository
from Database.session import Database
from Estimating.cost_ai import CostEstimator
from Estimating.takeoff import QuantityTakeoff
from Security.auth import AuthService
from Security.rbac import AccessControl
from Sustainability.carbon import CarbonAnalyzer
from Sustainability.certification import CertificationScorer
from Sustainability.energy import EnergySimulator


class AppState:
    """Conteneur de services, construit une seule fois au demarrage."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.database = Database(db_path or os.getenv("MERCURY_DB_PATH",
                                                      "mercury.db"))
        self.applied_migrations = self.database.migrate()
        self.repository = ProjectRepository(self.database)

        self.engine_2d = Engine2D()
        self.engine_3d = Engine3D()
        self.renderer = Renderer()
        self.documents = DocumentGenerator()

        self.designer = GenerativeDesigner()
        self.assistant = ConversationalAssistant()
        self.vision = PlanVisionModel()
        self.plan_reader = PlanReader()
        self.predictive = PredictiveMaintenance()

        self.library = ObjectLibrary()
        self.ifc = IFCHandler()
        self.collaboration = CollaborationHub()

        self.takeoff = QuantityTakeoff()
        self.estimator = CostEstimator()
        self.planner = ConstructionPlanner()

        self.carbon = CarbonAnalyzer()
        self.energy = EnergySimulator()
        self.certification = CertificationScorer()

        self.sensors = SensorRegistry()
        self.iot = IoTGateway(self.sensors)
        self.twin = DigitalTwin(self.sensors)
        self.tenants = TenantManager()

        self.auth = AuthService()
        self.access = AccessControl()

    def close(self) -> None:
        self.database.close()


STATE: Optional[AppState] = None


def get_state() -> AppState:
    """Renvoie l'etat applicatif, en le creant au premier appel."""
    global STATE
    if STATE is None:
        STATE = AppState()
    return STATE


def reset_state(db_path: Optional[str] = None) -> AppState:
    """Reinitialise l'etat : utilise par les tests pour repartir a neuf."""
    global STATE
    if STATE is not None:
        STATE.close()
    STATE = AppState(db_path)
    return STATE
