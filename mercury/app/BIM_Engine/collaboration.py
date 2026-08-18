"""Collaboration cloud (livrable #15).

Diffusion des modifications aux clients connectes et suivi de presence.
Le transport WebSocket est branche dans l'API ; ce module reste testable
sans reseau, ce qui permet de valider la logique en integration continue.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Participant:
    user_id: str
    joined_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class CollaborationHub:
    """Sessions par projet, journal des evenements, resolution simple."""

    def __init__(self, history: int = 200) -> None:
        self.sessions: Dict[str, Dict[str, Participant]] = {}
        self.journal: Dict[str, List[Dict[str, Any]]] = {}
        self.history = history

    def join(self, project_id: str, user_id: str) -> int:
        room = self.sessions.setdefault(project_id, {})
        room[user_id] = Participant(user_id)
        self._log(project_id, "presence", user_id, {"connectes": len(room)})
        return len(room)

    def leave(self, project_id: str, user_id: str) -> int:
        room = self.sessions.get(project_id, {})
        room.pop(user_id, None)
        self._log(project_id, "depart", user_id, {"connectes": len(room)})
        return len(room)

    def participants(self, project_id: str) -> List[str]:
        return sorted(self.sessions.get(project_id, {}))

    def publish(self, project_id: str, user_id: str, kind: str,
                payload: Dict[str, Any]) -> Dict[str, Any]:
        """Publie une modification et renvoie l'evenement diffuse."""
        if kind not in ("modification", "curseur", "commentaire"):
            raise ValueError("type d'evenement inconnu : %s" % kind)
        return self._log(project_id, kind, user_id, payload)

    def events(self, project_id: str, since: float = 0.0) -> List[Dict[str, Any]]:
        return [e for e in self.journal.get(project_id, []) if e["at"] > since]

    def _log(self, project_id: str, kind: str, user_id: str,
             payload: Dict[str, Any]) -> Dict[str, Any]:
        event = {"at": time.time(), "type": kind, "par": user_id, "detail": payload}
        entries = self.journal.setdefault(project_id, [])
        entries.append(event)
        if len(entries) > self.history:
            del entries[: len(entries) - self.history]
        return event
