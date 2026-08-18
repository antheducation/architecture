"""Depot de projets versionne (livrable #21).

Chaque enregistrement cree une nouvelle version : l'historique complet est
conserve, donc l'annulation, la comparaison et la collaboration restent
possibles. Le contenu est stocke en JSON, ce qui evite toute migration de
schema a chaque evolution du modele BIM.
"""
from __future__ import annotations

import json
import time
import zlib
from typing import Any, Dict, List, Optional

from BIM_Engine.models import BuildingProject

from .session import Database


class ProjectRepository:
    """Ecrit et relit les projets, avec leur historique."""

    def __init__(self, database: Database) -> None:
        self.db = database

    def save(self, project: BuildingProject, tenant_id: str = "default",
             author: str = "system") -> int:
        payload = zlib.compress(
            json.dumps(project.to_dict(), ensure_ascii=False).encode("utf-8"), 6)
        existing = self.db.one("SELECT version FROM projects WHERE id = ?",
                               (project.id,))
        now = time.time()
        if existing is None:
            self.db.execute(
                "INSERT INTO projects (id, tenant_id, name, building_type, "
                "version, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (project.id, tenant_id, project.name, project.building_type,
                 project.version, now, now))
        else:
            project.version = max(project.version, int(existing["version"]) + 1)
            self.db.execute(
                "UPDATE projects SET name = ?, building_type = ?, version = ?, "
                "updated_at = ? WHERE id = ?",
                (project.name, project.building_type, project.version, now,
                 project.id))
        self.db.execute(
            "INSERT OR REPLACE INTO project_versions "
            "(project_id, version, payload, author, created_at, size) "
            "VALUES (?,?,?,?,?,?)",
            (project.id, project.version, payload, author, now, len(payload)))
        return project.version

    def load(self, project_id: str,
             version: Optional[int] = None) -> BuildingProject:
        row = self.db.one("SELECT * FROM projects WHERE id = ? AND deleted = 0",
                          (project_id,))
        if row is None:
            raise KeyError("projet introuvable : %s" % project_id)
        target = version or int(row["version"])
        data = self.db.one(
            "SELECT payload FROM project_versions WHERE project_id = ? "
            "AND version = ?", (project_id, target))
        if data is None:
            data = self.db.one(
                "SELECT payload FROM project_versions WHERE project_id = ? "
                "ORDER BY version DESC LIMIT 1", (project_id,))
        if data is None:
            raise KeyError("aucune version enregistree pour %s" % project_id)
        raw = json.loads(zlib.decompress(data["payload"]).decode("utf-8"))
        return BuildingProject.from_dict(raw)

    def list(self, tenant_id: Optional[str] = None,
             limit: int = 100) -> List[Dict[str, Any]]:
        if tenant_id:
            rows = self.db.query(
                "SELECT * FROM projects WHERE deleted = 0 AND tenant_id = ? "
                "ORDER BY updated_at DESC LIMIT ?", (tenant_id, limit))
        else:
            rows = self.db.query(
                "SELECT * FROM projects WHERE deleted = 0 "
                "ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in rows]

    def versions(self, project_id: str) -> List[int]:
        return [int(row["version"]) for row in self.db.query(
            "SELECT version FROM project_versions WHERE project_id = ? "
            "ORDER BY version", (project_id,))]

    def delete(self, project_id: str) -> bool:
        cursor = self.db.execute(
            "UPDATE projects SET deleted = 1, updated_at = ? WHERE id = ?",
            (time.time(), project_id))
        return cursor.rowcount > 0

    def audit(self, user_id: str, action: str, target: str = "",
              detail: str = "") -> None:
        self.db.execute(
            "INSERT INTO audit_log (at, user_id, action, target, detail) "
            "VALUES (?,?,?,?,?)",
            (time.time(), user_id, action, target, detail[:2000]))
