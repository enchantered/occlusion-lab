"""Command-line interface: python -m projects.reviewgate <command>."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from .core import ReviewError, ReviewStore, fingerprint, redact


def _read_checkpoint(path):
    try:
        with path.open("rb") as checkpoint_file:
            raw = checkpoint_file.read(4097)
        if len(raw) > 4096:
            raise ReviewError("checkpoint file exceeds the 4 KB limit")
        return json.loads(raw)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise ReviewError("cannot read valid checkpoint JSON (maximum 4 KB)") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m projects.reviewgate")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="load sample JSON as a pending draft only")
    demo.add_argument("sample"); demo.add_argument("--db", required=True)
    approve = sub.add_parser("approve"); approve.add_argument("id"); approve.add_argument("--hash", required=True); approve.add_argument("--reviewer", required=True); approve.add_argument("--db", required=True)
    inspect = sub.add_parser("inspect", help="read local draft for human review, not approved delivery")
    inspect.add_argument("id"); inspect.add_argument("--db", required=True)
    reject = sub.add_parser("reject"); reject.add_argument("id"); reject.add_argument("--reason", required=True); reject.add_argument("--db", required=True)
    export = sub.add_parser("export"); export.add_argument("id"); export.add_argument("--db", required=True)
    export.add_argument("--checkpoint", type=Path, help="require a trusted checkpoint match in the same export snapshot")
    audit = sub.add_parser("audit"); audit.add_argument("--db", required=True)
    audit.add_argument("--checkpoint", type=Path, help="verify against a separately retained trusted checkpoint JSON file")
    checkpoint = sub.add_parser("checkpoint", help="print an audit witness; retain it separately from the database")
    checkpoint.add_argument("--db", required=True)
    redact_cmd = sub.add_parser("redact"); redact_cmd.add_argument("file")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            try:
                record = json.loads(Path(args.sample).read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ReviewError(f"cannot read sample JSON: {exc}") from exc
            if not isinstance(record, dict) or not isinstance(record.get("source"), str) or not isinstance(record.get("draft"), str):
                raise ReviewError("sample JSON must contain string source and draft fields")
            store = ReviewStore(args.db)
            ident = store.create_draft(record["source"], record["draft"])
            print(json.dumps({"id": ident, "hash": fingerprint(record["draft"]), "status": "pending"}))
        elif args.command == "approve":
            ReviewStore(args.db).approve(args.id, args.hash, args.reviewer)
            print(json.dumps({"id": args.id, "status": "approved"}))
        elif args.command == "inspect":
            print(json.dumps(ReviewStore(args.db).inspect_draft(args.id), ensure_ascii=False))
        elif args.command == "reject":
            ReviewStore(args.db).reject(args.id, args.reason)
            print(json.dumps({"id": args.id, "status": "rejected"}))
        elif args.command == "export":
            options = {} if args.checkpoint is None else {"checkpoint": _read_checkpoint(args.checkpoint)}
            print(json.dumps(ReviewStore(args.db).export_approved(args.id, **options), ensure_ascii=False))
        elif args.command == "checkpoint":
            print(json.dumps(ReviewStore(args.db).create_checkpoint(), sort_keys=True))
        elif args.command == "audit":
            if args.checkpoint is None:
                ok = ReviewStore(args.db).verify_audit()
            else:
                witness = _read_checkpoint(args.checkpoint)
                ok = ReviewStore(args.db).verify_checkpoint(witness)
            print(json.dumps({"valid": ok}))
            return 0 if ok else 1
        elif args.command == "redact":
            try:
                text = Path(args.file).read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise ReviewError(f"cannot read file: {exc}") from exc
            print(json.dumps(redact(text), ensure_ascii=False))
        return 0
    except (ReviewError, OSError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
