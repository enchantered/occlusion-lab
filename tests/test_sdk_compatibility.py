"""Exercise the actual optional SDK runner with a no-network synthetic model."""
import asyncio
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from projects.reviewgate import ReviewError, ReviewStore
from projects.reviewgate import agent_adapter

try:
    from agents import Agent, Model, ModelResponse, Usage
    from openai.types.responses import ResponseOutputMessage, ResponseOutputText
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


if SDK_AVAILABLE:
    class OfflineModel(Model):
        def __init__(self, payload):
            self.payload = payload
            self.calls = []

        async def get_response(self, system_instructions, input, model_settings,
                               tools, output_schema, handoffs, tracing, **kwargs):
            self.calls.append({"input": input, "tools": tools, "handoffs": handoffs,
                               "schema": output_schema, "settings": model_settings,
                               "tracing_disabled": tracing.is_disabled()})
            return ModelResponse(output=[ResponseOutputMessage(
                id="synthetic-message", role="assistant", status="completed", type="message",
                content=[ResponseOutputText(type="output_text", text=json.dumps(self.payload),
                                            annotations=[])],
            )], usage=Usage(), response_id="synthetic-response")

        async def stream_response(self, *args, **kwargs):
            raise AssertionError("Streaming is not used by this adapter")
            yield  # Required async-generator shape; deliberately unreachable.


@unittest.skipUnless(SDK_AVAILABLE, "Optional Agents SDK not installed")
class SDKCompatibilityTests(unittest.TestCase):
    def generate(self, store, model):
        real_types = agent_adapter._sdk_types()

        def offline_agent(**kwargs):
            self.assertEqual(kwargs["model"], "offline-synthetic")
            kwargs["model"] = model
            return Agent(**kwargs)

        replacement = (offline_agent,) + real_types[1:]
        # A real Runner, real typed schema and real persistence; no external traffic.
        with patch.object(agent_adapter, "_sdk_types", return_value=replacement), \
                patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            return asyncio.run(agent_adapter.generate_draft(
                "Synthetic brief for person@example.com", model="offline-synthetic",
                allow_network=True, store=store,
            ))

    def test_actual_runner_typed_output_redaction_and_pending_gate(self):
        model = OfflineModel({"draft": "Synthetic brief", "uncertainties": ["Confirm date"]})
        with tempfile.TemporaryDirectory() as tmp:
            store = ReviewStore(Path(tmp) / "review.sqlite")
            ident = self.generate(store, model)
            info = store.inspect_draft(ident)
            self.assertEqual(info["status"], "pending")
            self.assertIn("Confirm date", info["draft"])
            with self.assertRaises(ReviewError):
                store.export_approved(ident)
            self.assertTrue(store.verify_audit())
        self.assertEqual(len(model.calls), 1)
        call = model.calls[0]
        self.assertNotIn("person@example.com", str(call["input"]))
        self.assertIn("REDACTED:EMAIL", str(call["input"]))
        self.assertEqual((call["tools"], call["handoffs"]), ([], []))
        self.assertIsNotNone(call["schema"])
        self.assertEqual(call["settings"].max_tokens, 900)
        self.assertTrue(call["tracing_disabled"])

    def test_typed_but_blank_output_never_enters_store(self):
        model = OfflineModel({"draft": "  ", "uncertainties": []})
        with tempfile.TemporaryDirectory() as tmp:
            store = ReviewStore(Path(tmp) / "review.sqlite")
            with self.assertRaises(agent_adapter.DraftOutputError):
                self.generate(store, model)
            with store._connect() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM drafts").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
