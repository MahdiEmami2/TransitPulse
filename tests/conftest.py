"""Shared pytest configuration.

The suite runs against the documented SQLite development fallback so it does
not require a running PostgreSQL server or Docker.
"""
import os
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="transitpulse-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DIR}/test.db"
os.environ["MODEL_PATH"] = f"{_TMP_DIR}/latest.pkl"
