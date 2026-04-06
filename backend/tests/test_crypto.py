from app.utils.crypto import encrypt, decrypt


def test_encrypt_decrypt_roundtrip():
    plaintext = "sk-test-key-12345"
    encrypted = encrypt(plaintext)
    assert encrypted != plaintext
    decrypted = decrypt(encrypted)
    assert decrypted == plaintext


def test_encrypt_produces_different_output():
    plaintext = "sk-test-key-12345"
    encrypted1 = encrypt(plaintext)
    encrypted2 = encrypt(plaintext)
    # Fernet includes timestamp, so outputs differ
    assert encrypted1 != encrypted2


def test_decrypt_invalid_token():
    import pytest
    with pytest.raises(Exception):
        decrypt("not-a-valid-token")
