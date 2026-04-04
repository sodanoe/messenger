import base64
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from app.crypto.base import BaseCrypto


class AESCrypto(BaseCrypto):
    """AES-256-CBC with PKCS7 padding. Key passed as 64-char hex string."""

    def __init__(self, hex_key: str) -> None:
        raw = bytes.fromhex(hex_key)
        if len(raw) != 32:
            raise ValueError("AES key must be 32 bytes (64 hex chars)")
        self._key = raw

    def encrypt(self, text: str, **kwargs) -> str:
        iv = os.urandom(16)
        padded = self._pad(text.encode())
        cipher = Cipher(
            algorithms.AES(self._key), modes.CBC(iv), backend=default_backend()
        )
        ct = cipher.encryptor().update(padded) + cipher.encryptor().finalize()
        # Store as  base64(iv + ciphertext)
        encryptor = cipher.encryptor()
        ct = encryptor.update(padded) + encryptor.finalize()
        return base64.b64encode(iv + ct).decode()

    def decrypt(self, text: str, **kwargs) -> str:
        raw = base64.b64decode(text.encode())
        iv, ct = raw[:16], raw[16:]
        cipher = Cipher(
            algorithms.AES(self._key), modes.CBC(iv), backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded = decryptor.update(ct) + decryptor.finalize()
        return self._unpad(padded).decode()

    @staticmethod
    def _pad(data: bytes) -> bytes:
        pad_len = 16 - len(data) % 16
        return data + bytes([pad_len] * pad_len)

    @staticmethod
    def _unpad(data: bytes) -> bytes:
        return data[: -data[-1]]
