"""Tests for the crypto module."""

from app.security.crypto import decrypt, encrypt


def test_encrypt_decrypt() -> None:
    """Test encrypting and decrypting a secret."""
    # GIVEN a secret
    dummy_secret = "dummy_secret"  # noqa: S105
    # WHEN encrypting and then decrypting the secret
    encrypted = encrypt(dummy_secret)
    decrypted = decrypt(encrypted)
    # THEN the decrypted secret should match the original secret
    assert decrypted == dummy_secret
