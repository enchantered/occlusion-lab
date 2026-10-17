import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from projects.reviewgate import ReviewError, ReviewStore, fingerprint
from projects.reviewgate.__main__ import main


class LocalReviewFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'review.sqlite'
        self.store = ReviewStore(self.path)

    def cli(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(args + ['--db', str(self.path)])
        return code, out.getvalue(), err.getvalue()

    def test_inspection_does_not_approve_or_enable_export(self):
        ident = self.store.create_draft('source', 'Draft with uncertainties')
        code, text, err = self.cli(['inspect', ident])
        self.assertEqual((code, err), (0, ''))
        inspected = json.loads(text)
        self.assertEqual(inspected['draft'], 'Draft with uncertainties')
        self.assertEqual(inspected['status'], 'pending')
        self.assertEqual(inspected['hash'], fingerprint(inspected['draft']))
        self.assertIsNone(inspected['reviewer'])
        self.assertEqual(self.cli(['export', ident])[0], 2)
        self.assertTrue(self.store.verify_audit())
        self.assertEqual(self.cli(['approve', ident, '--hash', inspected['hash'], '--reviewer', 'Synthetic reviewer'])[0], 0)
        self.assertEqual(json.loads(self.cli(['export', ident])[1])['draft'], inspected['draft'])

    def test_rejection_is_visible_and_not_exportable(self):
        ident = self.store.create_draft('source', 'draft')
        self.assertEqual(self.cli(['reject', ident, '--reason', 'Unsupported claim'])[0], 0)
        info = self.store.inspect_draft(ident)
        self.assertEqual((info['status'], info['reason']), ('rejected', 'Unsupported claim'))
        self.assertEqual(self.cli(['export', ident])[0], 2)
        self.assertTrue(self.store.verify_audit())

    def test_inspection_missing_draft_fails_cleanly(self):
        with self.assertRaisesRegex(ReviewError, 'not found'):
            self.store.inspect_draft('missing')
        self.assertEqual(self.cli(['inspect', 'missing'])[0], 2)


if __name__ == '__main__':
    unittest.main()
