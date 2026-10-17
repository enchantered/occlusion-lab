import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from projects.reviewgate import ReviewError, ReviewStore, fingerprint, redact
from projects.reviewgate.__main__ import main


class ReviewHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'review.sqlite'
        self.store = ReviewStore(self.path)

    def test_raw_matches_never_returned_in_findings(self):
        result = redact('Call +1 (415) 555-0123 or mail synthetic@example.com')
        rendered = json.dumps(result)
        self.assertNotIn('synthetic@example.com', rendered)
        self.assertNotIn('555-0123', rendered)
        self.assertTrue(result['findings'])
        self.assertTrue(all(set(f) == {'type', 'start', 'end'} for f in result['findings']))

    def test_forged_approved_state_cannot_export(self):
        ident = self.store.create_draft('source', 'draft')
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE drafts SET status='approved',reviewer='forged' WHERE id=?", (ident,))
        with self.assertRaisesRegex(ReviewError, 'integrity'):
            self.store.export_approved(ident)

    def test_draft_and_hash_rewrite_does_not_reuse_approval(self):
        ident = self.store.create_draft('source', 'draft')
        self.store.approve(ident, fingerprint('draft'), 'human')
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE drafts SET draft=?,draft_hash=? WHERE id=?', ('changed', fingerprint('changed'), ident))
        with self.assertRaisesRegex(ReviewError, 'integrity'):
            self.store.export_approved(ident)

    def test_corrupt_audit_fails_closed_on_write_and_malformed_event(self):
        ident = self.store.create_draft('source', 'draft')
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE audit SET event='[]'")
        self.assertFalse(self.store.verify_audit())
        with self.assertRaisesRegex(ReviewError, 'integrity'):
            self.store.approve(ident, fingerprint('draft'), 'human')
        with self.assertRaisesRegex(ReviewError, 'integrity'):
            self.store.create_draft('source', 'next draft')

    def test_blank_and_oversized_drafts_and_memory_path_rejected(self):
        for source, draft in [(' ', 'draft'), ('source', ''), ('source', 'x' * 102401)]:
            with self.subTest(source=source[:8], size=len(draft)), self.assertRaises(ReviewError):
                self.store.create_draft(source, draft)
        with self.assertRaisesRegex(ReviewError, 'persistent'):
            ReviewStore(':memory:')

    def test_repeated_approval_fails_repeated_export_is_read_only(self):
        ident = self.store.create_draft('source', 'draft')
        self.store.approve(ident, fingerprint('draft'), 'human')
        with self.assertRaisesRegex(ReviewError, 'pending'):
            self.store.approve(ident, fingerprint('draft'), 'human')
        self.assertEqual(self.store.export_approved(ident), self.store.export_approved(ident))
        self.assertTrue(self.store.verify_audit())

    def test_concurrent_creation_serializes_audit_updates(self):
        def create(i):
            return ReviewStore(self.path).create_draft(f'source {i}', f'draft {i}')
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(create, range(12)))
        self.assertEqual(len(set(ids)), 12)
        self.assertTrue(self.store.verify_audit())

    def test_programmatic_cli_handles_database_error_cleanly(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(['audit', '--db', str(Path(self.tmp.name))])
        self.assertEqual(code, 2)
        self.assertIn('error:', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
