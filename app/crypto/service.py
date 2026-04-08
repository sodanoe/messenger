"""
AES-256-GCM encryption service.

Public API:
    encrypt_text(text: str) -> str
    decrypt_text(ciphertext: str) -> str

Storage format: base64(nonce[12] + ciphertext + tag[16])
"""

import base64
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_SIZE = 12


@lru_cache(maxsize=1)
def _get_key() -> bytes:
    from app.core.config import settings

    key = bytes.fromhex(settings.CRYPTO_KEY)
    if len(key) != 32:
        raise ValueError("CRYPTO_KEY must be 32 bytes (64 hex chars)")
    return key


def encrypt_text(text: str) -> str:
    nonce = os.urandom(_NONCE_SIZE)
    ct = AESGCM(_get_key()).encrypt(nonce, text.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_text(ciphertext: str) -> str:
    raw = base64.b64decode(ciphertext)
    nonce, ct = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
    return AESGCM(_get_key()).decrypt(nonce, ct, None).decode()
