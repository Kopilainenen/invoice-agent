from __future__ import annotations

import argparse
import json
from pathlib import Path

from .extractor import extract_invoice


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract structured fields from a Russian invoice PDF."
    )
    parser.add_argument("pdf", type=Path, help="Path to a text-based PDF invoice")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Optional JSON output path. Prints to stdout when omitted.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = extract_invoice(args.pdf).to_dict()
    serialized = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

