"""Chiffrement des donnees sensibles.

Chiffrement symetrique par flux derive de HMAC-SHA256, avec authentification
du message. Suffisant pour proteger un champ en base ; pour des volumes ou
des exigences reglementaires, brancher AES-GCM via `cryptography`.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Optional


class Encryptor:
    """Chiffre, dechiffre et verifie l'integrite."""

    def __init__(self, key: Optional[str] = None) -> None:
        self.key = (key or os.getenv("MERCURY_ENCRYPTION_KEY", "dev-key")).encode()

    def _stream(self, nonce: bytes, length: int) -> bytes:
        output = b""
        counter = 0
        while len(output) < length:
            block = hmac.new(self.key, nonce + counter.to_bytes(4, "big"),
                             hashlib.sha256).digest()
            output += block
            counter += 1
        return output[:length]

    def encrypt(self, plaintext: str) -> str:
        data = plaintext.encode("utf-8")
        nonce = os.urandom(16)
        cipher = bytes(a ^ b for a, b in zip(data, self._stream(nonce, len(data))))
        tag = hmac.new(self.key, nonce + cipher, hashlib.sha256).digest()[:16]
        return base64.urlsafe_b64encode(nonce + tag + cipher).decode()

    def decrypt(self, token: str) -> str:
        raw = base64.urlsafe_b64decode(token.encode())
        if len(raw) < 32:
            raise ValueError("message chiffre trop court")
        nonce, tag, cipher = raw[:16], raw[16:32], raw[32:]
        expected = hmac.new(self.key, nonce + cipher, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected):
            raise ValueError("integrite compromise : message altere ou mauvaise cle")
        data = bytes(a ^ b for a, b in zip(cipher, self._stream(nonce, len(cipher))))
        return data.decode("utf-8")
