"""Password hashing (argon2id via pwdlib) and JWT access tokens (HS256 via pyjwt)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

settings = get_settings()

_password_hash = PasswordHash((Argon2Hasher(),))

# Verified against when the email does not exist, so a wrong email takes about as long
# as a wrong password (the response time must not reveal which accounts exist).
_DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, password_hash)


@dataclass(frozen=True)
class AccessToken:
    token: str
    expires_in: int  # seconds


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> AccessToken:
    lifetime = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + lifetime}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return AccessToken(token=token, expires_in=int(lifetime.total_seconds()))


def decode_access_token(token: str) -> int:
    """Return the user id in the token, or raise UnauthorizedError."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired") from None
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid token") from None

    try:
        return int(payload["sub"])
    except (TypeError, ValueError):
        raise UnauthorizedError("Invalid token") from None
