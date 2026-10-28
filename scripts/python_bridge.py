from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from invoice_agent.exporters import export_csv, export_xlsx  # noqa: E402
from invoice_agent.extractor import extract_invoice  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract")
    extract.add_argument("input", type=Path)
    extract.add_argument("output", type=Path)

    export = subparsers.add_parser("export")
    export.add_argument("format", choices=("csv", "xlsx"))
    export.add_argument("input", type=Path)
    export.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "extract":
        result = extract_invoice(args.input).to_dict()
        args.output.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return 0

    records = json.loads(args.input.read_text(encoding="utf-8"))
    if args.format == "csv":
        export_csv(records, args.output)
    else:
        export_xlsx(records, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
