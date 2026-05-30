"""Password hashing and JWT access tokens (auth-api patterns, distilled).

Uses the ``bcrypt`` library directly rather than passlib — modern bcrypt (4.x)
is incompatible with passlib's backend probing, and the direct API is simpler.
bcrypt only considers the first 72 bytes of a password, so we truncate to that.
"""

from __future__ import annotations

from datetime import timedelta

import bcrypt
from jose import JWTError, jwt

from .config import get_settings
from .models import utcnow

_ALGO = "HS256"
_BCRYPT_MAX = 72  # bcrypt ignores bytes beyond this; truncate to avoid errors


def _encode(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_encode(password), password_hash.encode("ascii"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = utcnow() + timedelta(seconds=settings.access_token_seconds)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGO)


def decode_token(token: str) -> str | None:
    """Return the token's subject (username), or None if invalid/expired."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGO])
    except JWTError:
        return None
    return payload.get("sub")
