"""Sanity check: AES-GCM encrypt→decrypt roundtrip."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_roundtrip():
    from app.crypto.service import encrypt_text, decrypt_text

    plaintext = "Hello, ICQ! 🙂"
    assert decrypt_text(encrypt_text(plaintext)) == plaintext


def test_different_ciphertexts():
    """Same input → different ciphertext each time (random nonce)."""
    from app.crypto.service import encrypt_text

    msg = "same message"
    assert encrypt_text(msg) != encrypt_text(msg)


def test_gcm_detects_tampering():
    """GCM authentication tag catches any modification."""
    import base64
    import pytest
    from cryptography.exceptions import InvalidTag
    from app.crypto.service import encrypt_text, decrypt_text

    ct = encrypt_text("important data")
    raw = base64.b64decode(ct)
    tampered = raw[:-5] + bytes([raw[-5] ^ 0xFF]) + raw[-4:]
    with pytest.raises((InvalidTag, Exception)):
        decrypt_text(base64.b64encode(tampered).decode())


if __name__ == "__main__":
    test_roundtrip()
    test_different_ciphertexts()
    test_gcm_detects_tampering()
    print("✅  All crypto tests passed.")
