from __future__ import annotations

import argparse
import cgi
import json
import os
import sys
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
sys.path.insert(0, str(ROOT / "src"))

from invoice_agent.exporters import export_csv, export_xlsx  # noqa: E402
from invoice_agent.extractor import extract_invoice  # noqa: E402
from invoice_agent.pdf_text import PdfTextError  # noqa: E402


MAX_FILE_SIZE = 12 * 1024 * 1024
MAX_FILES = 20
SUPPORTED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png"}


class InvoiceRequestHandler(BaseHTTPRequestHandler):
    server_version = "InvoiceAgent/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json({"status": "ok"})
            return

        file_name = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
        static_path = (WEB_ROOT / file_name).resolve()
        if WEB_ROOT.resolve() not in static_path.parents and static_path != WEB_ROOT.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not static_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }
        body = static_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_types.get(static_path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/extract":
                self._handle_extract()
            elif parsed.path == "/api/export":
                format_name = parse_qs(parsed.query).get("format", [""])[0]
                self._handle_export(format_name)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as error:  # defensive HTTP boundary
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def _handle_extract(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("Ожидалась загрузка multipart/form-data")

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        upload_items = form["files"] if "files" in form else []
        if not isinstance(upload_items, list):
            upload_items = [upload_items]
        if not upload_items:
            raise ValueError("Файлы не переданы")
        if len(upload_items) > MAX_FILES:
            raise ValueError(f"За один раз можно обработать не больше {MAX_FILES} файлов")

        records = []
        errors = []
        upload_root = ROOT / "tmp" / "uploads"
        upload_root.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(dir=upload_root) as directory:
            temp_dir = Path(directory)
            for index, item in enumerate(upload_items):
                filename = Path(item.filename or f"invoice-{index + 1}.pdf").name
                if Path(filename).suffix.lower() not in SUPPORTED_SUFFIXES:
                    errors.append({"file": filename, "error": "Поддерживаются PDF, JPG и PNG"})
                    continue
                data = item.file.read(MAX_FILE_SIZE + 1)
                if len(data) > MAX_FILE_SIZE:
                    errors.append({"file": filename, "error": "Файл превышает 12 МБ"})
                    continue
                temp_path = temp_dir / f"{index:03d}-{filename}"
                temp_path.write_bytes(data)
                try:
                    record = extract_invoice(temp_path).to_dict()
                    record["source_file"] = filename
                    records.append(record)
                except PdfTextError as error:
                    errors.append({"file": filename, "error": str(error)})

        if not records:
            message = errors[0]["error"] if errors else "Документы не обработаны"
            raise ValueError(message)
        self._send_json({"records": records, "errors": errors})

    def _handle_export(self, format_name: str) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 8 * 1024 * 1024:
            raise ValueError("Некорректный размер запроса")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        records = payload.get("records")
        if not isinstance(records, list) or not records:
            raise ValueError("Нет данных для экспорта")

        export_root = ROOT / "tmp" / "exports"
        export_root.mkdir(parents=True, exist_ok=True)
        suffix = ".csv" if format_name == "csv" else ".xlsx" if format_name == "xlsx" else None
        if suffix is None:
            raise ValueError("Поддерживается экспорт CSV или XLSX")

        with tempfile.TemporaryDirectory(dir=export_root) as directory:
            output = Path(directory) / f"invoice-register{suffix}"
            if format_name == "csv":
                export_csv(records, output)
                content_type = "text/csv; charset=utf-8"
            else:
                export_xlsx(records, output)
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            body = output.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="invoice-register{suffix}"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local Invoice Agent web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    server = ThreadingHTTPServer((args.host, args.port), InvoiceRequestHandler)
    print(f"Invoice Agent: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

