from __future__ import annotations

import argparse
import json
from pathlib import Path

from .exporters import export_csv, export_xlsx
from .extractor import extract_invoice


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract multiple invoice PDFs into a CSV or XLSX register."
    )
    parser.add_argument("pdfs", nargs="+", type=Path, help="Invoice PDF paths")
    parser.add_argument("--output", "-o", required=True, type=Path)
    parser.add_argument(
        "--json-dir",
        type=Path,
        help="Optional directory for individual extracted JSON files",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    invoices: list[dict] = []

    for pdf_path in args.pdfs:
        result = extract_invoice(pdf_path).to_dict()
        invoices.append(result)
        if args.json_dir:
            args.json_dir.mkdir(parents=True, exist_ok=True)
            json_path = args.json_dir / f"{pdf_path.stem}.json"
            json_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    suffix = args.output.suffix.lower()
    if suffix == ".csv":
        export_csv(invoices, args.output)
    elif suffix == ".xlsx":
        export_xlsx(invoices, args.output)
    else:
        raise SystemExit("Output must have a .csv or .xlsx extension")

    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

