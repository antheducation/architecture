"""Authentification (livrable #25).

Hachage PBKDF2-HMAC-SHA256 et jetons signes HMAC. Aucune dependance : le
service demarre sans installation, et le format des jetons reste compatible
avec la specification JWT (HS256), donc interoperable.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

ITERATIONS = 200_000


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class AuthService:
    """Mots de passe, jetons de session et cles d'API."""

    def __init__(self, secret: Optional[str] = None, ttl_hours: int = 12) -> None:
        self.secret = secret or os.getenv("MERCURY_JWT_SECRET", "dev-secret")
        if ttl_hours <= 0:
            raise ValueError("la duree de validite doit etre positive")
        self.ttl_hours = ttl_hours

    # -- mots de passe -----------------------------------------------------
    @staticmethod
    def hash_password(password: str) -> str:
        if len(password) < 8:
            raise ValueError("mot de passe trop court (8 caracteres minimum)")
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
        return "pbkdf2$%d$%s$%s" % (ITERATIONS, salt.hex(), digest.hex())

    @staticmethod
    def verify_password(password: str, stored: str) -> bool:
        try:
            _, iterations, salt_hex, digest_hex = stored.split("$")
            digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                         bytes.fromhex(salt_hex), int(iterations))
            return hmac.compare_digest(digest.hex(), digest_hex)
        except Exception:
            return False

    # -- jetons ------------------------------------------------------------
    def create_token(self, subject: str,
                     claims: Optional[Dict[str, Any]] = None) -> str:
        payload: Dict[str, Any] = {
            "sub": subject, "iat": int(time.time()),
            "exp": int(time.time()) + self.ttl_hours * 3600,
        }
        payload.update(claims or {})
        header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        body = _b64(json.dumps(payload, separators=(",", ":")).encode())
        signature = hmac.new(self.secret.encode(),
                             ("%s.%s" % (header, body)).encode(),
                             hashlib.sha256).digest()
        return "%s.%s.%s" % (header, body, _b64(signature))

    def decode_token(self, token: str) -> Dict[str, Any]:
        try:
            header, body, signature = token.split(".")
        except ValueError:
            raise ValueError("jeton malforme")
        expected = hmac.new(self.secret.encode(),
                            ("%s.%s" % (header, body)).encode(),
                            hashlib.sha256).digest()
        if not hmac.compare_digest(_b64(expected), signature):
            raise ValueError("signature invalide")
        payload = json.loads(_unb64(body))
        if int(payload.get("exp", 0)) < time.time():
            raise ValueError("jeton expire")
        return payload

    # -- cles d'API --------------------------------------------------------
    @staticmethod
    def generate_api_key() -> str:
        return "mk_" + base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("=")

    @staticmethod
    def hash_api_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()
