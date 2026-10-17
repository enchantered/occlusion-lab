"""Command-line interface for Venture Lab."""
import argparse
import json
import sys

from .opportunities import rank_opportunities


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m venturelab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    rank_parser = subparsers.add_parser("rank", help="rank opportunities from a JSON manifest")
    rank_parser.add_argument("manifest", help="path to JSON manifest")
    args = parser.parse_args(argv)
    try:
        with open(args.manifest, "r", encoding="utf-8") as source:
            data = json.load(source)
        result = rank_opportunities(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
