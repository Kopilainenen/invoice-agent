from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WebAssetsTest(unittest.TestCase):
    def test_required_assets_exist(self) -> None:
        for relative_path in ("web/index.html", "web/styles.css", "web/app.js"):
            with self.subTest(path=relative_path):
                path = ROOT / relative_path
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 100)

    def test_index_contains_primary_workflow_controls(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        for element_id in (
            'id="file-input"',
            'id="extract-button"',
            'id="invoice-form"',
            'id="validation-summary"',
            'id="export-csv"',
            'id="export-xlsx"',
        ):
            with self.subTest(element=element_id):
                self.assertIn(element_id, html)

    def test_client_validation_checks_requisites_and_totals(self) -> None:
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        for marker in ("innIsValid", "количество × цена", "Сумма без НДС + НДС"):
            with self.subTest(marker=marker):
                self.assertIn(marker, script)


if __name__ == "__main__":
    unittest.main()

