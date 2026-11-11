import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from app.core.config import get_settings

_ph = PasswordHasher()
_DUMMY = _ph.hash("khong-dung-de-dang-nhap")


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(pw: str, hashed: str | None) -> bool:
    try:
        return _ph.verify(hashed or _DUMMY, pw) and hashed is not None
    except (VerifyMismatchError, InvalidHashError):
        return False


def temp_password() -> str:
    return secrets.token_urlsafe(9) + "@1a"


def make_token(user_id: int, token_version: int) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "tv": token_version, "iat": now, "exp": now + timedelta(minutes=s.JWT_TTL_MINUTES)}
    return jwt.encode(payload, s.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().JWT_SECRET, algorithms=["HS256"])
