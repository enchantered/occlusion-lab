"""Local-first draft review with a durable, hash-chained audit trail.

The audit chain detects accidental or partial modification; it is not
cryptographic proof against an attacker able to rewrite the entire database.
Redaction is heuristic and is not comprehensive PII protection.
"""
from .core import ReviewError, ReviewStore, fingerprint, redact

__all__ = ["ReviewError", "ReviewStore", "fingerprint", "redact"]
