from __future__ import annotations

import sqlite3
import os
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import search_server


class SearchServerDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "comvoly.db"
        with closing(sqlite3.connect(self.database_path)) as database:
            database.executescript(
                """
                CREATE TABLE communities (id INTEGER PRIMARY KEY, title TEXT, source_type TEXT, imported_at TEXT);
                CREATE TABLE messages (id INTEGER PRIMARY KEY, community_id INTEGER, telegram_message_id INTEGER,
                    sender_telegram_id TEXT, sent_at TEXT, text TEXT, has_media INTEGER);
                CREATE TABLE sync_runs (id INTEGER PRIMARY KEY, finished_at TEXT, status TEXT);
                INSERT INTO communities VALUES (1, 'Test Community', 'Channel', '2026-07-27T10:00:00+00:00');
                INSERT INTO messages VALUES (7, 1, 42, '123', '2026-07-27T11:00:00+00:00', 'A useful community answer', 0);
                INSERT INTO sync_runs VALUES (1, '2026-07-27T12:00:00+00:00', 'success');
                """
            )
        self.path_patch = patch.object(search_server, "DATABASE_PATH", self.database_path)
        self.path_patch.start()

    def tearDown(self) -> None:
        self.path_patch.stop()
        self.temporary_directory.cleanup()

    def test_status_summary(self) -> None:
        summary = search_server.status_summary()
        self.assertEqual(summary["community_count"], 1)
        self.assertEqual(summary["message_count"], 1)
        self.assertEqual(summary["last_successful_sync"], "2026-07-27T12:00:00+00:00")

    def test_search_and_get_message(self) -> None:
        results = search_server.search_messages("useful")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], 7)
        message = search_server.get_message(7)
        self.assertIsNotNone(message)
        self.assertEqual(message["telegram_message_id"], 42)
        self.assertIsNone(search_server.get_message(999))

    def test_ai_health_flag_requires_both_gate_and_server_key(self) -> None:
        with patch.dict(os.environ, {
                "COMVOLY_AI_INTERPRETATION_ENABLED": "true", "OPENAI_API_KEY": "test-key"}):
            self.assertTrue(search_server.ai_interpretation_configured())
        with patch.dict(os.environ, {
                "COMVOLY_AI_INTERPRETATION_ENABLED": "false", "OPENAI_API_KEY": "test-key"}):
            self.assertFalse(search_server.ai_interpretation_configured())


if __name__ == "__main__":
    unittest.main()
