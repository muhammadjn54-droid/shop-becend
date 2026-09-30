"""
Regression tests for the SQLite concurrency fix.

Before the fix, concurrent writes (sell / add-stock / return) raised
"OperationalError: database is locked", which surfaced to the frontend as
HTTP 500 and silently lost stock updates.

Note: Django's test runner uses an *in-memory* SQLite database, which cannot
run in WAL mode and returns non-retryable "table is locked" errors instead.
The concurrency test below therefore exercises the real file-based setup
using the exact pragmas taken from settings.DATABASES.
"""

import os
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.test import SimpleTestCase


def using_sqlite():
    return settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"


def sqlite_init_command():
    options = settings.DATABASES["default"].get("OPTIONS") or {}
    return options.get("init_command", "")


class SQLiteConcurrencySettingsTests(SimpleTestCase):
    """The SQLite fallback must be configured for safe concurrent writes."""

    def test_sqlite_options_enable_wal_and_busy_timeout(self):
        if not using_sqlite():
            self.skipTest("DATABASE_URL is configured (PostgreSQL) - not SQLite")
        options = settings.DATABASES["default"].get("OPTIONS") or {}
        init = options.get("init_command", "")
        self.assertIn("journal_mode=WAL", init)
        self.assertIn("busy_timeout", init)
        self.assertEqual(options.get("transaction_mode"), "IMMEDIATE")
        self.assertGreaterEqual(options.get("timeout", 0), 20)

    def test_vercel_fallback_uses_writable_tmp(self):
        # On Vercel without DATABASE_URL the DB must live in /tmp, not the
        # read-only bundle directory.
        if not using_sqlite():
            self.skipTest("DATABASE_URL is configured (PostgreSQL) - not SQLite")
        name = settings.DATABASES["default"]["NAME"]
        if getattr(settings, "IS_VERCEL", False):
            self.assertTrue(str(name).startswith("/tmp"), name)


class SQLiteConcurrentWriteTests(SimpleTestCase):
    """
    Proves the configured pragmas actually remove "database is locked"
    on a real file-based SQLite database (the production layout).
    """

    def test_concurrent_writers_do_not_get_database_is_locked(self):
        if not using_sqlite():
            self.skipTest("PostgreSQL handles this natively")

        init = sqlite_init_command()
        timeout = (settings.DATABASES["default"].get("OPTIONS") or {}).get("timeout", 30)

        handle, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        os.remove(path)

        def connect():
            conn = sqlite3.connect(path, timeout=timeout, isolation_level=None)
            for pragma in [p.strip() for p in init.split(";") if p.strip()]:
                conn.execute(pragma)
            return conn

        try:
            setup = sqlite3.connect(path, isolation_level=None)
            setup.execute("CREATE TABLE stock (id INTEGER PRIMARY KEY, n INTEGER NOT NULL)")
            setup.execute("INSERT INTO stock (id, n) VALUES (1, 0)")
            setup.close()

            def bump(_):
                conn = connect()
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    row = conn.execute("SELECT n FROM stock WHERE id = 1").fetchone()
                    conn.execute("UPDATE stock SET n = ? WHERE id = 1", (row[0] + 1,))
                    conn.execute("COMMIT")
                    return None
                except sqlite3.OperationalError as exc:
                    return f"{type(exc).__name__}: {exc}"
                finally:
                    conn.close()

            with ThreadPoolExecutor(max_workers=20) as pool:
                errors = [e for e in pool.map(bump, range(40)) if e]

            check = sqlite3.connect(path)
            final = check.execute("SELECT n FROM stock WHERE id = 1").fetchone()[0]
            check.close()

            self.assertEqual(errors, [], f"concurrent writes failed: {errors[:3]}")
            self.assertEqual(final, 40, "lost updates detected")
        finally:
            for suffix in ("", "-wal", "-shm"):
                try:
                    os.remove(path + suffix)
                except OSError:
                    pass
