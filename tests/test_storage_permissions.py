import os
import stat
import tempfile
import unittest
from pathlib import Path

from projects.reviewgate import ReviewError, ReviewStore, fingerprint


@unittest.skipUnless(os.name == "posix", "POSIX file modes required")
class StoragePermissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def mode(self, path):
        return stat.S_IMODE(path.stat().st_mode)

    def test_new_db_is_private_even_with_permissive_umask(self):
        path = self.root / "new" / "nested" / "review.db"
        previous = os.umask(0)
        try:
            store = ReviewStore(path)
        finally:
            os.umask(previous)
        self.assertEqual(self.mode(path), 0o600)
        self.assertEqual(self.mode(path.parent), 0o700)
        self.assertEqual(self.mode(path.parent.parent), 0o700)
        self.assertTrue(store.verify_audit())

    def test_symlink_is_rejected_without_touching_target(self):
        target = self.root / "target.db"
        target.write_bytes(b"important")
        link = self.root / "linked.db"
        link.symlink_to(target)
        with self.assertRaisesRegex(ReviewError, "regular file"):
            ReviewStore(link)
        self.assertEqual(target.read_bytes(), b"important")

    def test_existing_unsafe_db_is_rejected_not_hardened(self):
        path = self.root / "unsafe.db"
        path.write_bytes(b"existing")
        path.chmod(0o644)
        with self.assertRaisesRegex(ReviewError, "permissions are unsafe"):
            ReviewStore(path)
        self.assertEqual(self.mode(path), 0o644)
        self.assertEqual(path.read_bytes(), b"existing")

    def test_existing_safe_db_normal_workflow(self):
        path = self.root / "normal.db"
        store = ReviewStore(path)
        self.assertEqual(self.mode(path), 0o600)
        ident = store.create_draft("source", "draft")
        store.approve(ident, fingerprint("draft"), "Reviewer")
        reopened = ReviewStore(path)
        self.assertEqual(reopened.export_approved(ident)["draft"], "draft")
        self.assertTrue(reopened.verify_audit())

    def test_preexisting_parent_is_not_chmodded(self):
        parent = self.root / "shared"
        parent.mkdir(mode=0o755)
        parent.chmod(0o755)
        ReviewStore(parent / "review.db")
        self.assertEqual(self.mode(parent), 0o755)


if __name__ == "__main__":
    unittest.main()
