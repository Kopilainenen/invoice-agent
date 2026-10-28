from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .models import Invoice, LineItem, Party
from .pdf_text import extract_document_text


RU_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


def _first(pattern: str, text: str, flags: int = re.IGNORECASE) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def _parse_ru_date(value: str | None) -> str | None:
    if not value:
        return None

    value = value.strip().rstrip(".:;,")
    numeric = re.fullmatch(r"(\d{1,2})[.](\d{1,2})[.](\d{4})", value)
    if numeric:
        day, month, year = map(int, numeric.groups())
        return date(year, month, day).isoformat()

    words = re.fullmatch(
        r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})(?:\s*г[.]?)?",
        value.strip(),
        re.IGNORECASE,
    )
    if not words:
        return None
    day = int(words.group(1))
    month = RU_MONTHS.get(words.group(2).lower())
    year = int(words.group(3))
    if month is None:
        return None
    return date(year, month, day).isoformat()


def _parse_money(value: str | None) -> float | None:
    if not value:
        return None
    normalized = (
        value.replace("О", "0").replace("O", "0")
        .replace("₽", "").replace(" ", "").replace("\u00a0", "")
    )
    normalized = normalized.replace(",", ".")
    try:
        return round(float(normalized), 2)
    except ValueError:
        return None


def _extract_party(line: str | None) -> Party | None:
    if not line:
        return None
    name = _first(r"^(.+?),\s*ИНН\s+\d", line)
    inn = _first(r"\bИНН\s+(\d{10}|\d{12})\b", line)
    kpp = _first(r"\bКПП\s+(\d{9})\b", line)
    if not any((name, inn, kpp)):
        return None
    return Party(name=name, inn=inn, kpp=kpp)


def _required_confidence(value: object, present: float = 0.99) -> float:
    return present if value not in (None, "") else 0.0


def _parse_quantity(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def _extract_line_items(text: str) -> list[LineItem]:
    items: list[LineItem] = []
    pattern = re.compile(
        r"^(\d+)\s+(.+?)\s+([^\s]+)\s+([\d.,]+)\s+"
        r"([\d\s]+[,]\d{2})\s+([\d\s]+[,]\d{2})$",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        items.append(
            LineItem(
                line_number=int(match.group(1)),
                name=match.group(2).strip(),
                unit=match.group(3).strip(),
                quantity=_parse_quantity(match.group(4)),
                unit_price=_parse_money(match.group(5)),
                line_total=_parse_money(match.group(6)),
            )
        )
    if items:
        return items

    # OCR often loses the small row number and sometimes the quantity, while
    # preserving the larger description, price and total columns.
    money_pattern = re.compile(r"(?:\d{1,3}(?: \d{3})+|\d+)\s*[,]\s*\d{2}")
    for line in text.splitlines():
        normalized_line = line.replace("О", "0").replace("O", "0")
        money_matches = list(money_pattern.finditer(normalized_line))
        if len(money_matches) < 2:
            continue
        unit_price_match, line_total_match = money_matches[-2:]
        prefix = line[: unit_price_match.start()].strip()
        prefix_match = re.match(
            r"^(.+?)\s+(шт|усл|компл)[.:]*(?:\s+(\d+(?:[.,]\d+)?))?$",
            prefix,
            re.IGNORECASE,
        )
        if not prefix_match:
            continue
        unit_price = _parse_money(unit_price_match.group(0))
        line_total = _parse_money(line_total_match.group(0))
        quantity = _parse_quantity(prefix_match.group(3))
        if quantity is None and unit_price and line_total:
            inferred = line_total / unit_price
            quantity = round(inferred, 3)
            if abs(quantity - round(quantity)) < 0.001:
                quantity = float(round(quantity))
        items.append(
            LineItem(
                line_number=len(items) + 1,
                name=prefix_match.group(1).strip(),
                unit=prefix_match.group(2).lower().rstrip(".:"),
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
        )
    return items


def extract_invoice(path: str | Path) -> Invoice:
    pdf_path = Path(path)
    text, used_ocr = extract_document_text(pdf_path)

    header = re.search(
        r"Сч[её]т\s+на\s+оплату\s+(?:№|N[°oгg]?)\s*([^\s]+)\s+от\s+"
        r"(\d{1,2}\s+[А-Яа-яЁё]+\s+\d{4}\s*г[.]?|\d{1,2}[.]\d{1,2}[.]\d{4})",
        text,
        re.IGNORECASE,
    )
    invoice_number = header.group(1).strip() if header else None
    invoice_date = _parse_ru_date(header.group(2)) if header else None

    supplier_line = _first(r"^Поставщик:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    buyer_line = _first(r"^Покупатель:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    supplier = _extract_party(supplier_line) or Party()
    buyer = _extract_party(buyer_line)

    recipient_block = re.search(
        r"Получатель\s+ИНН\s*(?:/\s*)?КПП\s+Расч[её]тный\s+сч[её]т\s*\n"
        r"(.+?)\s+(\d{10}|\d{12})\s*(?:/\s*)?(\d{9})\s+(\d{20})",
        text,
        re.IGNORECASE,
    )
    if recipient_block:
        supplier.name = supplier.name or recipient_block.group(1).strip()
        supplier.inn = supplier.inn or recipient_block.group(2)
        supplier.kpp = supplier.kpp or recipient_block.group(3)
        supplier.bank_account = recipient_block.group(4)

    bank_block = re.search(
        r"Банк\s+получателя\s+БИК\s+Сч[её]т\s+банка\s*\n"
        r"(.+?)\s+(\d{9})\s+(\d{20})",
        text,
        re.IGNORECASE,
    )
    if bank_block:
        supplier.bank_name = bank_block.group(1).strip()
        supplier.bik = bank_block.group(2)

    payment_date_text = _first(
        r"^Срок\s+оплаты:\s*до\s+(.+?)\s*$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    contract_number = _first(
        r"^Основание:\s*.*?(?:№|N[°oгg]?)\s*([^\s]+)",
        text,
        re.IGNORECASE | re.MULTILINE,
    )

    subtotal = _parse_money(
        _first(r"Итого\s+без\s+НДС:\s*([\dОO\s]+[,]\d{2})", text)
    )
    vat_match = re.search(
        r"НДС\s+(\d+(?:[.,]\d+)?)%:\s*([\dОO\s]+[,]\d{2})",
        text,
        re.IGNORECASE,
    )
    vat_rate = float(vat_match.group(1).replace(",", ".")) if vat_match else None
    vat_amount = _parse_money(vat_match.group(2)) if vat_match else None
    total = _parse_money(
        _first(r"Всего\s+к\s+оплате:\s*([\dОO\s]+[,]\d{2})", text)
    )
    items = _extract_line_items(text)

    invoice = Invoice(
        source_file=pdf_path.name,
        supplier=supplier,
        buyer=buyer,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        subtotal_amount=subtotal,
        vat_amount=vat_amount,
        vat_rate=vat_rate,
        total_amount=total,
        payment_deadline=_parse_ru_date(payment_date_text),
        contract_number=contract_number,
        items=items,
    )

    confidence_values = {
        "supplier.name": supplier.name,
        "supplier.inn": supplier.inn,
        "supplier.kpp": supplier.kpp,
        "supplier.bank_account": supplier.bank_account,
        "supplier.bank_name": supplier.bank_name,
        "supplier.bik": supplier.bik,
        "buyer.name": buyer.name if buyer else None,
        "buyer.inn": buyer.inn if buyer else None,
        "buyer.kpp": buyer.kpp if buyer else None,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "subtotal_amount": subtotal,
        "vat_amount": vat_amount,
        "vat_rate": vat_rate,
        "total_amount": total,
        "payment_deadline": invoice.payment_deadline,
        "contract_number": contract_number,
    }
    invoice.confidence = {
        field_name: _required_confidence(value, present=0.72 if used_ocr else 0.99)
        for field_name, value in confidence_values.items()
    }

    if "ТЕСТОВЫЙ ДОКУМЕНТ" in text.upper():
        invoice.warnings.append(
            "Документ содержит синтетические реквизиты и предназначен только для тестирования"
        )

    if used_ocr:
        invoice.warnings.append(
            "Текст получен с помощью OCR — внимательно проверьте реквизиты и суммы"
        )

    if subtotal is not None and vat_amount is not None and total is not None:
        if abs((subtotal + vat_amount) - total) > 0.01:
            invoice.warnings.append("Итоговая сумма не совпадает с суммой без НДС и НДС")

    for item in items:
        if None not in (item.quantity, item.unit_price, item.line_total):
            calculated = round(item.quantity * item.unit_price, 2)
            if abs(calculated - item.line_total) > 0.01:
                invoice.warnings.append(
                    f"Позиция {item.line_number}: количество × цена не равно сумме"
                )

    if not items:
        invoice.warnings.append("Не удалось извлечь товарные позиции")

    missing = [
        name
        for name, value in confidence_values.items()
        if value in (None, "")
    ]
    if missing:
        invoice.warnings.append("Не найдены поля: " + ", ".join(missing))

    return invoice

