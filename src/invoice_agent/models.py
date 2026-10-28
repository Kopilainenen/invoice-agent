from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Party:
    name: str | None = None
    inn: str | None = None
    kpp: str | None = None
    bank_account: str | None = None
    bank_name: str | None = None
    bik: str | None = None


@dataclass(slots=True)
class LineItem:
    line_number: int
    name: str
    unit: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    line_total: float | None = None


@dataclass(slots=True)
class Invoice:
    source_file: str
    document_type: str = "invoice_for_payment"
    supplier: Party = field(default_factory=Party)
    buyer: Party | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    currency: str | None = "RUB"
    subtotal_amount: float | None = None
    vat_amount: float | None = None
    vat_rate: float | None = None
    total_amount: float | None = None
    payment_deadline: str | None = None
    contract_number: str | None = None
    items: list[LineItem] = field(default_factory=list)
    confidence: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

