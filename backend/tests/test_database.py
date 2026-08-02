from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from database import connect_database, create_schema, query, uses_postgres


class DatabaseTests(unittest.TestCase):
    def test_postgres_mode_converts_parameter_markers(self) -> None:
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://example.invalid/test"}):
            self.assertTrue(uses_postgres())
            self.assertEqual(query("SELECT * FROM messages WHERE id = ?"), "SELECT * FROM messages WHERE id = %s")

    def test_postgres_mode_escapes_literal_percent_signs(self) -> None:
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://example.invalid/test"}):
            self.assertEqual(
                query("SELECT checkpoint_key FROM import_checkpoints "
                      "WHERE job_id=? AND checkpoint_key LIKE 'chunk:%'"),
                "SELECT checkpoint_key FROM import_checkpoints "
                "WHERE job_id=%s AND checkpoint_key LIKE 'chunk:%%'",
            )

    def test_shared_schema_is_created_in_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"DATABASE_URL": ""}):
            path = Path(directory) / "archive.db"
            with connect_database(path) as database:
                create_schema(database)
                tables = {
                    row[0]
                    for row in database.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            self.assertTrue({"communities", "messages", "sync_runs"}.issubset(tables))
            self.assertNotIn("accounts", tables)


if __name__ == "__main__":
    unittest.main()
