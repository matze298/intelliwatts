"""Cryptography functions."""

from cryptography.fernet import Fernet

from app.config import GLOBAL_SETTINGS

fernet = Fernet(GLOBAL_SETTINGS.APP_SECRET_KEY)


def encrypt(secret: str) -> bytes:
    """Ecnodes a secret using the app secret key.

    Returns:
        The encrypted secret.
    """
    return fernet.encrypt(secret.encode())


def decrypt(secret: bytes) -> str:
    """Decodes a secret using the app secret key.

    Returns:
        The decrypted secret.
    """
    return fernet.decrypt(secret).decode()
