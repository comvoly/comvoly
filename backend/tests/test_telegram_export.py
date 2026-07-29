from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telegram_export import TelegramExportError, normalise_messages, preview_export


FIXTURE = Path(__file__).parent / "fixtures" / "telegram_small.json"


class TelegramExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_preview_inventory_is_deterministic_and_does_not_process_media(self) -> None:
        preview = preview_export(self.document)
        self.assertEqual("424242", preview.external_community_id)
        self.assertEqual(3, preview.message_count)
        self.assertEqual(1, preview.service_event_count)
        self.assertEqual(2, preview.participant_count)
        self.assertEqual(1, preview.media_count)
        self.assertEqual("2026-01-01T10:00:00+00:00", preview.history_start)

    def test_normalisation_preserves_text_reply_author_and_media_inventory(self) -> None:
        items = normalise_messages(self.document["messages"], "424242")
        self.assertEqual(["2", "3", "4"], [item.external_item_id for item in items])
        self.assertEqual("Here is the guide", items[1].body_text)
        self.assertEqual("2", items[1].reply_to_external_id)
        self.assertEqual("user2", items[1].author_external_id)
        self.assertEqual("files/guide.pdf", items[1].metadata["media"][0]["path"])

    def test_invalid_or_non_chat_export_is_explained(self) -> None:
        with self.assertRaises(TelegramExportError):
            preview_export({"name": "wrong"})
        preview = preview_export({"name": "Direct chat", "type": "personal_chat", "messages": []})
        self.assertTrue(preview.warnings)


if __name__ == "__main__":
    unittest.main()
