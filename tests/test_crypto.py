"""Quick sanity check: AESCrypto encrypt->decrypt roundtrip."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_roundtrip():
    from app.crypto.aes import AESCrypto

    key = "a" * 64  # 64 hex chars = 32 bytes
    crypto = AESCrypto(key)
    plaintext = "Hello, ICQ! 🙂"
    assert crypto.decrypt(crypto.encrypt(plaintext)) == plaintext


def test_different_ciphertexts():
    """Same input → different ciphertext each time (random IV)."""
    from app.crypto.aes import AESCrypto

    key = "b" * 64
    crypto = AESCrypto(key)
    msg = "same message"
    assert crypto.encrypt(msg) != crypto.encrypt(msg)


if __name__ == "__main__":
    test_roundtrip()
    test_different_ciphertexts()
    print("✅  All crypto tests passed.")
