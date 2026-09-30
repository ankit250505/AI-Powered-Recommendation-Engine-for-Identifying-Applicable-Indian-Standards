import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from scripts.backup_database import create_backup, prune_backups
from src.config import ROOT_DIR, load_settings
from src.monitoring import ApplicationMetrics
from src.security import LoginRateLimiter


class DeploymentTests(unittest.TestCase):
    def test_login_rate_limiter_blocks_and_resets(self):
        limiter = LoginRateLimiter(attempt_limit=2, window_seconds=300)
        limiter.record_failure("client:user")
        self.assertFalse(limiter.is_blocked("client:user"))
        limiter.record_failure("client:user")
        self.assertTrue(limiter.is_blocked("client:user"))
        limiter.reset("client:user")
        self.assertFalse(limiter.is_blocked("client:user"))

    def test_metrics_render_prometheus_counters(self):
        application_metrics = ApplicationMetrics()
        application_metrics.observe(200, 20.0)
        application_metrics.observe(503, 30.0)

        rendered = application_metrics.prometheus_text()

        self.assertIn("standards_app_requests_total 2", rendered)
        self.assertIn("standards_app_errors_total 1", rendered)
        self.assertIn("standards_app_request_duration_seconds_total 0.050000", rendered)

    def test_environment_settings_parse_security_and_paths(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "DATABASE_PATH": "runtime/app.db",
                "SESSION_COOKIE_SECURE": "true",
                "SESSION_HOURS": "12",
                "TRUSTED_HOSTS": "standards.example.in,localhost",
                "EMBEDDING_LOCAL_ONLY": "true",
            },
            clear=False,
        ):
            configured = load_settings()

        self.assertEqual(configured.environment, "production")
        self.assertEqual(configured.database_path, ROOT_DIR / "runtime" / "app.db")
        self.assertTrue(configured.session_cookie_secure)
        self.assertEqual(configured.session_hours, 12)
        self.assertEqual(configured.trusted_hosts, ("standards.example.in", "localhost"))
        self.assertTrue(configured.embedding_local_only)

    def test_sqlite_backup_is_consistent_and_retention_is_applied(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.db"
            backup_directory = root / "backups"
            with closing(sqlite3.connect(source)) as connection:
                connection.execute("CREATE TABLE records (value TEXT NOT NULL)")
                connection.execute("INSERT INTO records VALUES ('verified')")
                connection.commit()

            backup = create_backup(source, backup_directory)

            with closing(sqlite3.connect(backup)) as connection:
                value = connection.execute("SELECT value FROM records").fetchone()[0]
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            self.assertEqual(value, "verified")
            self.assertEqual(integrity, "ok")

            older = backup_directory / "recommendations-20000101T000000Z.db"
            older.touch()
            removed = prune_backups(backup_directory, keep=1)
            self.assertEqual(removed, [older])


if __name__ == "__main__":
    unittest.main()
