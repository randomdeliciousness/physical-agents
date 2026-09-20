"""Local PO markdown. Write only when approved=true. Never send."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from domains.buyer.landed_cost import LandedQuote
from domains.buyer.negotiate import reservation_unit

OUT_NAME = "po_{spec_id}.md"


def po_total(quote: LandedQuote) -> float:
    res = reservation_unit(quote.unit_price, quote.floor)
    return res.unit * quote.qty + quote.shipping + quote.penalty


def po_path(spec_id: str, dest: Path) -> Path:
    return dest / OUT_NAME.format(spec_id=spec_id)


def render_po(spec: Mapping[str, object], quote: LandedQuote) -> str:
    res = reservation_unit(quote.unit_price, quote.floor)
    total = po_total(quote)
    return (
        f"# PO draft {spec['id']}\n"
        "\n"
        "Not sent. Not a live purchase order.\n"
        "\n"
        f"- Spec: {spec['id']}\n"
        f"- SKU: {spec['sku']}\n"
        f"- Qty: {spec['qty']}\n"
        f"- Zone: {spec['zone']}\n"
        f"- Vendor: {quote.vendor_id} {quote.name}\n"
        f"- List unit: ${quote.unit_price:.4f}\n"
        f"- Reservation unit: ${res.unit:.4f}\n"
        f"- Shipping: ${quote.shipping:.2f}\n"
        f"- Lead penalty: ${quote.penalty:.2f}\n"
        f"- Total: ${total:.2f}\n"
        "\n"
        "Human approval recorded locally. Do not email the vendor.\n"
    )


def write_po(
    spec: Mapping[str, object],
    quote: LandedQuote,
    *,
    approved: bool,
    dest: Path,
    cap_usd: float | None,
) -> Path | None:
    if approved is not True:
        return None
    total = po_total(quote)
    if cap_usd is not None and total > cap_usd:
        return None
    dest.mkdir(parents=True, exist_ok=True)
    path = po_path(str(spec["id"]), dest)
    path.write_text(render_po(spec, quote), encoding="utf-8")
    return path
