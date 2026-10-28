from __future__ import annotations

from pathlib import Path
from threading import Lock

import pdfplumber


class PdfTextError(RuntimeError):
    """Raised when a PDF cannot provide a usable text layer."""


SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png"}
_reader = None
_reader_lock = Lock()


def _get_ocr_reader():
    global _reader
    if _reader is None:
        with _reader_lock:
            if _reader is None:
                try:
                    import easyocr
                except ImportError as error:
                    raise PdfTextError(
                        "OCR не установлен. Выполните: pip install easyocr PyMuPDF"
                    ) from error
                _reader = easyocr.Reader(["ru", "en"], gpu=False, verbose=False)
    return _reader


def _ordered_ocr_text(image) -> str:
    results = _get_ocr_reader().readtext(image, detail=1, paragraph=False)
    fragments = []
    for box, text, confidence in results:
        cleaned = str(text).strip()
        if not cleaned or float(confidence) < 0.15:
            continue
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        fragments.append((sum(ys) / len(ys), min(xs), max(ys) - min(ys), cleaned))

    fragments.sort(key=lambda item: (item[0], item[1]))
    lines: list[dict] = []
    for center_y, left_x, height, text in fragments:
        tolerance = max(8.0, height * 0.6)
        target = next(
            (line for line in reversed(lines) if abs(line["y"] - center_y) <= tolerance),
            None,
        )
        if target is None:
            lines.append({"y": center_y, "parts": [(left_x, text)]})
        else:
            target["parts"].append((left_x, text))
    return "\n".join(
        " ".join(text for _, text in sorted(line["parts"])) for line in lines
    )


def _ocr_pdf(path: Path) -> str:
    try:
        import pymupdf
    except ImportError as error:
        raise PdfTextError(
            "Для OCR PDF не установлен PyMuPDF. Выполните: pip install PyMuPDF"
        ) from error

    pages: list[str] = []
    with pymupdf.open(path) as document:
        for page in document:
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), alpha=False)
            pages.append(_ordered_ocr_text(pixmap.tobytes("png")))
    return "\n".join(pages).strip()


def extract_document_text(path: str | Path) -> tuple[str, bool]:
    document_path = Path(path)
    if not document_path.is_file():
        raise FileNotFoundError(document_path)

    suffix = document_path.suffix.lower()
    if suffix in SUPPORTED_IMAGES:
        text = _ordered_ocr_text(str(document_path))
        if len(text) < 20:
            raise PdfTextError("OCR не смог распознать достаточно текста на изображении")
        return text, True
    if suffix != ".pdf":
        raise PdfTextError(f"Неподдерживаемый тип файла: {suffix or '<нет>'}")

    pages: list[str] = []
    with pdfplumber.open(document_path) as document:
        for page in document.pages:
            pages.append(page.extract_text(x_tolerance=2, y_tolerance=3) or "")
    text = "\n".join(pages).strip()
    if len(text) >= 40:
        return text, False

    text = _ocr_pdf(document_path)
    if len(text) < 20:
        raise PdfTextError("OCR не смог распознать достаточно текста в документе")
    return text, True


def extract_pdf_text(path: str | Path) -> str:
    text, _ = extract_document_text(path)
    return text

