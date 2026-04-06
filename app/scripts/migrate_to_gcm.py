"""
One-time migration: re-encrypt all messages AES-256-CBC → AES-256-GCM.

Безопасно запускать несколько раз:
  - уже мигрированные сообщения пропускаются (GCM decrypt succeeds → skip)
  - неудачные расшифровки логируются, приложение не падает

Вызывается автоматически из lifespan при каждом старте.
Как только все строки будут смигрированы — превращается в no-op (~1ms).
"""
import base64
import logging
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text

logger = logging.getLogger(__name__)

_NONCE_SIZE = 12
_TABLES = [
    ("messages", "content_encrypted", "id"),
    ("group_messages", "content_encrypted", "id"),
]


def _cbc_decrypt(key: bytes, ciphertext: str) -> str:
    raw = base64.b64decode(ciphertext)
    iv, ct = raw[:16], raw[16:]
    cipher = Cipher(
        algorithms.AES(key), modes.CBC(iv), backend=default_backend()
    )
    dec = cipher.decryptor()
    padded = dec.update(ct) + dec.finalize()
    pad_len = padded[-1]
    return padded[:-pad_len].decode()


def _gcm_try_decrypt(key: bytes, ciphertext: str) -> str | None:
    """Returns plaintext if GCM succeeds, None if not a GCM ciphertext."""
    try:
        raw = base64.b64decode(ciphertext)
        nonce, ct = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
        return AESGCM(key).decrypt(nonce, ct, None).decode()
    except (InvalidTag, Exception):
        return None


def _gcm_encrypt(key: bytes, plaintext: str) -> str:
    nonce = os.urandom(_NONCE_SIZE)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


async def run_migration(session_factory) -> None:
    """Call once at startup. session_factory = AsyncSessionLocal."""
    from app.core.config import settings

    key = bytes.fromhex(settings.CRYPTO_KEY)

    for table, col, pk in _TABLES:
        migrated = skipped = errors = 0

        async with session_factory() as db:
            result = await db.execute(text(f"SELECT {pk}, {col} FROM {table}"))
            rows = result.fetchall()

        for row_id, ciphertext in rows:
            if not ciphertext:
                skipped += 1
                continue

            # Already GCM — skip
            if _gcm_try_decrypt(key, ciphertext) is not None:
                skipped += 1
                continue

            # Attempt CBC decrypt
            try:
                plaintext = _cbc_decrypt(key, ciphertext)
            except Exception as exc:
                logger.error(
                    "migrate_to_gcm: cannot decrypt %s id=%s: %s",
                    table, row_id, exc,
                )
                errors += 1
                continue

            new_ct = _gcm_encrypt(key, plaintext)

            async with session_factory() as db:
                await db.execute(
                    text(f"UPDATE {table} SET {col} = :new WHERE {pk} = :id"),
                    {"new": new_ct, "id": row_id},
                )
                await db.commit()

            migrated += 1

        logger.info(
            "migrate_to_gcm [%s]: migrated=%s  skipped=%s  errors=%s",
            table, migrated, skipped, errors,
        )
