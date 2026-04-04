from functools import lru_cache

from app.crypto.base import BaseCrypto


@lru_cache(maxsize=1)
def get_crypto() -> BaseCrypto:
    from app.core.config import settings  # lazy to avoid circular imports

    backend = settings.CRYPTO_BACKEND.lower()
    if backend == "aes":
        from app.crypto.aes import AESCrypto

        return AESCrypto(settings.CRYPTO_KEY)
    raise ValueError(f"Unknown CRYPTO_BACKEND: {backend!r}")
