"""Registre des 70 livrables du PROJET TITAN.

Source unique consommee par l'API (/api/v1/deliverables), la
documentation et les tests de conformite.
"""
from __future__ import annotations

from typing import Any, Dict, List

DELIVERABLES: List[Dict[str, Any]] = [
    {
        "numero": 1,
        "titre": "Vision et architecture globale",
        "groupe": "CORE",
        "module": "docs",
        "etat": "livre"
    },
    {
        "numero": 2,
        "titre": "Analyse marche CAO BIM Construction Tech",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "documente"
    },
    {
        "numero": 3,
        "titre": "Moteur IA Design Generatif",
        "groupe": "CORE",
        "module": "AI_Engine.generative_design",
        "etat": "livre"
    },
    {
        "numero": 4,
        "titre": "Assistant conversationnel IA ingenierie",
        "groupe": "CORE",
        "module": "AI_Engine.nlp_assistant",
        "etat": "livre"
    },
    {
        "numero": 5,
        "titre": "Lecture automatique PDF et plans",
        "groupe": "CORE",
        "module": "AI_Engine.vision_ai",
        "etat": "livre"
    },
    {
        "numero": 6,
        "titre": "Vision AI reconnaissance plans",
        "groupe": "CORE",
        "module": "AI_Engine.vision_ai",
        "etat": "livre"
    },
    {
        "numero": 7,
        "titre": "Conversion 2D vers 3D",
        "groupe": "CORE",
        "module": "CAD_Core.engine_3d",
        "etat": "livre"
    },
    {
        "numero": 8,
        "titre": "Interface CAO nouvelle generation",
        "groupe": "CORE",
        "module": "Frontend",
        "etat": "livre"
    },
    {
        "numero": 9,
        "titre": "Rendu 3D temps reel",
        "groupe": "CORE",
        "module": "CAD_Core.rendering",
        "etat": "livre"
    },
    {
        "numero": 10,
        "titre": "MVP initial",
        "groupe": "CORE",
        "module": "API.main",
        "etat": "livre"
    },
    {
        "numero": 11,
        "titre": "BIM Engine",
        "groupe": "BIM",
        "module": "BIM_Engine.models",
        "etat": "livre"
    },
    {
        "numero": 12,
        "titre": "Objets BIM intelligents",
        "groupe": "BIM",
        "module": "BIM_Engine.object_library",
        "etat": "livre"
    },
    {
        "numero": 13,
        "titre": "Bibliotheque BIM",
        "groupe": "BIM",
        "module": "BIM_Engine.object_library",
        "etat": "livre"
    },
    {
        "numero": 14,
        "titre": "Standards IFC",
        "groupe": "BIM",
        "module": "BIM_Engine.ifc_handler",
        "etat": "livre"
    },
    {
        "numero": 15,
        "titre": "BIM Cloud Collaboration",
        "groupe": "COLLAB",
        "module": "BIM_Engine.collaboration",
        "etat": "livre"
    },
    {
        "numero": 16,
        "titre": "Architecture Professional Module",
        "groupe": "BIM",
        "module": "CAD_Core.engine_2d",
        "etat": "livre"
    },
    {
        "numero": 17,
        "titre": "Structure Engineering Module",
        "groupe": "BIM",
        "module": "BIM_Engine.structure",
        "etat": "esquisse"
    },
    {
        "numero": 18,
        "titre": "MEP Engineering Module",
        "groupe": "BIM",
        "module": "BIM_Engine.mep",
        "etat": "esquisse"
    },
    {
        "numero": 19,
        "titre": "Documentation automatique",
        "groupe": "BIM",
        "module": "CAD_Core.documentation",
        "etat": "livre"
    },
    {
        "numero": 20,
        "titre": "Assistant ingenieur BIM IA",
        "groupe": "CORE",
        "module": "AI_Engine.nlp_assistant",
        "etat": "livre"
    },
    {
        "numero": 21,
        "titre": "Gestion versions projet",
        "groupe": "COLLAB",
        "module": "Database.repository",
        "etat": "livre"
    },
    {
        "numero": 22,
        "titre": "Marketplace BIM",
        "groupe": "BIM",
        "module": "BIM_Engine.object_library",
        "etat": "esquisse"
    },
    {
        "numero": 23,
        "titre": "Fabricants materiaux",
        "groupe": "BIM",
        "module": "BIM_Engine.object_library",
        "etat": "esquisse"
    },
    {
        "numero": 24,
        "titre": "API BIM",
        "groupe": "CORE",
        "module": "API.main",
        "etat": "livre"
    },
    {
        "numero": 25,
        "titre": "Enterprise BIM Platform",
        "groupe": "COLLAB",
        "module": "Security.rbac",
        "etat": "livre"
    },
    {
        "numero": 26,
        "titre": "Construction AI Platform",
        "groupe": "CONSTRUCTION",
        "module": "Construction.platform",
        "etat": "esquisse"
    },
    {
        "numero": 27,
        "titre": "Planning chantier IA",
        "groupe": "CONSTRUCTION",
        "module": "Construction.planning",
        "etat": "livre"
    },
    {
        "numero": 28,
        "titre": "Suivi avancement chantier",
        "groupe": "CONSTRUCTION",
        "module": "Construction.progress",
        "etat": "esquisse"
    },
    {
        "numero": 29,
        "titre": "Vision IA qualite",
        "groupe": "CONSTRUCTION",
        "module": "AI_Engine.vision_ai",
        "etat": "esquisse"
    },
    {
        "numero": 30,
        "titre": "Securite chantier IA",
        "groupe": "CONSTRUCTION",
        "module": "Construction.safety",
        "etat": "esquisse"
    },
    {
        "numero": 31,
        "titre": "Drone chantier",
        "groupe": "CONSTRUCTION",
        "module": "Construction.drone",
        "etat": "esquisse"
    },
    {
        "numero": 32,
        "titre": "Comparaison BIM reel",
        "groupe": "CONSTRUCTION",
        "module": "Construction.progress",
        "etat": "esquisse"
    },
    {
        "numero": 33,
        "titre": "Gestion ressources",
        "groupe": "CONSTRUCTION",
        "module": "Construction.resources",
        "etat": "esquisse"
    },
    {
        "numero": 34,
        "titre": "Gestion fournisseurs",
        "groupe": "CONSTRUCTION",
        "module": "Construction.resources",
        "etat": "esquisse"
    },
    {
        "numero": 35,
        "titre": "Rapports automatiques",
        "groupe": "CONSTRUCTION",
        "module": "CAD_Core.documentation",
        "etat": "livre"
    },
    {
        "numero": 36,
        "titre": "Cost AI",
        "groupe": "COST",
        "module": "Estimating.cost_ai",
        "etat": "livre"
    },
    {
        "numero": 37,
        "titre": "Metres automatiques",
        "groupe": "COST",
        "module": "Estimating.takeoff",
        "etat": "livre"
    },
    {
        "numero": 38,
        "titre": "Devis IA",
        "groupe": "COST",
        "module": "Estimating.cost_ai",
        "etat": "livre"
    },
    {
        "numero": 39,
        "titre": "Optimisation budget",
        "groupe": "COST",
        "module": "Estimating.cost_ai",
        "etat": "esquisse"
    },
    {
        "numero": 40,
        "titre": "Project Management Enterprise",
        "groupe": "COLLAB",
        "module": "Construction.planning",
        "etat": "esquisse"
    },
    {
        "numero": 41,
        "titre": "Digital Twin Platform",
        "groupe": "TWIN",
        "module": "Cloud_Platform.digital_twin",
        "etat": "livre"
    },
    {
        "numero": 42,
        "titre": "Smart Building OS",
        "groupe": "TWIN",
        "module": "Cloud_Platform.digital_twin",
        "etat": "esquisse"
    },
    {
        "numero": 43,
        "titre": "IoT Integration",
        "groupe": "TWIN",
        "module": "Cloud_Platform.iot",
        "etat": "livre"
    },
    {
        "numero": 44,
        "titre": "Maintenance predictive",
        "groupe": "TWIN",
        "module": "Cloud_Platform.predictive",
        "etat": "livre"
    },
    {
        "numero": 45,
        "titre": "Energy Intelligence",
        "groupe": "GREEN",
        "module": "Sustainability.energy",
        "etat": "livre"
    },
    {
        "numero": 46,
        "titre": "Solar Microgrid",
        "groupe": "GREEN",
        "module": "Sustainability.energy",
        "etat": "esquisse"
    },
    {
        "numero": 47,
        "titre": "Performance batiment",
        "groupe": "GREEN",
        "module": "Sustainability.energy",
        "etat": "livre"
    },
    {
        "numero": 48,
        "titre": "AR Maintenance",
        "groupe": "MOBILE",
        "module": "Mobile.ar",
        "etat": "esquisse"
    },
    {
        "numero": 49,
        "titre": "Drone Inspection Digital Twin",
        "groupe": "TWIN",
        "module": "Construction.drone",
        "etat": "esquisse"
    },
    {
        "numero": 50,
        "titre": "Cycle de vie batiment",
        "groupe": "GREEN",
        "module": "Sustainability.carbon",
        "etat": "livre"
    },
    {
        "numero": 51,
        "titre": "Green Building AI",
        "groupe": "GREEN",
        "module": "Sustainability.carbon",
        "etat": "livre"
    },
    {
        "numero": 52,
        "titre": "Calcul carbone",
        "groupe": "GREEN",
        "module": "Sustainability.carbon",
        "etat": "livre"
    },
    {
        "numero": 53,
        "titre": "Materiaux durables",
        "groupe": "GREEN",
        "module": "Sustainability.carbon",
        "etat": "livre"
    },
    {
        "numero": 54,
        "titre": "Simulation energetique",
        "groupe": "GREEN",
        "module": "Sustainability.energy",
        "etat": "livre"
    },
    {
        "numero": 55,
        "titre": "Certification verte",
        "groupe": "GREEN",
        "module": "Sustainability.certification",
        "etat": "livre"
    },
    {
        "numero": 56,
        "titre": "Adaptation climatique",
        "groupe": "GREEN",
        "module": "Sustainability.energy",
        "etat": "esquisse"
    },
    {
        "numero": 57,
        "titre": "Smart Village Platform",
        "groupe": "CITY",
        "module": "Cloud_Platform.city",
        "etat": "esquisse"
    },
    {
        "numero": 58,
        "titre": "Digital Twin Smart City",
        "groupe": "CITY",
        "module": "Cloud_Platform.city",
        "etat": "esquisse"
    },
    {
        "numero": 59,
        "titre": "GIS Topography Drone",
        "groupe": "CITY",
        "module": "Cloud_Platform.city",
        "etat": "esquisse"
    },
    {
        "numero": 60,
        "titre": "Finance Projet AI",
        "groupe": "BUSINESS",
        "module": "Estimating.cost_ai",
        "etat": "esquisse"
    },
    {
        "numero": 61,
        "titre": "Sustainability AI",
        "groupe": "GREEN",
        "module": "Sustainability.carbon",
        "etat": "livre"
    },
    {
        "numero": 62,
        "titre": "Topography Integration",
        "groupe": "CITY",
        "module": "Cloud_Platform.city",
        "etat": "esquisse"
    },
    {
        "numero": 63,
        "titre": "Mobile Tablet Platform",
        "groupe": "MOBILE",
        "module": "Mobile",
        "etat": "livre"
    },
    {
        "numero": 64,
        "titre": "Expansion internationale",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "documente"
    },
    {
        "numero": 65,
        "titre": "Legal Corporate Governance",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "documente"
    },
    {
        "numero": 66,
        "titre": "Investor Package",
        "groupe": "BUSINESS",
        "module": "docs/INVESTOR_DECK.md",
        "etat": "documente"
    },
    {
        "numero": 67,
        "titre": "Documentation technique",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "livre"
    },
    {
        "numero": 68,
        "titre": "Beta Testing Program",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "documente"
    },
    {
        "numero": 69,
        "titre": "Global Launch Plan",
        "groupe": "BUSINESS",
        "module": "docs",
        "etat": "documente"
    },
    {
        "numero": 70,
        "titre": "Master Plan 2030",
        "groupe": "BUSINESS",
        "module": "docs/ROADMAP_2030.md",
        "etat": "documente"
    }
]

GROUPS: Dict[str, str] = {
    "CORE": "Systeme central : CAO, IA, interface, MVP",
    "BIM": "Moteur BIM, objets, standards IFC, metiers",
    "COLLAB": "Collaboration, versions, entreprise",
    "CONSTRUCTION": "Chantier : planning, suivi, qualite, securite",
    "COST": "Economie : metres, couts, devis",
    "TWIN": "Jumeau numerique, IoT, maintenance",
    "GREEN": "Environnement : carbone, energie, certification",
    "CITY": "Territoire : village et ville intelligents",
    "MOBILE": "Terrain : tablette, mobile, realite augmentee",
    "BUSINESS": "Marche, juridique, investisseurs, lancement"
}


def by_group(group: str) -> List[Dict[str, Any]]:
    """Livrables d'un groupe donne."""
    return [d for d in DELIVERABLES if d['groupe'] == group]


def by_state(state: str) -> List[Dict[str, Any]]:
    """Livrables dans un etat donne : livre, esquisse, documente."""
    return [d for d in DELIVERABLES if d['etat'] == state]
