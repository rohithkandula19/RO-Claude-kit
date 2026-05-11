"""Symmetric encryption for stored third-party credentials.

We use Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography package.
The single key lives in ``FERNET_KEY`` env var in production. Rotating it
re-encrypts existing rows via a migration script.

For Stripe Restricted Keys / Linear PATs / etc., this means even a stolen DB
dump doesn't leak credentials.
"""
from __future__ import annotations

import hashlib
import hmac
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    return Fernet(get_settings().fernet_key.encode("utf-8"))


def encrypt(plaintext: str) -> str:
    """Returns a URL-safe ciphertext."""
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """Raises ``cryptography.fernet.InvalidToken`` if the ciphertext is corrupt or the key changed."""
    if not ciphertext:
        return ""
    return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def hash_api_token(token: str) -> str:
    """One-way hash for storing per-user API tokens. We compare hashes on auth,
    so a DB leak doesn't hand attackers usable tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_api_token(token: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_api_token(token), stored_hash)


__all__ = ["encrypt", "decrypt", "hash_api_token", "verify_api_token", "InvalidToken"]
