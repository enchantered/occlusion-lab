import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from projects.reviewgate import ReviewError, ReviewStore


class AuditCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "review.sqlite"
        self.store = ReviewStore(self.path)

    def add_event(self, suffix=""):
        return self.store.create_draft("source" + suffix, "draft" + suffix)

    def test_clean_roundtrip_and_append_allowed(self):
        self.add_event()
        checkpoint = self.store.create_checkpoint()
        self.assertEqual(set(checkpoint), {"version", "event_count", "head_hash"})
        self.assertEqual(checkpoint["version"], 1)
        self.assertEqual(checkpoint["event_count"], 1)
        self.assertRegex(checkpoint["head_hash"], r"^[0-9a-f]{64}$")
        self.assertTrue(self.store.verify_checkpoint(checkpoint))
        self.add_event(" next")
        self.assertTrue(self.store.verify_checkpoint(checkpoint))

    def test_consistent_rollback_and_alternative_history_fail_checkpoint(self):
        self.add_event()
        checkpoint = self.store.create_checkpoint()
        self.add_event(" later")
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM audit WHERE seq > 1")
            db.execute("DELETE FROM drafts WHERE id NOT IN (SELECT json_extract(event, '$.data.id') FROM audit)")
        self.assertTrue(self.store.verify_audit())
        self.assertTrue(self.store.verify_checkpoint(checkpoint))  # witness is at this prefix

        # Save witness at two events, then replace both events and replayed state
        # with a different but internally valid history of the same length.
        self.add_event(" second")
        checkpoint2 = self.store.create_checkpoint()
        replacement = ReviewStore(Path(self.temp.name) / "other.sqlite")
        replacement.create_draft("different source", "different draft")
        replacement.create_draft("different source 2", "different draft 2")
        with sqlite3.connect(self.path) as dest, sqlite3.connect(replacement.db_path) as src:
            dest.execute("DELETE FROM audit")
            dest.execute("DELETE FROM drafts")
            dest.executemany("INSERT INTO audit(seq,prev_hash,event,event_hash) VALUES(?,?,?,?)", src.execute("SELECT seq,prev_hash,event,event_hash FROM audit"))
            dest.executemany("INSERT INTO drafts VALUES(?,?,?,?,?,?,?)", src.execute("SELECT * FROM drafts"))
        self.assertTrue(self.store.verify_audit())
        self.assertFalse(self.store.verify_checkpoint(checkpoint2))

    def test_rollback_to_prior_valid_prefix_is_detected(self):
        self.add_event()
        self.add_event(" two")
        self.add_event(" three")
        witness = self.store.create_checkpoint()
        self.add_event(" four")
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM audit WHERE seq > 2")
            db.execute("DELETE FROM drafts WHERE id NOT IN (SELECT json_extract(event, '$.data.id') FROM audit)")
        self.assertTrue(self.store.verify_audit())
        self.assertFalse(self.store.verify_checkpoint(witness))

    def test_malformed_checkpoints_raise_review_error(self):
        self.add_event()
        good = self.store.create_checkpoint()
        bad = [None, [], {}, {**good, "extra": 1}]
        for field, values in {
            "version": [True, 2, "1"],
            "event_count": [True, 0, -1, 1.0, "1", 2 ** 63, 10 ** 40],
            "head_hash": ["A" * 64, "0" * 63, "g" * 64, None],
        }.items():
            bad.extend({**good, field: value} for value in values)
        for item in bad:
            with self.subTest(checkpoint=item), self.assertRaisesRegex(ReviewError, "checkpoint"):
                self.store.verify_checkpoint(item)

    def test_empty_and_corrupt_audit_checkpoint_behavior(self):
        with self.assertRaisesRegex(ReviewError, "checkpoint"):
            self.store.create_checkpoint()
        self.add_event()
        witness = self.store.create_checkpoint()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE audit SET event='not json'")
        self.assertFalse(self.store.verify_audit())
        self.assertFalse(self.store.verify_checkpoint(witness))
        with self.assertRaisesRegex(ReviewError, "checkpoint"):
            self.store.create_checkpoint()

    def test_checkpoint_read_operations_do_not_write_audit(self):
        self.add_event()
        before = self._audit_rows()
        checkpoint = self.store.create_checkpoint()
        self.assertTrue(self.store.verify_checkpoint(checkpoint))
        self.assertTrue(self.store.verify_audit())
        self.assertEqual(self._audit_rows(), before)

    def _audit_rows(self):
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT seq,prev_hash,event,event_hash FROM audit ORDER BY seq").fetchall()


if __name__ == "__main__":
    unittest.main()
