import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from projects.reviewgate import ReviewStore, ReviewError, fingerprint
from projects.reviewgate.__main__ import main


class CheckpointExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'review.db'
        self.store = ReviewStore(self.path)
        self.ident = self.store.create_draft('Synthetic source', 'Synthetic draft')
        self.store.approve(self.ident, fingerprint('Synthetic draft'), 'Synthetic reviewer')

    def test_checkpoint_and_export_share_one_connection(self):
        witness = self.store.create_checkpoint()
        self.store.create_draft('Another synthetic source', 'Later pending text')
        with patch.object(self.store, '_connect', wraps=self.store._connect) as connect:
            self.assertEqual(self.store.export_approved(self.ident, checkpoint=witness)['draft'], 'Synthetic draft')
            self.assertEqual(connect.call_count, 1)

    def test_rollback_keeps_ordinary_export_but_refuses_checkpoint_bound_export(self):
        older = self.root / 'older.db'
        shutil.copy2(self.path, older)
        self.store.create_draft('Later source', 'Later draft')
        witness = self.store.create_checkpoint()
        shutil.copy2(older, self.path)
        self.assertTrue(self.store.verify_audit())
        self.assertEqual(self.store.export_approved(self.ident)['draft'], 'Synthetic draft')
        with self.assertRaisesRegex(ReviewError, 'checkpoint'):
            self.store.export_approved(self.ident, checkpoint=witness)

    def test_explicit_null_or_invalid_checkpoint_never_means_skip(self):
        for value in (None, {}, [], {'version': True}):
            with self.subTest(value=value), self.assertRaisesRegex(ReviewError, 'checkpoint'):
                self.store.export_approved(self.ident, checkpoint=value)

    def test_checkpoint_never_approves_pending_text(self):
        ident = self.store.create_draft('source', 'pending')
        witness = self.store.create_checkpoint()
        with self.assertRaisesRegex(ReviewError, 'not approved'):
            self.store.export_approved(ident, checkpoint=witness)

    def test_cli_checkpoint_export_and_invalid_witness_fail_without_output(self):
        witness_file = self.root / 'witness.json'
        witness_file.write_text(json.dumps(self.store.create_checkpoint()), encoding='utf-8')
        for payload, expected_code in ((witness_file.read_text(), 0), ('null', 2)):
            witness_file.write_text(payload, encoding='utf-8')
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(['export', self.ident, '--db', str(self.path), '--checkpoint', str(witness_file)])
            self.assertEqual(code, expected_code)
            if code:
                self.assertEqual(out.getvalue(), '')
                self.assertIn('checkpoint', err.getvalue())
            else:
                self.assertEqual(json.loads(out.getvalue())['id'], self.ident)


if __name__ == '__main__':
    unittest.main()
