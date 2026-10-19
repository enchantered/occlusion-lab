import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from projects.reviewgate import ReviewStore, fingerprint
from projects.reviewgate.__main__ import main


class CheckpointCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'review.sqlite'
        self.store = ReviewStore(self.path)
        self.witness = self.root / 'trusted-witness.json'

    def cli(self, command):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(command + ['--db', str(self.path)])
        return code, out.getvalue(), err.getvalue()

    def test_checkpoint_is_read_only_and_allows_verified_append(self):
        ident = self.store.create_draft('Synthetic source', 'Synthetic draft')
        code, text, err = self.cli(['checkpoint'])
        self.assertEqual((code, err), (0, ''))
        witness = json.loads(text)
        self.assertEqual(witness['event_count'], 1)
        self.witness.write_text(text, encoding='utf-8')
        self.assertEqual(self.store.inspect_draft(ident)['status'], 'pending')
        self.store.approve(ident, fingerprint('Synthetic draft'), 'Synthetic reviewer')
        code, result, err = self.cli(['audit', '--checkpoint', str(self.witness)])
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(json.loads(result), {'valid': True})
        self.assertEqual(self.witness.read_text(encoding='utf-8'), text)
        self.assertEqual(self.cli(['audit'])[0], 0)

    def test_consistent_rollback_fails_against_witness_but_plain_audit_passes(self):
        ident = self.store.create_draft('Synthetic source', 'Synthetic draft')
        backup = self.root / 'older.sqlite'
        shutil.copy2(self.path, backup)
        self.store.approve(ident, fingerprint('Synthetic draft'), 'Synthetic reviewer')
        self.witness.write_text(self.cli(['checkpoint'])[1], encoding='utf-8')
        shutil.copy2(backup, self.path)
        self.assertEqual(self.cli(['audit'])[0], 0)
        code, result, err = self.cli(['audit', '--checkpoint', str(self.witness)])
        self.assertEqual((code, err), (1, ''))
        self.assertEqual(json.loads(result), {'valid': False})

    def test_empty_database_cannot_issue_a_meaningful_witness(self):
        code, out, err = self.cli(['checkpoint'])
        self.assertEqual((code, out), (2, ''))
        self.assertIn('error:', err)

    def test_unreadable_malformed_and_oversized_witnesses_fail_cleanly(self):
        oversized_counter = json.dumps({'version': 1, 'event_count': 10 ** 40,
                                        'head_hash': '0' * 64}).encode('utf-8')
        for payload in (None, b'not json', b'\xff', b' ' * 4097, b'[]', b'{}', oversized_counter):
            with self.subTest(payload=payload):
                if payload is not None:
                    self.witness.write_bytes(payload)
                code, out, err = self.cli(['audit', '--checkpoint', str(self.witness)])
                self.assertEqual((code, out), (2, ''))
                self.assertIn('checkpoint', err.lower())


if __name__ == '__main__':
    unittest.main()
