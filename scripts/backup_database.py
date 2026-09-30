from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT))

from src.config import settings  # noqa: E402
from src.storage import init_db  # noqa: E402


def create_backup(source: Path, backup_directory: Path) -> Path:
    if source == settings.database_path:
        init_db()
    if not source.exists():
        raise FileNotFoundError(f"Database not found: {source}")

    backup_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_directory / f"recommendations-{timestamp}.db"

    with closing(sqlite3.connect(source)) as source_connection:
        with closing(sqlite3.connect(destination)) as destination_connection:
            source_connection.backup(destination_connection)
            integrity = destination_connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Backup integrity check failed: {integrity}")
    return destination


def prune_backups(backup_directory: Path, keep: int) -> list[Path]:
    backups = sorted(backup_directory.glob("recommendations-*.db"), reverse=True)
    removed: list[Path] = []
    for backup in backups[max(keep, 1) :]:
        backup.unlink()
        removed.append(backup)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a verified online SQLite backup.")
    parser.add_argument("--database", type=Path, default=settings.database_path)
    parser.add_argument("--output", type=Path, default=ROOT / "backups")
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()

    backup = create_backup(args.database.resolve(), args.output.resolve())
    removed = prune_backups(args.output.resolve(), args.keep)
    print(f"Backup created: {backup}")
    print(f"Old backups removed: {len(removed)}")


if __name__ == "__main__":
    main()
