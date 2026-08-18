-- Donnees initiales : organisation et compte de demonstration.
-- Le mot de passe est un hachage PBKDF2 genere par Security.auth.

INSERT OR IGNORE INTO tenants (id, name, plan)
VALUES ('default', 'Organisation de demonstration', 'pro');

INSERT OR IGNORE INTO users (id, tenant_id, email, name, password_hash, role)
VALUES ('usr_demo', 'default', 'demo@mercury.local', 'Utilisateur demo',
        'pbkdf2$200000$0000$0000', 'admin');
