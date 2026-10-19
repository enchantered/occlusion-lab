import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from projects.reviewgate import ReviewError, ReviewStore, fingerprint


class ReviewTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "review.sqlite"
        self.store = ReviewStore(self.path)

    def _events(self):
        with sqlite3.connect(self.path) as db:
            return [json.loads(row[0]) for row in db.execute(
                "SELECT event FROM audit ORDER BY seq"
            )]

    def _race(self, operations):
        barrier = threading.Barrier(len(operations), timeout=5)

        def invoke(operation):
            barrier.wait(timeout=5)
            try:
                operation()
                return "success"
            except ReviewError:
                return "error"

        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            futures = [pool.submit(invoke, operation) for operation in operations]
            return [future.result(timeout=10) for future in futures]

    def test_competing_approvals_have_one_winner(self):
        ident = self.store.create_draft("source", "draft")
        digest = fingerprint("draft")
        stores = [ReviewStore(self.path), ReviewStore(self.path)]
        outcomes = self._race([
            lambda: stores[0].approve(ident, digest, "Reviewer A"),
            lambda: stores[1].approve(ident, digest, "Reviewer B"),
        ])

        self.assertCountEqual(outcomes, ["success", "error"])
        self.assertEqual(self.store.inspect_draft(ident)["status"], "approved")
        approved = [event for event in self._events() if event["type"] == "approved"]
        self.assertEqual(len(approved), 1)
        self.assertTrue(self.store.verify_audit())

    def test_concurrent_approve_and_reject_have_one_terminal_winner(self):
        ident = self.store.create_draft("source", "draft")
        digest = fingerprint("draft")
        stores = [ReviewStore(self.path), ReviewStore(self.path)]
        outcomes = self._race([
            lambda: stores[0].approve(ident, digest, "Reviewer"),
            lambda: stores[1].reject(ident, "Needs revision"),
        ])

        self.assertCountEqual(outcomes, ["success", "error"])
        info = self.store.inspect_draft(ident)
        events = self._events()
        terminal = [event for event in events if event["type"] in ("approved", "rejected")]
        self.assertEqual(len(terminal), 1)
        self.assertEqual(info["status"], terminal[0]["type"])
        self.assertTrue(self.store.verify_audit())
        if info["status"] == "approved":
            self.assertEqual(self.store.export_approved(ident)["hash"], digest)
        else:
            with self.assertRaises(ReviewError):
                self.store.export_approved(ident)

    def test_create_draft_append_failure_rolls_back_draft_and_audit(self):
        original_append = self.store._append

        def fail_append(db, kind, data):
            raise RuntimeError("injected append failure")

        self.store._append = fail_append
        try:
            with self.assertRaisesRegex(RuntimeError, "injected append failure"):
                self.store.create_draft("source", "draft")
        finally:
            self.store._append = original_append

        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM drafts").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 0)
        ident = self.store.create_draft("source", "subsequent draft")
        self.assertEqual(self.store.inspect_draft(ident)["status"], "pending")
        self.assertTrue(self.store.verify_audit())

    def test_approval_append_failure_rolls_back_status_and_audit(self):
        ident = self.store.create_draft("source", "draft")
        original_append = self.store._append

        def fail_append(db, kind, data):
            raise RuntimeError("injected append failure")

        self.store._append = fail_append
        try:
            with self.assertRaisesRegex(RuntimeError, "injected append failure"):
                self.store.approve(ident, fingerprint("draft"), "Reviewer")
        finally:
            self.store._append = original_append

        self.assertEqual(self.store.inspect_draft(ident)["status"], "pending")
        self.assertFalse(any(event["type"] == "approved" for event in self._events()))
        self.assertTrue(self.store.verify_audit())


if __name__ == "__main__":
    unittest.main()
