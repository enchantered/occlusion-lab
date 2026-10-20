"""Offline review core. Heuristic redaction is NOT comprehensive PII protection.

A local hash chain detects many mutations, not an attacker who rewrites the
entire database or rolls back both state and log to a consistent snapshot.
"""
from contextlib import contextmanager
import hashlib
import json
import os
import re
import stat
import sqlite3
import uuid
from pathlib import Path

MAX_TEXT_BYTES = 100 * 1024
_NO_CHECKPOINT = object()
_PATTERNS = (
    ("api_key", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|(?:api[_-]?key|secret)[=: ]+[A-Za-z0-9_./+-]{12,})\b", re.I)),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{12,}={0,2}", re.I)),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)")),
)


class ReviewError(ValueError):
    """Expected review operation or input error."""


def fingerprint(text: str) -> str:
    """SHA-256 of the exact UTF-8 text, without normalization."""
    if not isinstance(text, str):
        raise ReviewError("text must be a string")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_text(value, label, *, allow_blank=False):
    if not isinstance(value, str):
        raise ReviewError(f"{label} must be a string")
    if not allow_blank and not value.strip():
        raise ReviewError(f"{label} must not be empty")
    if len(value.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ReviewError(f"{label} exceeds the 100 KB limit")


def redact(text: str) -> dict:
    """Mask heuristic matches; findings contain offsets/types, never raw matches.

    Names, addresses, account numbers and many secrets may remain. This is not
    a security boundary. Spans refer to the original input.
    """
    _validate_text(text, "text", allow_blank=True)
    matches = []
    for kind, pattern in _PATTERNS:
        matches.extend((m.start(), m.end(), kind) for m in pattern.finditer(text))
    chosen = []
    for item in sorted(matches, key=lambda x: (x[0], -(x[1] - x[0]))):
        if chosen and item[0] < chosen[-1][1]:
            continue
        chosen.append(item)
    output, findings, cursor = [], [], 0
    for start, end, kind in chosen:
        output.extend((text[cursor:start], f"[REDACTED:{kind.upper()}]"))
        findings.append({"type": kind, "start": start, "end": end})
        cursor = end
    output.append(text[cursor:])
    return {"text": "".join(output), "findings": findings}


class ReviewStore:
    """Durable plaintext SQLite drafts and a local tamper-evident event chain.

    Reviewer names are assertions, not authenticated identities. Repeated
    approval/rejection fails; repeated approved export is read-only and safe.
    """
    def __init__(self, db_path):
        self.db_path = str(db_path)
        if not self.db_path or self.db_path == ":memory:":
            raise ReviewError("a persistent database file path is required")
        self._prepare_storage()
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, source_hash TEXT NOT NULL, draft TEXT NOT NULL, draft_hash TEXT NOT NULL, status TEXT NOT NULL, reviewer TEXT, reason TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, prev_hash TEXT NOT NULL, event TEXT NOT NULL, event_hash TEXT NOT NULL)")

    def _prepare_storage(self):
        """Create private missing directories/database; reject unsafe existing files.

        Existing database files with any group/other permissions are rejected,
        not chmodded. This avoids silently changing user-managed files. Directories
        that already exist are never chmodded; applications should keep their
        database directory trusted against concurrent same-user replacement.
        """
        path = Path(self.db_path)
        parent = path.parent
        missing = []
        current = parent
        while not current.exists():
            missing.append(current)
            if current.parent == current:
                raise ReviewError("cannot locate database parent directory")
            current = current.parent
        for directory in reversed(missing):
            try:
                os.mkdir(directory, 0o700)
            except FileExistsError:
                pass
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(self.db_path, flags, 0o600)
        except FileExistsError:
            try:
                info = os.lstat(self.db_path)
            except OSError as exc:
                raise ReviewError(f"cannot inspect database file: {exc}") from exc
            if not stat.S_ISREG(info.st_mode):
                raise ReviewError("database path must be a regular file, not a symlink or special file")
            if info.st_mode & 0o077:
                raise ReviewError("existing database permissions are unsafe; set mode 0600 before opening")
        except OSError as exc:
            raise ReviewError(f"cannot securely create database file: {exc}") from exc
        else:
            os.close(fd)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _canonical(obj):
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def _append(self, db, kind, data):
        row = db.execute("SELECT seq,event_hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        prev, seq = (row["event_hash"], row["seq"] + 1) if row else ("0" * 64, 1)
        body = {"seq": seq, "prev_hash": prev, "type": kind, "data": data}
        digest = fingerprint(self._canonical(body))
        db.execute("INSERT INTO audit(seq,prev_hash,event,event_hash) VALUES(?,?,?,?)", (seq, prev, self._canonical(body), digest))

    def _require_integrity(self, db):
        if not self._verify_audit(db):
            raise ReviewError("audit or draft integrity check failed")

    def create_draft(self, source: str, draft: str) -> str:
        _validate_text(source, "source")
        _validate_text(draft, "draft")
        draft_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_integrity(db)
            db.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?,?)", (draft_id, fingerprint(source), draft, fingerprint(draft), "pending", None, None))
            self._append(db, "created", {"id": draft_id, "source_hash": fingerprint(source), "draft_hash": fingerprint(draft)})
        return draft_id

    def approve(self, draft_id: str, expected_hash: str, reviewer: str) -> None:
        _validate_text(reviewer, "reviewer")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_integrity(db)
            row = db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
            if row is None:
                raise ReviewError("draft not found")
            if row["status"] != "pending":
                raise ReviewError("only pending drafts can be approved")
            actual = fingerprint(row["draft"])
            if actual != row["draft_hash"] or expected_hash != actual:
                raise ReviewError("draft hash mismatch")
            db.execute("UPDATE drafts SET status='approved', reviewer=? WHERE id=?", (reviewer.strip(), draft_id))
            self._append(db, "approved", {"id": draft_id, "hash": actual, "reviewer": reviewer.strip()})

    def reject(self, draft_id: str, reason: str) -> None:
        _validate_text(reason, "reason")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_integrity(db)
            row = db.execute("SELECT status FROM drafts WHERE id=?", (draft_id,)).fetchone()
            if row is None:
                raise ReviewError("draft not found")
            if row["status"] != "pending":
                raise ReviewError("only pending drafts can be rejected")
            db.execute("UPDATE drafts SET status='rejected', reason=? WHERE id=?", (reason.strip(), draft_id))
            self._append(db, "rejected", {"id": draft_id, "reason": reason.strip()})

    def inspect_draft(self, draft_id: str) -> dict:
        """Read local review text and status; this is not approved delivery/export."""
        with self._connect() as db:
            db.execute("BEGIN")
            self._require_integrity(db)
            row = db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
            if row is None:
                raise ReviewError("draft not found")
            return {"id": row["id"], "draft": row["draft"], "hash": row["draft_hash"],
                    "status": row["status"], "reviewer": row["reviewer"], "reason": row["reason"]}

    def export_approved(self, draft_id: str, *, checkpoint=_NO_CHECKPOINT) -> dict:
        """Export approved text, optionally bound to a trusted audit prefix.

        Checkpoint and draft checks share one SQLite read snapshot. The caller
        must protect the witness separately; this does not authenticate identity.
        """
        parts = None if checkpoint is _NO_CHECKPOINT else self._checkpoint_parts(checkpoint)
        with self._connect() as db:
            db.execute("BEGIN")
            self._require_integrity(db)
            if parts is not None:
                count, head = parts
                witness_row = db.execute("SELECT event_hash FROM audit WHERE seq=?", (count,)).fetchone()
                if witness_row is None or witness_row["event_hash"] != head:
                    raise ReviewError("checkpoint does not match current audit history; export refused")
            row = db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
            if row is None:
                raise ReviewError("draft not found")
            if row["status"] != "approved":
                raise ReviewError("draft is not approved")
            return {"id": row["id"], "draft": row["draft"], "hash": row["draft_hash"], "reviewer": row["reviewer"]}

    def _verify_audit(self, db) -> bool:
        try:
            events = db.execute("SELECT seq,prev_hash,event,event_hash FROM audit ORDER BY seq").fetchall()
            drafts = {r["id"]: dict(r) for r in db.execute("SELECT * FROM drafts")}
            replay, prev = {}, "0" * 64
            for n, row in enumerate(events, 1):
                if row["seq"] != n or row["prev_hash"] != prev:
                    return False
                body = json.loads(row["event"])
                if not isinstance(body, dict) or set(body) != {"seq", "prev_hash", "type", "data"}:
                    return False
                if body["seq"] != n or body["prev_hash"] != prev:
                    return False
                digest = fingerprint(self._canonical(body))
                if digest != row["event_hash"]:
                    return False
                data, kind = body["data"], body["type"]
                if not isinstance(data, dict):
                    return False
                if kind == "created":
                    if data["id"] in replay:
                        return False
                    replay[data["id"]] = {"source_hash": data["source_hash"], "draft_hash": data["draft_hash"], "status": "pending", "reviewer": None, "reason": None}
                elif kind == "approved":
                    state = replay.get(data["id"])
                    if not state or state["status"] != "pending" or state["draft_hash"] != data["hash"] or not isinstance(data["reviewer"], str) or not data["reviewer"].strip():
                        return False
                    state.update(status="approved", reviewer=data["reviewer"])
                elif kind == "rejected":
                    state = replay.get(data["id"])
                    if not state or state["status"] != "pending" or not isinstance(data["reason"], str) or not data["reason"].strip():
                        return False
                    state.update(status="rejected", reason=data["reason"])
                else:
                    return False
                prev = digest
            if set(replay) != set(drafts):
                return False
            for ident, expected in replay.items():
                actual = drafts[ident]
                if any(actual[field] != value for field, value in expected.items()):
                    return False
                if fingerprint(actual["draft"]) != actual["draft_hash"]:
                    return False
            return True
        except (sqlite3.Error, ValueError, KeyError, TypeError, AttributeError):
            return False

    def verify_audit(self) -> bool:
        """Verify chain and replayed state within one consistent read snapshot."""
        try:
            with self._connect() as db:
                db.execute("BEGIN")
                return self._verify_audit(db)
        except sqlite3.Error:
            return False

    def create_checkpoint(self) -> dict:
        """Return a local witness for the current nonempty, verified audit prefix.

        This only detects rollback/rewrite relative to a separately retained
        trusted witness. It provides no automatic external anchoring and no
        protection if both the witness and database are compromised.
        """
        try:
            with self._connect() as db:
                db.execute("BEGIN")
                if not self._verify_audit(db):
                    raise ReviewError("cannot create checkpoint: audit integrity check failed")
                row = db.execute("SELECT seq,event_hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
                if row is None:
                    raise ReviewError("cannot create checkpoint for empty audit")
                return {"version": 1, "event_count": row["seq"], "head_hash": row["event_hash"]}
        except sqlite3.Error as exc:
            raise ReviewError(f"cannot create checkpoint: {exc}") from exc

    @staticmethod
    def _checkpoint_parts(checkpoint):
        message = "invalid checkpoint"
        if not isinstance(checkpoint, dict) or set(checkpoint) != {"version", "event_count", "head_hash"}:
            raise ReviewError(f"{message}: expected exactly version, event_count, and head_hash")
        count, version, head = checkpoint["event_count"], checkpoint["version"], checkpoint["head_hash"]
        if type(version) is not int or version != 1:
            raise ReviewError(f"{message}: version must be integer 1")
        if type(count) is not int or not 1 <= count <= (2 ** 63 - 1):
            raise ReviewError(f"{message}: event_count must be a positive signed 64-bit integer")
        if not isinstance(head, str) or re.fullmatch(r"[0-9a-f]{64}", head) is None:
            raise ReviewError(f"{message}: head_hash must be 64 lowercase hexadecimal characters")
        return count, head

    def verify_checkpoint(self, checkpoint) -> bool:
        """Compare a caller-retained checkpoint to a verified local audit prefix.

        The checkpoint is a trusted witness supplied by the caller, not loaded
        from this database. Subsequent valid events after its sequence are allowed.
        """
        count, head = self._checkpoint_parts(checkpoint)
        try:
            with self._connect() as db:
                db.execute("BEGIN")
                if not self._verify_audit(db):
                    return False
                row = db.execute("SELECT event_hash FROM audit WHERE seq=?", (count,)).fetchone()
                return row is not None and row["event_hash"] == head
        except sqlite3.Error:
            return False
