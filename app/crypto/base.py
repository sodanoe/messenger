from abc import ABC, abstractmethod


class BaseCrypto(ABC):
    """Service-layer contract. The rest of the app never imports concrete impls."""

    @abstractmethod
    def encrypt(self, text: str, **kwargs) -> str: ...

    @abstractmethod
    def decrypt(self, text: str, **kwargs) -> str: ...
