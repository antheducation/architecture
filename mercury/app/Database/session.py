"""Acces a la base (SQLite en local, PostgreSQL en production).

Le module n'utilise que `sqlite3` de la bibliotheque standard : le service
demarre sans aucune installation. Le meme schema SQL est applicable a
PostgreSQL ; seule la chaine de connexion change.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class Database:
    """Connexion, migrations et requetes parametrees."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or os.getenv("MERCURY_DB_PATH", "mercury.db")
        directory = os.path.dirname(os.path.abspath(self.path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    def migrate(self) -> List[str]:
        """Applique les migrations non encore executees, dans l'ordre."""
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "  name TEXT PRIMARY KEY,"
            "  applied_at REAL NOT NULL DEFAULT (strftime('%s','now')))")
        applied = {row["name"] for row in
                   self._connection.execute("SELECT name FROM schema_migrations")}
        executed: List[str] = []
        if not MIGRATIONS_DIR.is_dir():
            return executed
        for script in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if script.name in applied:
                continue
            sql = script.read_text(encoding="utf-8")
            try:
                self._connection.executescript(sql)
            except sqlite3.Error as error:
                raise RuntimeError(
                    "migration %s en echec : %s" % (script.name, error)) from error
            self._connection.execute(
                "INSERT INTO schema_migrations (name) VALUES (?)", (script.name,))
            self._connection.commit()
            executed.append(script.name)
        return executed

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        cursor = self._connection.execute(sql, params)
        self._connection.commit()
        return cursor

    def query(self, sql: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
        return list(self._connection.execute(sql, params))

    def one(self, sql: str, params: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def close(self) -> None:
        self._connection.close()
