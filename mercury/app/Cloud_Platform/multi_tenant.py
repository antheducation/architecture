"""Multi-tenant (livrable #25).

Isolation des organisations : chaque projet appartient a un tenant, et
aucune requete ne peut franchir cette frontiere. L'isolation est verifiee
ici plutot que dans chaque route, ou elle finirait par etre oubliee.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

PLANS = {
    "essai": {"projets_max": 3, "membres_max": 2, "stockage_go": 1},
    "pro": {"projets_max": 200, "membres_max": 10, "stockage_go": 50},
    "entreprise": {"projets_max": 100000, "membres_max": 1000,
                   "stockage_go": 5000},
}


@dataclass
class Tenant:
    id: str
    name: str
    plan: str = "essai"
    created_at: float = field(default_factory=time.time)
    members: List[str] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)

    @property
    def quota(self) -> Dict[str, int]:
        return PLANS[self.plan]


class TenantManager:
    """Cree les organisations et fait respecter les quotas."""

    def __init__(self) -> None:
        self.tenants: Dict[str, Tenant] = {}

    def create(self, tenant_id: str, name: str, plan: str = "essai") -> Tenant:
        if plan not in PLANS:
            raise ValueError("offre inconnue : %s" % sorted(PLANS))
        if tenant_id in self.tenants:
            raise ValueError("organisation deja existante : %s" % tenant_id)
        tenant = Tenant(tenant_id, name, plan)
        self.tenants[tenant_id] = tenant
        return tenant

    def add_member(self, tenant_id: str, user_id: str) -> Tenant:
        tenant = self._require(tenant_id)
        if user_id in tenant.members:
            return tenant
        if len(tenant.members) >= tenant.quota["membres_max"]:
            raise ValueError("quota de membres atteint pour l'offre %s" % tenant.plan)
        tenant.members.append(user_id)
        return tenant

    def add_project(self, tenant_id: str, project_id: str) -> Tenant:
        tenant = self._require(tenant_id)
        if len(tenant.projects) >= tenant.quota["projets_max"]:
            raise ValueError("quota de projets atteint pour l'offre %s" % tenant.plan)
        tenant.projects.append(project_id)
        return tenant

    def owns(self, tenant_id: str, project_id: str) -> bool:
        tenant = self.tenants.get(tenant_id)
        return bool(tenant and project_id in tenant.projects)

    def assert_access(self, tenant_id: str, project_id: str) -> None:
        if not self.owns(tenant_id, project_id):
            raise PermissionError("projet hors du perimetre de l'organisation")

    def _require(self, tenant_id: str) -> Tenant:
        tenant = self.tenants.get(tenant_id)
        if tenant is None:
            raise KeyError("organisation inconnue : %s" % tenant_id)
        return tenant
