-- Migration 001 : schema initial de MERCURY CAD AI X
-- Compatible SQLite et PostgreSQL (types volontairement neutres).

CREATE TABLE IF NOT EXISTS tenants (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    plan        TEXT NOT NULL DEFAULT 'essai',
    created_at  REAL NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL DEFAULT 'default',
    email         TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'editeur',
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    REAL NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS projects (
    id            TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL DEFAULT 'default',
    name          TEXT NOT NULL,
    building_type TEXT NOT NULL DEFAULT 'inconnu',
    version       INTEGER NOT NULL DEFAULT 1,
    deleted       INTEGER NOT NULL DEFAULT 0,
    created_at    REAL NOT NULL DEFAULT (strftime('%s','now')),
    updated_at    REAL NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS project_versions (
    project_id  TEXT NOT NULL,
    version     INTEGER NOT NULL,
    payload     BLOB NOT NULL,
    author      TEXT NOT NULL DEFAULT '',
    size        INTEGER NOT NULL DEFAULT 0,
    created_at  REAL NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (project_id, version),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS project_shares (
    project_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'lecteur',
    created_at  REAL NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (project_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_projects_tenant
    ON projects (tenant_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_versions_project
    ON project_versions (project_id, version);
