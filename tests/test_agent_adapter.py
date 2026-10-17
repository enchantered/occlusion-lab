import asyncio
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from projects.reviewgate.agent_adapter import (
    DraftOutputError, generate_draft, prepare_input, validate_output,
)
from projects.reviewgate.core import ReviewStore, fingerprint


class FakeRunner:
    def __init__(self, output=None, error=None):
        self.output, self.error, self.calls = output, error, []

    async def run(self, text, **kwargs):
        self.calls.append((text, kwargs))
        if self.error:
            raise self.error
        return SimpleNamespace(final_output=self.output)


class FakeStore:
    def __init__(self):
        self.items = []

    def create_draft(self, source, draft):
        self.items.append((source, draft))
        return "draft-id"


class AgentAdapterTests(unittest.TestCase):
    def test_network_flag_fails_closed_before_any_redaction_or_runner(self):
        runner = FakeRunner({"draft": "ok", "uncertainties": []})
        with self.assertRaisesRegex(PermissionError, "privacy"):
            asyncio.run(generate_draft("raw", model="test-model", allow_network=False, runner=runner))
        self.assertEqual(runner.calls, [])

    def test_sanitized_text_sent_but_original_source_and_reviewable_string_stored(self):
        runner = FakeRunner({"draft": "Reply draft", "uncertainties": ["Date unclear", "Need confirmation"]})
        store = FakeStore()
        seen = []

        def redact(text):
            seen.append(text)
            return {"text": "[REDACTED] review", "findings": ["email"]}

        result = asyncio.run(generate_draft(
            "raw email@example.com", model="model-explicit", allow_network=True,
            redact_fn=redact, runner=runner, store=store,
        ))
        self.assertEqual(seen, ["raw email@example.com"])
        self.assertEqual(runner.calls[0][0], "[REDACTED] review")
        self.assertEqual(runner.calls[0][1], {"model": "model-explicit", "max_turns": 2, "max_tokens": 900})
        self.assertEqual(result, "draft-id")
        self.assertEqual(store.items, [("raw email@example.com", "Reply draft\n\nUncertainties:\n- Date unclear\n- Need confirmation")])

    def test_real_reviewstore_pending_source_hash_audit_and_no_export(self):
        source = "Actual customer review: order delayed"
        runner = FakeRunner({"draft": "We are sorry about the delay.", "uncertainties": ["Delivery date unknown"]})
        with tempfile.TemporaryDirectory() as tmp:
            store = ReviewStore(Path(tmp) / "reviewgate.sqlite")
            draft_id = asyncio.run(generate_draft(
                source, model="offline-test", allow_network=True,
                redact_fn=lambda text: {"text": text, "findings": []},
                runner=runner, store=store,
            ))
            with store._connect() as db:
                row = db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
                audit = db.execute("SELECT event FROM audit").fetchall()
            self.assertIsNotNone(row)
            self.assertEqual(row["status"], "pending")
            self.assertEqual(row["source_hash"], fingerprint(source))
            self.assertEqual(hashlib.sha256(source.encode()).hexdigest(), row["source_hash"])
            self.assertEqual(row["draft"], "We are sorry about the delay.\n\nUncertainties:\n- Delivery date unknown")
            self.assertTrue(store.verify_audit())
            self.assertEqual(len(audit), 1)
            self.assertNotIn("approved", audit[0]["event"])
            self.assertNotIn("export", audit[0]["event"])
            with self.assertRaises(Exception):
                store.export_approved(draft_id)

    def test_missing_store_fails_before_runner_or_redaction(self):
        runner = FakeRunner({"draft": "ok", "uncertainties": []})
        redact_calls = []
        with self.assertRaisesRegex(RuntimeError, "ReviewStore instance required"):
            asyncio.run(generate_draft("raw", model="m", allow_network=True,
                redact_fn=lambda text: redact_calls.append(text) or {"text": text}, runner=runner))
        self.assertEqual(runner.calls, [])
        self.assertEqual(redact_calls, [])

    def test_model_must_be_explicit(self):
        with self.assertRaisesRegex(ValueError, "explicit"):
            asyncio.run(generate_draft("text", model=" ", allow_network=True))

    def test_bad_outputs_rejected_and_not_stored(self):
        for output in ({"draft": " ", "uncertainties": []},
                       {"draft": "x", "uncertainties": "none"},
                       {"draft": "x", "uncertainties": ["y"] * 21}):
            store = FakeStore()
            with self.subTest(output=output), self.assertRaises(DraftOutputError):
                asyncio.run(generate_draft("raw", model="m", allow_network=True,
                    redact_fn=lambda _: {"text": "safe", "findings": []}, runner=FakeRunner(output), store=store))
            self.assertEqual(store.items, [])

    def test_run_failure_propagates_without_saving(self):
        store = FakeStore()
        with self.assertRaisesRegex(RuntimeError, "offline failure"):
            asyncio.run(generate_draft("raw", model="m", allow_network=True,
                redact_fn=lambda _: {"text": "safe", "findings": []},
                runner=FakeRunner(error=RuntimeError("offline failure")), store=store))
        self.assertEqual(store.items, [])

    def test_helpers_enforce_blank_and_length(self):
        with self.assertRaises(ValueError):
            prepare_input("  ", lambda _: {"text": ""})
        with self.assertRaises(DraftOutputError):
            validate_output({"draft": "x" * 12001, "uncertainties": []})

    def test_sdk_import_is_lazy_and_missing_sdk_has_clean_message(self):
        with patch("projects.reviewgate.agent_adapter._sdk_types", side_effect=RuntimeError("Optional dependencies missing. Install with: pip install -r requirements-agent.in")):
            with self.assertRaisesRegex(RuntimeError, "requirements-agent.in"):
                asyncio.run(generate_draft("raw", model="m", allow_network=True,
                    redact_fn=lambda _: {"text": "safe", "findings": []}, store=FakeStore()))


if __name__ == "__main__":
    unittest.main()
