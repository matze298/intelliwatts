"""Cryptography functions."""

from cryptography.fernet import Fernet

from app.config import get_settings

# Use a property or function to avoid top-level global state where possible,
# but Fernet is often used as a global instance once settings are loaded.
_settings = get_settings()
fernet = Fernet(_settings.APP_SECRET_KEY)


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
