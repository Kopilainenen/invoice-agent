from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "dea_test_invoice.pdf"


def register_fonts() -> tuple[str, str]:
    regular_candidates = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
    ]
    bold_candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\calibrib.ttf"),
    ]
    regular = next(path for path in regular_candidates if path.exists())
    bold = next(path for path in bold_candidates if path.exists())
    pdfmetrics.registerFont(TTFont("InvoiceRegular", str(regular)))
    pdfmetrics.registerFont(TTFont("InvoiceBold", str(bold)))
    return "InvoiceRegular", "InvoiceBold"


def money(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def build_invoice() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    regular, bold = register_fonts()

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Тестовый счет D.E.A. Fitness Supply",
        author="Synthetic fixture for Invoice Agent MVP",
    )

    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "Base",
        parent=styles["Normal"],
        fontName=regular,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1F2937"),
    )
    small = ParagraphStyle("Small", parent=base, fontSize=7.5, leading=10)
    tiny = ParagraphStyle("Tiny", parent=base, fontSize=6.8, leading=8.5)
    bold_style = ParagraphStyle("Bold", parent=base, fontName=bold)
    title = ParagraphStyle(
        "Title",
        parent=base,
        fontName=bold,
        fontSize=15,
        leading=18,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#111827"),
    )
    brand = ParagraphStyle(
        "Brand",
        parent=base,
        fontName=bold,
        fontSize=18,
        leading=20,
        textColor=colors.HexColor("#0F766E"),
    )
    right = ParagraphStyle("Right", parent=base, alignment=TA_RIGHT)
    center_small = ParagraphStyle("CenterSmall", parent=small, alignment=TA_CENTER)
    white_bold = ParagraphStyle(
        "WhiteBold",
        parent=base,
        fontName=bold,
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    story = []

    test_banner = Table(
        [[Paragraph("ТЕСТОВЫЙ ДОКУМЕНТ - НЕ ЯВЛЯЕТСЯ ПЛАТЁЖНЫМ ДОКУМЕНТОМ", white_bold)]],
        colWidths=[178 * mm],
    )
    test_banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#B91C1C")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#7F1D1D")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([test_banner, Spacer(1, 7 * mm)])

    header = Table(
        [
            [
                Paragraph("D.E.A.<br/><font size='9'>FITNESS SUPPLY</font>", brand),
                Paragraph(
                    "Поставщик фитнес-оборудования и аксессуаров<br/>"
                    "Сеть из 6 тестовых магазинов<br/>"
                    "Москва · Санкт-Петербург · Казань · Екатеринбург · Самара · Новосибирск",
                    right,
                ),
            ]
        ],
        colWidths=[62 * mm, 116 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 1.2, colors.HexColor("#0F766E")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([header, Spacer(1, 5 * mm)])

    bank_data = [
        [Paragraph("Банк получателя", small), Paragraph("БИК", small), Paragraph("Счёт банка", small)],
        [
            Paragraph("АО «ТЕСТ БАНК»", bold_style),
            Paragraph("044500000", bold_style),
            Paragraph("30101810000000000000", bold_style),
        ],
        [Paragraph("Получатель", small), Paragraph("ИНН / КПП", small), Paragraph("Расчётный счёт", small)],
        [
            Paragraph("ООО «Д.Е.А. ФИТНЕС САПЛАЙ»", bold_style),
            Paragraph("7712345678 / 771201001", bold_style),
            Paragraph("40702810000000000001", bold_style),
        ],
    ]
    bank = Table(bank_data, colWidths=[76 * mm, 40 * mm, 62 * mm], rowHeights=[7 * mm] * 4)
    bank.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9CA3AF")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#E5E7EB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([bank, Spacer(1, 7 * mm)])

    story.append(Paragraph("Счёт на оплату № DEA-1042 от 23 октября 2026 г.", title))
    story.append(Spacer(1, 2 * mm))

    parties = Table(
        [
            [Paragraph("Поставщик:", bold_style), Paragraph("ООО «Д.Е.А. ФИТНЕС САПЛАЙ», ИНН 7712345678, КПП 771201001", base)],
            [Paragraph("Покупатель:", bold_style), Paragraph("ООО «ОЛИМП-ФИТНЕС», ИНН 7812345670, КПП 781201001", base)],
            [Paragraph("Основание:", bold_style), Paragraph("Договор поставки № OF-6/2026 от 01.09.2026", base)],
            [Paragraph("Срок оплаты:", bold_style), Paragraph("до 30 октября 2026 г.", base)],
        ],
        colWidths=[27 * mm, 151 * mm],
    )
    parties.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([parties, Spacer(1, 4 * mm)])

    items = [
        ("1", "Беговая дорожка D.E.A. RUN T4", "шт.", 6, 118000.00),
        ("2", "Эллиптический тренажёр D.E.A. E8", "шт.", 6, 84500.00),
        ("3", "Комплект регулируемых гантелей 2-24 кг", "компл.", 12, 26750.00),
        ("4", "Коврик тренировочный PRO 8 мм", "шт.", 60, 2850.00),
        ("5", "Стойка для хранения инвентаря", "шт.", 6, 32900.00),
        ("6", "Доставка по 6 адресам магазинов", "усл.", 1, 96000.00),
    ]

    item_rows = [
        [
            Paragraph("№", center_small),
            Paragraph("Наименование", center_small),
            Paragraph("Ед.", center_small),
            Paragraph("Кол-во", center_small),
            Paragraph("Цена, ₽", center_small),
            Paragraph("Сумма, ₽", center_small),
        ]
    ]
    subtotal = 0.0
    for number, name, unit, quantity, price in items:
        line_total = quantity * price
        subtotal += line_total
        item_rows.append(
            [
                Paragraph(number, center_small),
                Paragraph(name, small),
                Paragraph(unit, center_small),
                Paragraph(str(quantity), center_small),
                Paragraph(money(price), right),
                Paragraph(money(line_total), right),
            ]
        )

    items_table = Table(
        item_rows,
        colWidths=[9 * mm, 82 * mm, 16 * mm, 18 * mm, 25 * mm, 28 * mm],
        repeatRows=1,
    )
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D1FAE5")),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#9CA3AF")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([items_table, Spacer(1, 4 * mm)])

    vat_rate = 20.0
    vat_amount = round(subtotal * vat_rate / 100, 2)
    total = subtotal + vat_amount
    totals = Table(
        [
            [Paragraph("Итого без НДС:", bold_style), Paragraph(f"{money(subtotal)} ₽", right)],
            [Paragraph("НДС 20%:", bold_style), Paragraph(f"{money(vat_amount)} ₽", right)],
            [Paragraph("Всего к оплате:", bold_style), Paragraph(f"{money(total)} ₽", ParagraphStyle("TotalRight", parent=right, fontName=bold, fontSize=11))],
        ],
        colWidths=[45 * mm, 42 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#0F766E")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([totals, Spacer(1, 6 * mm)])

    amount_words = "Два миллиона четыреста тысяч четыреста восемьдесят рублей 00 копеек"
    summary = KeepTogether(
        [
            Paragraph(f"Всего наименований: {len(items)}, на сумму {money(total)} ₽", base),
            Paragraph(f"<b>{amount_words}</b>", base),
            Spacer(1, 3 * mm),
            Paragraph(
                "Назначение: оборудование и аксессуары для оснащения шести магазинов сети. "
                "Адреса доставки согласуются в приложении к договору.",
                base,
            ),
        ]
    )
    story.append(summary)
    story.append(Spacer(1, 8 * mm))

    signatures = Table(
        [
            [Paragraph("Руководитель", bold_style), "", Paragraph("Е.А. Воронова", base)],
            ["", Paragraph("подпись", tiny), ""],
            [Paragraph("Главный бухгалтер", bold_style), "", Paragraph("М.С. Левина", base)],
            ["", Paragraph("подпись", tiny), ""],
        ],
        colWidths=[42 * mm, 56 * mm, 60 * mm],
    )
    signatures.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (1, 0), (1, 0), 0.6, colors.HexColor("#4B5563")),
                ("LINEBELOW", (1, 2), (1, 2), 0.6, colors.HexColor("#4B5563")),
                ("ALIGN", (1, 1), (1, 3), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("TOPPADDING", (0, 2), (-1, 2), 8),
            ]
        )
    )
    story.append(signatures)
    story.append(Spacer(1, 5 * mm))
    story.append(
        Paragraph(
            "Все организации, реквизиты, лица, суммы и адреса в этом документе вымышлены. "
            "Файл создан исключительно для тестирования распознавания документов.",
            ParagraphStyle("Disclaimer", parent=tiny, textColor=colors.HexColor("#6B7280"), alignment=TA_CENTER),
        )
    )

    doc.build(story)
    return OUTPUT


if __name__ == "__main__":
    print(build_invoice())

