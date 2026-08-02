from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authorization import Principal
from database import connect_database, create_schema
from v2_store import ComvolyStore
from workspace_application import WorkspaceApplication
from workspace_intelligence import (
    Interpretation,
    OpenAIEvidenceInterpreter,
    WorkspaceIntelligence,
)


class RecordingInterpreter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[dict[str, object]], str]] = []

    def interpret(self, question: str, evidence: list[dict[str, object]],
                  safety_identifier: str) -> Interpretation:
        self.calls.append((question, evidence, safety_identifier))
        return Interpretation(
            "The discussion is critical of Tesla drivers, but it is mostly humour [E1].",
            [1], "test-model", input_tokens=120, output_tokens=24)


class FakeResponses:
    def __init__(self) -> None:
        self.request: dict[str, object] = {}

    def create(self, **kwargs: object) -> object:
        self.request = kwargs
        return SimpleNamespace(
            output_text="A cited synthesis [E2].",
            usage=SimpleNamespace(input_tokens=75, output_tokens=9),
        )


class InvalidCitationInterpreter:
    def interpret(self, question: str, evidence: list[dict[str, object]],
                  safety_identifier: str) -> Interpretation:
        return Interpretation("An unsupported claim [E99].", [99], "test-model")


class WorkspaceIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "intelligence.db"
        self.environment = patch.dict(os.environ, {
            "DATABASE_URL": "", "COMVOLY_ENABLE_V2_SCHEMA": "true",
            "COMVOLY_AI_INTERPRETATION_ENABLED": "false",
        })
        self.environment.start()
        self.database_context = connect_database(self.path)
        self.database = self.database_context.__enter__()
        create_schema(self.database)
        self.store = ComvolyStore(self.database)
        self.owner_a = Principal(self.store.create_account("Owner A", "acct_a"))
        self.owner_b = Principal(self.store.create_account("Owner B", "acct_b"))
        self.workspace_a = self.store.create_workspace(self.owner_a, "Alpha", "alpha", "ws_a")
        self.workspace_b = self.store.create_workspace(self.owner_b, "Beta", "beta", "ws_b")
        self.context_a = self.store.context(self.owner_a, self.workspace_a, "manage_sources")
        self.context_b = self.store.context(self.owner_b, self.workspace_b, "manage_sources")
        for workspace_id, source_id in (("ws_a", "src_a"), ("ws_b", "src_b")):
            self.store.create_source(
                self.context_a if workspace_id == "ws_a" else self.context_b,
                "telegram", f"chat-{workspace_id}", workspace_id, source_id)

    def tearDown(self) -> None:
        self.database_context.__exit__(None, None, None)
        self.environment.stop()
        self.temp.cleanup()

    def add(self, workspace: str, source: str, external_id: str, body: str,
            created: str) -> None:
        context = self.context_a if workspace == "ws_a" else self.context_b
        self.store.add_content(context, source, external_id, body, created)

    def test_generic_question_words_do_not_rank_unrelated_messages(self) -> None:
        self.add("ws_a", "src_a", "1", "Comvoly pilot notice for this community", "2026-08-02T12:00:00Z")
        self.add("ws_a", "src_a", "2", "I sent the same note to my mortgage adviser", "2026-08-02T11:00:00Z")
        self.add("ws_a", "src_a", "3", "Tesla drivers always defend the charging network", "2026-08-01T10:00:00Z")
        self.add("ws_a", "src_a", "4", "Are you saying Tesla owners are all the same?", "2026-08-01T09:00:00Z")
        context = self.store.context(self.owner_a, "ws_a", "use_intelligence")
        results = WorkspaceIntelligence(self.database).retrieve(
            context, "What does the community think of Tesla drivers?", 12)
        self.assertEqual(["3", "4"], [item["external_item_id"] for item in results])

    def test_ai_interpretation_is_cited_scoped_and_usage_limited(self) -> None:
        self.add("ws_a", "src_a", "1", "Tesla drivers defend the charging network", "2026-08-01T10:00:00Z")
        self.add("ws_a", "src_a", "2", "The next reply was clearly a joke", "2026-08-01T10:01:00Z")
        self.add("ws_b", "src_b", "1", "Beta Tesla material must remain private", "2026-08-01T10:00:00Z")
        for workspace_id, source_id, conversation_id in (
                ("ws_a", "src_a", "conv_a"), ("ws_b", "src_b", "conv_b")):
            self.database.execute("""INSERT INTO conversations
                (id, workspace_id, source_connection_id, external_conversation_id,
                 conversation_type, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'chat', 'Test', ?, ?)""",
                (conversation_id, workspace_id, source_id, conversation_id,
                 "2026-08-01T09:00:00Z", "2026-08-01T09:00:00Z"))
            self.database.execute("""UPDATE content_items SET conversation_id=?
                WHERE workspace_id=? AND source_connection_id=?""",
                (conversation_id, workspace_id, source_id))
        interpreter = RecordingInterpreter()
        intelligence = WorkspaceIntelligence(self.database, interpreter)
        application = WorkspaceApplication(self.database, intelligence=intelligence)
        with patch.dict(os.environ, {"COMVOLY_AI_MONTHLY_QUESTION_LIMIT": "1"}):
            first = application.ask(self.owner_a, "ws_a", {
                "question": "What do Tesla drivers think?"})
            second = application.ask(self.owner_a, "ws_a", {
                "question": "What do Tesla drivers think?"})

        self.assertEqual("ai_interpretation", first["mode"])
        self.assertEqual("E1", first["citations"][0]["evidence_label"])
        self.assertEqual("ranked_evidence", second["mode"])
        self.assertEqual(1, len(interpreter.calls))
        supplied = repr(interpreter.calls[0][1])
        self.assertIn("charging network", supplied)
        self.assertIn("clearly a joke", supplied)
        self.assertNotIn("Beta Tesla", supplied)
        self.assertTrue(interpreter.calls[0][2].startswith("cv_"))
        usage = {row["metric"]: row["quantity"] for row in self.database.execute(
            "SELECT metric, quantity FROM usage_counters WHERE workspace_id='ws_a'").fetchall()}
        self.assertEqual(1, usage["ai_interpretations"])
        self.assertEqual(120, usage["ai_input_tokens"])
        self.assertEqual(24, usage["ai_output_tokens"])
        self.assertEqual(2, usage["intelligence_questions"])

    def test_openai_adapter_is_stateless_bounded_and_parses_valid_citations(self) -> None:
        responses = FakeResponses()
        client = SimpleNamespace(responses=responses)
        adapter = OpenAIEvidenceInterpreter(
            client, model="gpt-5.6-luna", reasoning_effort="none", max_output_tokens=500)
        evidence = [
            {"source_created_at": "2026-08-01", "author_display_name": "A", "body_text": "First"},
            {"source_created_at": "2026-08-02", "author_display_name": "B", "body_text": "Second"},
        ]
        result = adapter.interpret("What happened?", evidence, "cv_safe")
        self.assertEqual([2], result.citation_indexes)
        self.assertEqual((75, 9), (result.input_tokens, result.output_tokens))
        self.assertEqual(False, responses.request["store"])
        self.assertEqual("cv_safe", responses.request["safety_identifier"])
        self.assertEqual({"verbosity": "low"}, responses.request["text"])
        self.assertNotIn("Beta", str(responses.request["input"]))

    def test_invalid_model_citation_cannot_be_presented_as_interpretation(self) -> None:
        self.add("ws_a", "src_a", "1", "Tesla drivers discussed charging", "2026-08-01T10:00:00Z")
        context = self.store.context(self.owner_a, "ws_a", "use_intelligence")
        result = WorkspaceIntelligence(self.database, InvalidCitationInterpreter()).answer(
            context, "What did Tesla drivers discuss?")
        self.assertEqual("ranked_evidence", result["mode"])
        self.assertNotIn("unsupported claim", result["answer"])
        self.assertEqual("E1", result["citations"][0]["evidence_label"])


if __name__ == "__main__":
    unittest.main()
