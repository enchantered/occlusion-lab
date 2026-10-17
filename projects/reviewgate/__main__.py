"""Command-line interface: python -m projects.reviewgate <command>."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from .core import ReviewError, ReviewStore, fingerprint, redact

def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m projects.reviewgate")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="load sample JSON as a pending draft only")
    demo.add_argument("sample"); demo.add_argument("--db", required=True)
    approve = sub.add_parser("approve"); approve.add_argument("id"); approve.add_argument("--hash", required=True); approve.add_argument("--reviewer", required=True); approve.add_argument("--db", required=True)
    export = sub.add_parser("export"); export.add_argument("id"); export.add_argument("--db", required=True)
    audit = sub.add_parser("audit"); audit.add_argument("--db", required=True)
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
        elif args.command == "export": print(json.dumps(ReviewStore(args.db).export_approved(args.id), ensure_ascii=False))
        elif args.command == "audit":
            ok = ReviewStore(args.db).verify_audit()
            print(json.dumps({"valid": ok}))
            return 0 if ok else 1
        elif args.command == "redact":
            try: text = Path(args.file).read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc: raise ReviewError(f"cannot read file: {exc}") from exc
            print(json.dumps(redact(text), ensure_ascii=False))
        return 0
    except (ReviewError, OSError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
