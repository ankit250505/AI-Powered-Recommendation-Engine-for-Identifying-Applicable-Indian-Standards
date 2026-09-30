from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import settings


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DATA_DIR = ROOT_DIR / "app_data"
DATABASE_PATH = settings.database_path


@dataclass(frozen=True)
class StoredSearch:
    id: int
    query: str
    mode: str
    source_type: str
    result_count: int
    created_at: str


@dataclass(frozen=True)
class StoredSearchDetail:
    id: int
    query: str
    mode: str
    source_type: str
    source_name: str | None
    result_count: int
    results: list[dict[str, Any]]
    created_at: str


@dataclass(frozen=True)
class FeedbackAggregate:
    standard_code: str
    useful: int
    not_useful: int
    total: int


@dataclass(frozen=True)
class ReviewRecord:
    id: int
    search_id: int
    query: str
    mode: str
    source_type: str
    source_name: str | None
    standard_id: str
    standard_code: str
    decision: str
    note: str | None
    reviewer_username: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class UserRecord:
    id: int
    username: str
    password_hash: str
    password_salt: str
    role: str
    is_active: bool
    created_at: str


@dataclass(frozen=True)
class VerificationHistoryRecord:
    id: int
    standard_id: str
    previous_data: dict[str, Any]
    new_data: dict[str, Any]
    note: str
    changed_by: str
    created_at: str


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def database_health() -> dict[str, str | int]:
    init_db()
    with closing(connect()) as connection:
        result = connection.execute("PRAGMA quick_check").fetchone()[0]
        user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return {"quick_check": str(result), "users": int(user_count)}


def init_db() -> None:
    with closing(connect()) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                mode TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_name TEXT,
                result_count INTEGER NOT NULL,
                results_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('procurement', 'reviewer', 'admin')),
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS standard_overrides (
                standard_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_url TEXT NOT NULL,
                verify_status TEXT NOT NULL,
                last_reviewed TEXT NOT NULL,
                verification_note TEXT NOT NULL,
                updated_by INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(updated_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS verification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                standard_id TEXT NOT NULL,
                previous_json TEXT NOT NULL,
                new_json TEXT NOT NULL,
                note TEXT NOT NULL,
                changed_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(changed_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER,
                standard_id TEXT NOT NULL,
                standard_code TEXT NOT NULL,
                rating TEXT NOT NULL CHECK (rating IN ('useful', 'not_useful')),
                note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(search_id) REFERENCES searches(id)
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER NOT NULL,
                standard_id TEXT NOT NULL,
                standard_code TEXT NOT NULL,
                decision TEXT NOT NULL CHECK (decision IN ('accepted', 'rejected')),
                note TEXT,
                reviewer_user_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(search_id) REFERENCES searches(id),
                FOREIGN KEY(reviewer_user_id) REFERENCES users(id),
                UNIQUE(search_id, standard_id)
            );
            """
        )
        review_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(reviews)").fetchall()
        }
        if "reviewer_user_id" not in review_columns:
            connection.execute("ALTER TABLE reviews ADD COLUMN reviewer_user_id INTEGER")
        connection.commit()


def save_search(
    query: str,
    mode: str,
    source_type: str,
    source_name: str | None,
    results: list[dict[str, Any]],
) -> int:
    init_db()
    with closing(connect()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO searches (query, mode, source_type, source_name, result_count, results_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query,
                mode,
                source_type,
                source_name,
                len(results),
                json.dumps(results),
                utc_now(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def save_feedback(
    search_id: int | None,
    standard_id: str,
    standard_code: str,
    rating: str,
    note: str | None = None,
) -> int:
    init_db()
    with closing(connect()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO feedback (search_id, standard_id, standard_code, rating, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (search_id, standard_id, standard_code, rating, note, utc_now()),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_searches(limit: int = 20) -> list[StoredSearch]:
    init_db()
    with closing(connect()) as connection:
        rows = connection.execute(
            """
            SELECT id, query, mode, source_type, result_count, created_at
            FROM searches
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        StoredSearch(
            id=row["id"],
            query=row["query"],
            mode=row["mode"],
            source_type=row["source_type"],
            result_count=row["result_count"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_search(search_id: int) -> StoredSearchDetail | None:
    init_db()
    with closing(connect()) as connection:
        row = connection.execute(
            """
            SELECT id, query, mode, source_type, source_name, result_count, results_json, created_at
            FROM searches
            WHERE id = ?
            """,
            (search_id,),
        ).fetchone()

    if row is None:
        return None

    return StoredSearchDetail(
        id=row["id"],
        query=row["query"],
        mode=row["mode"],
        source_type=row["source_type"],
        source_name=row["source_name"],
        result_count=row["result_count"],
        results=json.loads(row["results_json"]),
        created_at=row["created_at"],
    )


def feedback_summary() -> dict[str, int]:
    init_db()
    with closing(connect()) as connection:
        rows = connection.execute(
            """
            SELECT rating, COUNT(*) AS count
            FROM feedback
            GROUP BY rating
            """
        ).fetchall()
    summary = {"useful": 0, "not_useful": 0}
    for row in rows:
        summary[row["rating"]] = row["count"]
    return summary


def count_searches() -> int:
    init_db()
    with closing(connect()) as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM searches").fetchone()
    return int(row["count"])


def feedback_by_standard(limit: int = 10) -> list[FeedbackAggregate]:
    init_db()
    with closing(connect()) as connection:
        rows = connection.execute(
            """
            SELECT
                standard_code,
                SUM(CASE WHEN rating = 'useful' THEN 1 ELSE 0 END) AS useful,
                SUM(CASE WHEN rating = 'not_useful' THEN 1 ELSE 0 END) AS not_useful,
                COUNT(*) AS total
            FROM feedback
            GROUP BY standard_code
            ORDER BY total DESC, useful DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        FeedbackAggregate(
            standard_code=row["standard_code"],
            useful=int(row["useful"] or 0),
            not_useful=int(row["not_useful"] or 0),
            total=int(row["total"] or 0),
        )
        for row in rows
    ]


def save_review(
    search_id: int,
    standard_id: str,
    standard_code: str,
    decision: str,
    reviewer_user_id: int,
    note: str | None = None,
) -> int:
    init_db()
    timestamp = utc_now()
    with closing(connect()) as connection:
        connection.execute(
            """
            INSERT INTO reviews (
                search_id, standard_id, standard_code, decision, note, reviewer_user_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(search_id, standard_id) DO UPDATE SET
                standard_code = excluded.standard_code,
                decision = excluded.decision,
                note = excluded.note,
                reviewer_user_id = excluded.reviewer_user_id,
                updated_at = excluded.updated_at
            """,
            (
                search_id,
                standard_id,
                standard_code,
                decision,
                note,
                reviewer_user_id,
                timestamp,
                timestamp,
            ),
        )
        row = connection.execute(
            "SELECT id FROM reviews WHERE search_id = ? AND standard_id = ?",
            (search_id, standard_id),
        ).fetchone()
        connection.commit()
    return int(row["id"])


def review_summary() -> dict[str, int]:
    init_db()
    with closing(connect()) as connection:
        decision_rows = connection.execute(
            "SELECT decision, COUNT(*) AS count FROM reviews GROUP BY decision"
        ).fetchall()
        recommendation_row = connection.execute(
            "SELECT COALESCE(SUM(result_count), 0) AS count FROM searches"
        ).fetchone()

    summary = {"accepted": 0, "rejected": 0, "reviewed": 0, "pending": 0}
    for row in decision_rows:
        summary[row["decision"]] = int(row["count"])
    summary["reviewed"] = summary["accepted"] + summary["rejected"]
    summary["pending"] = max(0, int(recommendation_row["count"]) - summary["reviewed"])
    return summary


def list_reviews(limit: int = 20) -> list[ReviewRecord]:
    init_db()
    with closing(connect()) as connection:
        rows = connection.execute(
            """
            SELECT
                reviews.id,
                reviews.search_id,
                searches.query,
                searches.mode,
                searches.source_type,
                searches.source_name,
                reviews.standard_id,
                reviews.standard_code,
                reviews.decision,
                reviews.note,
                users.username AS reviewer_username,
                reviews.created_at,
                reviews.updated_at
            FROM reviews
            JOIN searches ON searches.id = reviews.search_id
            LEFT JOIN users ON users.id = reviews.reviewer_user_id
            ORDER BY reviews.updated_at DESC, reviews.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [ReviewRecord(**dict(row)) for row in rows]


def create_user(
    username: str,
    password_hash: str,
    password_salt: str,
    role: str,
) -> UserRecord:
    init_db()
    with closing(connect()) as connection:
        try:
            cursor = connection.execute(
                """
                INSERT INTO users (username, password_hash, password_salt, role, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, password_hash, password_salt, role, utc_now()),
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            raise ValueError(f"User '{username}' already exists.") from error
        user_id = int(cursor.lastrowid)
    user = get_user_by_id(user_id)
    if user is None:
        raise RuntimeError("Created user could not be loaded.")
    return user


def get_user_by_id(user_id: int) -> UserRecord | None:
    init_db()
    with closing(connect()) as connection:
        row = connection.execute(
            """
            SELECT id, username, password_hash, password_salt, role, is_active, created_at
            FROM users WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return UserRecord(**{**dict(row), "is_active": bool(row["is_active"])}) if row else None


def get_user_by_username(username: str) -> UserRecord | None:
    init_db()
    with closing(connect()) as connection:
        row = connection.execute(
            """
            SELECT id, username, password_hash, password_salt, role, is_active, created_at
            FROM users WHERE username = ? COLLATE NOCASE
            """,
            (username,),
        ).fetchone()
    return UserRecord(**{**dict(row), "is_active": bool(row["is_active"])}) if row else None


def save_session(user_id: int, token_hash: str, expires_at: str) -> None:
    init_db()
    with closing(connect()) as connection:
        connection.execute(
            "INSERT INTO sessions (user_id, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (user_id, token_hash, expires_at, utc_now()),
        )
        connection.commit()


def get_user_by_session(token_hash: str) -> UserRecord | None:
    init_db()
    with closing(connect()) as connection:
        row = connection.execute(
            """
            SELECT users.id, users.username, users.password_hash, users.password_salt,
                   users.role, users.is_active, users.created_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ? AND users.is_active = 1
            """,
            (token_hash, utc_now()),
        ).fetchone()
    return UserRecord(**{**dict(row), "is_active": bool(row["is_active"])}) if row else None


def delete_session(token_hash: str) -> None:
    init_db()
    with closing(connect()) as connection:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        connection.commit()


def get_standard_overrides() -> dict[str, dict[str, str]]:
    init_db()
    with closing(connect()) as connection:
        rows = connection.execute(
            """
            SELECT standard_id, title, source_url, verify_status, last_reviewed,
                   verification_note, updated_at
            FROM standard_overrides
            """
        ).fetchall()
    return {row["standard_id"]: dict(row) for row in rows}


def save_standard_override(
    standard_id: str,
    previous_data: dict[str, str],
    new_data: dict[str, str],
    note: str,
    user_id: int,
) -> None:
    init_db()
    timestamp = utc_now()
    with closing(connect()) as connection:
        connection.execute(
            """
            INSERT INTO standard_overrides (
                standard_id, title, source_url, verify_status, last_reviewed,
                verification_note, updated_by, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(standard_id) DO UPDATE SET
                title = excluded.title,
                source_url = excluded.source_url,
                verify_status = excluded.verify_status,
                last_reviewed = excluded.last_reviewed,
                verification_note = excluded.verification_note,
                updated_by = excluded.updated_by,
                updated_at = excluded.updated_at
            """,
            (
                standard_id,
                new_data["title"],
                new_data["source_url"],
                new_data["verify_status"],
                new_data["last_reviewed"],
                note,
                user_id,
                timestamp,
            ),
        )
        connection.execute(
            """
            INSERT INTO verification_history (
                standard_id, previous_json, new_json, note, changed_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                standard_id,
                json.dumps(previous_data),
                json.dumps(new_data),
                note,
                user_id,
                timestamp,
            ),
        )
        connection.commit()


def list_verification_history(limit: int = 50) -> list[VerificationHistoryRecord]:
    init_db()
    with closing(connect()) as connection:
        rows = connection.execute(
            """
            SELECT verification_history.id, verification_history.standard_id,
                   verification_history.previous_json, verification_history.new_json,
                   verification_history.note, users.username AS changed_by,
                   verification_history.created_at
            FROM verification_history
            JOIN users ON users.id = verification_history.changed_by
            ORDER BY verification_history.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        VerificationHistoryRecord(
            id=row["id"],
            standard_id=row["standard_id"],
            previous_data=json.loads(row["previous_json"]),
            new_data=json.loads(row["new_json"]),
            note=row["note"],
            changed_by=row["changed_by"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
