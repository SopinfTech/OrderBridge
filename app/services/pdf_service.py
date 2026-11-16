from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import settings
from app.db.models import Order


def generate_order_pdf(order: Order) -> Path:
    settings.print_pdf_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{safe_name(order.reference)}-{int(order.updated_at.timestamp())}.pdf"
    file_path = settings.print_pdf_dir / filename

    document = SimpleDocTemplate(
        str(file_path),
        pagesize=LETTER,
        leftMargin=0.35 * inch,
        rightMargin=0.35 * inch,
        topMargin=0.35 * inch,
        bottomMargin=0.35 * inch,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SmallRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            alignment=TA_RIGHT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TopBlock",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TitleBig",
            parent=styles["Title"],
            fontName="Helvetica",
            fontSize=20,
            leading=24,
            spaceAfter=10,
            textColor=colors.HexColor("#111827"),
        )
    )

    story = []
    story.append(build_header(order, styles))
    story.append(Spacer(1, 0.28 * inch))
    story.append(Paragraph(f"Order #{order.reference} - {format_order_date(order.created_at)}", styles["TitleBig"]))
    story.append(Spacer(1, 0.12 * inch))
    story.append(build_items_table(order, styles))
    story.append(Spacer(1, 0.16 * inch))
    story.append(build_totals_table(order, styles))
    story.append(Spacer(1, 0.18 * inch))
    story.append(build_footer_details(order, styles))

    document.build(story)
    return file_path


def build_header(order: Order, styles) -> Table:
    left_lines = build_merchant_lines(order)
    right_lines = [
        order.customer_name or "Cliente",
        clean_address(order.customer_address),
        order.customer_phone or "",
        order.customer_email or "",
    ]

    left_block = Paragraph(lines_to_html(left_lines), styles["TopBlock"])
    right_block = Paragraph(lines_to_html(right_lines), styles["SmallRight"])

    table = Table([[left_block, right_block]], colWidths=[3.7 * inch, 3.7 * inch])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def build_items_table(order: Order, styles) -> Table:
    data = [
        [
            Paragraph("<b>SKU</b>", styles["Normal"]),
            Paragraph("<b>Product</b>", styles["Normal"]),
            Paragraph("<b>Price</b>", styles["Normal"]),
            Paragraph("<b>Qty</b>", styles["Normal"]),
        ]
    ]

    for item in order.items:
        sku = item.external_id or "-"
        product_lines = [item.name]
        if item.options:
            product_lines.append(", ".join(str(option) for option in item.options if option))

        data.append(
            [
                Paragraph(html_escape(sku), styles["Normal"]),
                Paragraph(lines_to_html(product_lines), styles["Normal"]),
                Paragraph(f"{order.currency} {item.unit_price:,.2f}", styles["SmallRight"]),
                Paragraph(f"{item.quantity:g}", styles["SmallRight"]),
            ]
        )

    table = Table(
        data,
        colWidths=[1.4 * inch, 4.2 * inch, 1.0 * inch, 0.75 * inch],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
            ]
        )
    )
    return table


def build_totals_table(order: Order, styles) -> Table:
    data = [
        ["TOTAL", money(order.total, order.currency)],
    ]

    table = Table(data, colWidths=[2.0 * inch, 2.0 * inch], hAlign="RIGHT")
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("FONTSIZE", (0, -1), (-1, -1), 12),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def build_footer_details(order: Order, styles) -> Table:
    raw_payload = order.raw_payload if isinstance(order.raw_payload, dict) else {}
    customer_note = (
        raw_payload.get("customer_note")
        or raw_payload.get("notes")
        or raw_payload.get("comment")
        or order.fulfillment_notes
        or ""
    )
    delivery_time_slot = format_delivery_slot(
        raw_payload.get("selected_delivery_slot")
        or raw_payload.get("delivery_time_slot")
        or raw_payload.get("delivery_window")
        or raw_payload.get("time_slot")
    )
    delivery_address = (
        raw_payload.get("delivery_address")
        or raw_payload.get("shipping_address")
        or order.customer_address
        or "-"
    )
    delivery_contact_lines = build_delivery_contact_lines(order, delivery_address)
    payment_method = format_payment_method(
        order.payment_method
        or raw_payload.get("payment_method")
        or raw_payload.get("payment_type")
        or raw_payload.get("payment_mode")
        or "-"
    )
    delivery_method = format_delivery_method(
        order.fulfillment_method
        or raw_payload.get("shipping_method")
        or raw_payload.get("shipping_type")
        or raw_payload.get("delivery_method")
        or "-"
    )

    left_block = Paragraph(
        f"""
        <b>Delivery time slot</b><br/>
        {delivery_method}<br/>
        {delivery_time_slot}<br/>
        <br/>
        <b>Payment method</b><br/>
        {payment_method}
        {build_customer_note_html(customer_note)}
        """.strip(),
        styles["TopBlock"],
    )

    right_block = Paragraph(
        f"""
        <b>Delivery address</b><br/>
        {lines_to_html(delivery_contact_lines)}
        """.strip(),
        styles["SmallRight"],
    )

    table = Table([[left_block, right_block]], colWidths=[4.2 * inch, 3.15 * inch])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def lines_to_html(lines: list[str]) -> str:
    cleaned = [html_escape(line) for line in lines if line]
    return "<br/>".join(cleaned) if cleaned else "-"


def build_delivery_contact_lines(order: Order, delivery_address) -> list[str]:
    address_text = clean_address(delivery_address)
    return [
        order.customer_name or "",
        address_text if address_text != "-" else "",
        order.customer_phone or "",
        order.customer_email or "",
    ]


def build_merchant_lines(order: Order) -> list[str]:
    raw_payload = order.raw_payload if isinstance(order.raw_payload, dict) else {}
    merchant = first_dict(
        raw_payload.get("merchant"),
        raw_payload.get("store"),
        raw_payload.get("shop"),
        raw_payload.get("business"),
        raw_payload.get("company"),
        raw_payload.get("seller"),
        raw_payload.get("vendor"),
        raw_payload.get("pickup_store"),
    )
    merchant_address = first_dict(
        raw_payload.get("merchant_address"),
        raw_payload.get("store_address"),
        raw_payload.get("pickup_address"),
        merchant.get("address") if merchant else None,
    )

    return [
        first_value(
            merchant.get("name") if merchant else None,
            merchant.get("company_name") if merchant else None,
            settings.merchant_name,
        ),
        first_value(
            merchant.get("address_line1") if merchant else None,
            merchant_address.get("address_line1") if merchant_address else None,
            merchant_address.get("address") if merchant_address else None,
            settings.merchant_address_line1,
        ),
        first_value(
            merchant.get("address_line2") if merchant else None,
            merchant.get("city_state_zip") if merchant else None,
            merchant_address.get("address_line2") if merchant_address else None,
            merchant_address.get("localized_address") if merchant_address else None,
            settings.merchant_address_line2,
        ),
        first_value(
            merchant.get("country") if merchant else None,
            merchant_address.get("country") if merchant_address else None,
            settings.merchant_country,
        ),
        first_value(
            merchant.get("phone") if merchant else None,
            merchant_address.get("phone") if merchant_address else None,
            settings.merchant_phone,
        ),
        first_value(
            merchant.get("email") if merchant else None,
            merchant_address.get("email") if merchant_address else None,
            settings.merchant_email,
        ),
    ]


def first_dict(*values) -> dict:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def first_value(*values) -> str:
    for value in values:
        if value is None:
            continue
        cleaned = str(value).strip()
        if cleaned:
            return cleaned
    return ""


def html_escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def clean_address(value) -> str:
    if isinstance(value, dict):
        localized = value.get("localized_address")
        if localized:
            value = localized
        else:
            parts = [
                value.get("name"),
                value.get("address"),
                value.get("address_1"),
                value.get("address_2"),
                value.get("street"),
                value.get("city"),
                value.get("state"),
                value.get("zip") or value.get("zipcode") or value.get("postcode"),
                value.get("country"),
                value.get("phone") or value.get("phone_number"),
                value.get("email"),
            ]
            value = ", ".join(str(part).strip() for part in parts if part)

    text = str(value or "").replace("\r", "\n")
    lines = []
    for raw_line in text.split("\n"):
        cleaned_line = " ".join(raw_line.split()).strip(" ,")
        if cleaned_line:
            lines.append(cleaned_line)
    if not lines:
        return "-"
    return ", ".join(lines)


def build_customer_note_html(value: str) -> str:
    cleaned = " ".join(str(value or "").split()).strip()
    if not cleaned:
        return ""
    return f"<br/><br/><b>Customer note</b><br/>{html_escape(cleaned)}"


def format_delivery_slot(value) -> str:
    if isinstance(value, dict):
        slot_date = str(value.get("date") or "").strip()
        slot_start = str(value.get("slot_start") or value.get("start") or "").strip()
        slot_end = str(value.get("slot_end") or value.get("end") or "").strip()
        parts = [html_escape(part) for part in [slot_date, build_slot_range(slot_start, slot_end)] if part]
        return "<br/>".join(parts) if parts else "-"

    cleaned = " ".join(str(value or "").split()).strip()
    return html_escape(cleaned) if cleaned else "-"


def build_slot_range(start: str, end: str) -> str:
    if start and end:
        return f"Between {start} and {end}"
    return start or end or ""


def format_payment_method(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned or cleaned == "-":
        return "-"
    return html_escape(cleaned.replace("_", " ").title())


def format_delivery_method(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned or cleaned == "-":
        return "-"
    return html_escape(cleaned.replace("_", " ").title())


def format_order_date(value: datetime) -> str:
    if not hasattr(value, "strftime"):
        return str(value)

    hour = value.hour % 12 or 12
    minute = value.minute
    suffix = "AM" if value.hour < 12 else "PM"
    return f"{value.month}/{value.day}/{str(value.year)[2:]}, {hour}:{minute:02d} {suffix}"


def money(value: float, currency: str) -> str:
    return f"{currency} {value:,.2f}"


def safe_name(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "-" for character in value).strip("-")
