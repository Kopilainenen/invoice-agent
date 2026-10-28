from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from invoice_agent.extractor import _extract_line_items, extract_invoice  # noqa: E402


class DeaInvoiceExtractionTest(unittest.TestCase):
    def test_extracts_expected_invoice_fields(self) -> None:
        pdf_path = ROOT / "output" / "pdf" / "dea_test_invoice.pdf"
        expected_path = ROOT / "fixtures" / "expected" / "dea_test_invoice.json"

        actual = extract_invoice(pdf_path).to_dict()
        expected = json.loads(expected_path.read_text(encoding="utf-8"))

        comparable_fields = [
            "source_file",
            "document_type",
            "supplier",
            "buyer",
            "invoice_number",
            "invoice_date",
            "currency",
            "subtotal_amount",
            "vat_amount",
            "vat_rate",
            "total_amount",
            "payment_deadline",
            "contract_number",
            "items",
            "warnings",
        ]
        for field_name in comparable_fields:
            with self.subTest(field=field_name):
                self.assertEqual(expected[field_name], actual[field_name])

    def test_important_fields_have_high_confidence(self) -> None:
        pdf_path = ROOT / "output" / "pdf" / "dea_test_invoice.pdf"
        actual = extract_invoice(pdf_path).to_dict()

        for field_name in (
            "supplier.inn",
            "invoice_number",
            "invoice_date",
            "total_amount",
        ):
            with self.subTest(field=field_name):
                self.assertGreaterEqual(actual["confidence"][field_name], 0.95)

    def test_extracts_all_line_items(self) -> None:
        pdf_path = ROOT / "output" / "pdf" / "dea_test_invoice.pdf"
        actual = extract_invoice(pdf_path).to_dict()
        self.assertEqual(6, len(actual["items"]))
        self.assertEqual("Беговая дорожка D.E.A. RUN T4", actual["items"][0]["name"])
        self.assertEqual(708000.0, actual["items"][0]["line_total"])
        self.assertEqual("Доставка по 6 адресам магазинов", actual["items"][-1]["name"])

    def test_recovers_line_items_from_typical_ocr_text(self) -> None:
        text = """Беговая дорожка D E A: RUN Т4 ШТ 118 000,00 708 000,00
Комплект регулируемых гантелей 2-24 кг КОмПЛ: 12 26 750,00 321 00О ,00
Коврик тренировочный PRO 8 мм ШТ 2 850,00 171 000,00"""
        items = _extract_line_items(text)
        self.assertEqual(3, len(items))
        self.assertEqual(6.0, items[0].quantity)
        self.assertEqual(26750.0, items[1].unit_price)
        self.assertEqual(60.0, items[2].quantity)


if __name__ == "__main__":
    unittest.main()

