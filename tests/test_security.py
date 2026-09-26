# -*- coding: utf-8 -*-
"""Тест 3 — механізм авторизації: хешування паролів і токени сеансу."""
from server.security import create_token, decode_token, hash_password, verify_password


def test_password_hash_is_not_plain_text():
    """Пароль ніколи не зберігається у відкритому вигляді."""
    stored = hash_password("qwerty123")
    assert "qwerty123" not in stored
    assert stored.startswith("pbkdf2_sha256$")


def test_verify_correct_and_wrong_password():
    stored = hash_password("qwerty123")
    assert verify_password("qwerty123", stored) is True
    assert verify_password("qwerty124", stored) is False


def test_same_password_gives_different_hashes():
    """Різна сіль — різні хеші для однакових паролів."""
    assert hash_password("qwerty123") != hash_password("qwerty123")


def test_token_roundtrip():
    token = create_token(user_id=7, login="sofiia")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == 7 and payload["login"] == "sofiia"


def test_tampered_token_is_rejected():
    """Підроблений токен не проходить перевірку підпису."""
    token = create_token(user_id=7, login="sofiia")
    payload_b64, signature = token.split(".")
    assert decode_token(f"{payload_b64}.{signature[:-2]}xx") is None


def test_expired_token_is_rejected():
    assert decode_token(create_token(1, "sofiia", ttl_minutes=-1)) is None
