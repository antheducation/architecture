-- Migration 002 : jumeau numerique, capteurs et journal d'audit.

CREATE TABLE IF NOT EXISTS sensors (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    room_id     TEXT,
    quantity    TEXT NOT NULL,
    name        TEXT NOT NULL DEFAULT '',
    unit        TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS sensor_readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id   TEXT NOT NULL,
    value       REAL NOT NULL,
    recorded_at REAL NOT NULL,
    FOREIGN KEY (sensor_id) REFERENCES sensors (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    at       REAL NOT NULL,
    user_id  TEXT NOT NULL DEFAULT '',
    action   TEXT NOT NULL,
    target   TEXT NOT NULL DEFAULT '',
    detail   TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_readings_sensor
    ON sensor_readings (sensor_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_audit_at ON audit_log (at);
