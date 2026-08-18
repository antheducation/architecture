"""Controle d'acces par role (livrable #25).

Les roles sont hierarchiques et verifies au niveau de la ressource, pas de
la route : un utilisateur peut etre editeur sur un projet et lecteur sur un
autre. Verifier au niveau des routes conduit tot ou tard a un oubli.
"""
from __future__ import annotations

from typing import Dict, Optional, Set

ROLES = ("lecteur", "editeur", "proprietaire", "admin")
RANK: Dict[str, int] = {role: index for index, role in enumerate(ROLES)}

PERMISSIONS: Dict[str, str] = {
    "projet.lire": "lecteur",
    "projet.exporter": "lecteur",
    "projet.modifier": "editeur",
    "projet.generer": "editeur",
    "projet.supprimer": "proprietaire",
    "projet.partager": "proprietaire",
    "organisation.administrer": "admin",
}


class AccessControl:
    """Attribue les roles et repond aux questions d'autorisation."""

    def __init__(self) -> None:
        self._grants: Dict[str, Dict[str, str]] = {}
        self._globals: Dict[str, str] = {}

    def set_global_role(self, user_id: str, role: str) -> None:
        if role not in RANK:
            raise ValueError("role inconnu : %s" % sorted(ROLES))
        self._globals[user_id] = role

    def grant(self, project_id: str, user_id: str, role: str) -> None:
        if role not in RANK:
            raise ValueError("role inconnu : %s" % sorted(ROLES))
        self._grants.setdefault(project_id, {})[user_id] = role

    def revoke(self, project_id: str, user_id: str) -> bool:
        return self._grants.get(project_id, {}).pop(user_id, None) is not None

    def role_of(self, project_id: str, user_id: str) -> Optional[str]:
        if self._globals.get(user_id) == "admin":
            return "admin"
        return self._grants.get(project_id, {}).get(user_id)

    def can(self, project_id: str, user_id: str, permission: str) -> bool:
        required = PERMISSIONS.get(permission)
        if required is None:
            raise ValueError("permission inconnue : %s" % permission)
        role = self.role_of(project_id, user_id)
        if role is None:
            return False
        return RANK[role] >= RANK[required]

    def require(self, project_id: str, user_id: str, permission: str) -> None:
        if not self.can(project_id, user_id, permission):
            raise PermissionError(
                "acces refuse : la permission %s exige le role %s"
                % (permission, PERMISSIONS[permission]))

    def members(self, project_id: str) -> Dict[str, str]:
        return dict(self._grants.get(project_id, {}))
