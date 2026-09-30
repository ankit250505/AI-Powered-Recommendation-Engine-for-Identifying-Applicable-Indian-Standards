from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    path = Path(value) if value else default
    return path if path.is_absolute() else ROOT_DIR / path


@dataclass(frozen=True)
class Settings:
    environment: str
    database_path: Path
    session_hours: int
    session_cookie_secure: bool
    log_level: str
    trusted_hosts: tuple[str, ...]
    embedding_model: str
    embedding_local_only: bool
    login_attempt_limit: int
    login_window_seconds: int


def load_settings() -> Settings:
    environment = os.getenv("APP_ENV", "development").strip().lower()
    trusted_hosts = tuple(
        host.strip()
        for host in os.getenv("TRUSTED_HOSTS", "127.0.0.1,localhost,testserver").split(",")
        if host.strip()
    )
    return Settings(
        environment=environment,
        database_path=env_path("DATABASE_PATH", ROOT_DIR / "app_data" / "recommendations.db"),
        session_hours=max(1, int(os.getenv("SESSION_HOURS", "8"))),
        session_cookie_secure=env_bool("SESSION_COOKIE_SECURE", environment == "production"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        trusted_hosts=trusted_hosts,
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
        embedding_local_only=env_bool("EMBEDDING_LOCAL_ONLY", False),
        login_attempt_limit=max(1, int(os.getenv("LOGIN_ATTEMPT_LIMIT", "5"))),
        login_window_seconds=max(30, int(os.getenv("LOGIN_WINDOW_SECONDS", "300"))),
    )


settings = load_settings()
