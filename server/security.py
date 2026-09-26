# -*- coding: utf-8 -*-
"""Хешування паролів (PBKDF2-SHA256) і підписані токени сеансу (HMAC).

Використано лише стандартну бібліотеку — менше залежностей, простіше
пояснити роботу механізму на захисті.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from server.config import SECRET_KEY, TOKEN_TTL_MINUTES

_ITERATIONS = 200_000


# ------------------------------------------------------------------ паролі
def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        _ITERATIONS, base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"),
            base64.b64decode(salt_b64), int(iterations))
        return hmac.compare_digest(digest, base64.b64decode(digest_b64))
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------------ токени
def _sign(payload_b64: str) -> str:
    signature = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"),
                         hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).decode().rstrip("=")


def create_token(user_id: int, login: str, ttl_minutes: int = TOKEN_TTL_MINUTES) -> str:
    payload = {"sub": user_id, "login": login, "exp": int(time.time()) + ttl_minutes * 60}
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode("utf-8")).decode().rstrip("=")
    return f"{payload_b64}.{_sign(payload_b64)}"


def decode_token(token: str) -> Optional[dict]:
    """Повертає payload або None, якщо підпис невірний чи строк дії минув."""
    try:
        payload_b64, signature = token.split(".")
    except ValueError:
        return None
    if not hmac.compare_digest(_sign(payload_b64), signature):
        return None
    padding = "=" * (-len(payload_b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
    except (ValueError, TypeError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload
