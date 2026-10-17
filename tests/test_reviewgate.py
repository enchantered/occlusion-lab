import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from projects.reviewgate import ReviewError, ReviewStore, fingerprint, redact


class ReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = ReviewStore(self.root / "review.db")

    def make_draft(self, store=None):
        return (store or self.store).create_draft("books and records", "Quarterly summary is ready.")

    def test_success_and_restart_persistence(self):
        path = self.root / "durable.sqlite"
        store = ReviewStore(path)
        ident = store.create_draft("source", "draft")
        digest = fingerprint("draft")
        store.approve(ident, digest, "Reviewer")
        self.assertEqual(ReviewStore(path).export_approved(ident), {
            "id": ident, "draft": "draft", "hash": digest, "reviewer": "Reviewer"
        })
        self.assertTrue(store.verify_audit())

    def test_wrong_hash_and_pending_export(self):
        ident = self.make_draft()
        with self.assertRaises(ReviewError):
            self.store.approve(ident, "0" * 64, "R")
        with self.assertRaises(ReviewError):
            self.store.export_approved(ident)
        self.assertTrue(self.store.verify_audit())

    def test_reject_and_empty_reviewer(self):
        ident = self.make_draft()
        with self.assertRaises(ReviewError):
            self.store.approve(ident, fingerprint("Quarterly summary is ready."), "  ")
        self.store.reject(ident, "Needs revision")
        with self.assertRaises(ReviewError):
            self.store.export_approved(ident)
        self.assertTrue(self.store.verify_audit())

    def test_tampered_draft_and_audit_deletion_update(self):
        ident = self.make_draft()
        with sqlite3.connect(self.store.db_path) as db:
            db.execute("UPDATE drafts SET draft='altered' WHERE id=?", (ident,))
        self.assertFalse(self.store.verify_audit())
        path = self.root / "other.sqlite"
        other = ReviewStore(path)
        self.make_draft(other)
        with sqlite3.connect(path) as db:
            db.execute("UPDATE audit SET event_hash=? WHERE seq=1", ("f" * 64,))
        self.assertFalse(other.verify_audit())
        with sqlite3.connect(path) as db:
            db.execute("DELETE FROM audit")
        self.assertFalse(other.verify_audit())

    def test_redaction_positive_and_limits(self):
        result = redact("Mail jane@example.com; call +1 (415) 555-0123; Bearer abcdefghijklmnop; sk-abcdefghijklmnop")
        self.assertEqual({finding["type"] for finding in result["findings"]}, {"email", "phone", "bearer_token", "api_key"})
        self.assertNotIn("jane@example.com", result["text"])
        self.assertIn("REDACTED", result["text"])
        self.assertEqual(redact("Alice lives at 1 Main Street")["findings"], [])

    def test_cli_bad_json_exit_two(self):
        bad = self.root / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        proc = subprocess.run([
            sys.executable, "-m", "projects.reviewgate", "demo", str(bad),
            "--db", str(self.root / "db")
        ], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("error:", proc.stderr)


if __name__ == "__main__":
    unittest.main()
