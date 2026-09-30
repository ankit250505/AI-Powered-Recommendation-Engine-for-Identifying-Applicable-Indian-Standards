from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from src.config import settings
from src.storage import (
    UserRecord,
    create_user,
    delete_session,
    get_user_by_session,
    get_user_by_username,
    save_session,
)


PASSWORD_ITERATIONS = 600_000


def hash_password(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return base64.b64encode(digest).decode("ascii")


def create_user_account(username: str, password: str, role: str) -> UserRecord:
    normalized_username = username.strip()
    if len(normalized_username) < 3:
        raise ValueError("Username must contain at least 3 characters.")
    if len(password) < 10:
        raise ValueError("Password must contain at least 10 characters.")
    if role not in {"procurement", "reviewer", "admin"}:
        raise ValueError("Role must be procurement, reviewer, or admin.")

    salt = secrets.token_bytes(16)
    return create_user(
        username=normalized_username,
        password_hash=hash_password(password, salt),
        password_salt=base64.b64encode(salt).decode("ascii"),
        role=role,
    )


def authenticate_user(username: str, password: str) -> UserRecord | None:
    user = get_user_by_username(username.strip())
    if user is None or not user.is_active:
        return None
    salt = base64.b64decode(user.password_salt.encode("ascii"))
    candidate = hash_password(password, salt)
    return user if hmac.compare_digest(candidate, user.password_hash) else None


def session_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user_session(user_id: int) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    max_age = settings.session_hours * 60 * 60
    expires_at = (datetime.now(UTC) + timedelta(seconds=max_age)).isoformat(timespec="seconds")
    save_session(user_id=user_id, token_hash=session_hash(token), expires_at=expires_at)
    return token, max_age


def user_for_session(token: str) -> UserRecord | None:
    return get_user_by_session(session_hash(token))


def end_user_session(token: str) -> None:
    delete_session(session_hash(token))
