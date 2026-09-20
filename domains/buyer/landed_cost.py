"""Landed cost: list unit * qty + zone shipping + lead penalty. No network."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from domains.buyer.negotiate import LEAD_GRACE_DAYS, LEAD_PENALTY_USD_PER_DAY

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data" / "fixtures"

ZONE_SHIP = {
    "A": "ship_zone_A",
    "B": "ship_zone_B",
}


@dataclass(frozen=True)
class LandedQuote:
    vendor_id: str
    name: str
    sku: str
    qty: int
    unit_price: float
    shipping: float
    lead_days: int
    penalty: float
    landed: float
    floor: float
    moq: int
    zone: str


def load_vendors(path: Path | None = None) -> list[dict[str, Any]]:
    src = path or (FIXTURES / "vendors.csv")
    rows: list[dict[str, Any]] = []
    with src.open(encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            rows.append(
                {
                    "vendor_id": raw["vendor_id"],
                    "name": raw["name"],
                    "sku": raw["sku"],
                    "unit_price": float(raw["unit_price"]),
                    "moq": int(raw["moq"]),
                    "ship_zone_A": float(raw["ship_zone_A"]),
                    "ship_zone_B": float(raw["ship_zone_B"]),
                    "lead_days": int(raw["lead_days"]),
                    "floor": float(raw["floor"]),
                }
            )
    return rows


def load_specs(path: Path | None = None) -> list[dict[str, Any]]:
    src = path or (FIXTURES / "buyer_specs.json")
    data = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("buyer_specs.json must be a list")
    return data


def get_spec(spec_id: str, specs: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    rows = specs if specs is not None else load_specs()
    for row in rows:
        if row["id"] == spec_id:
            return dict(row)
    raise KeyError(f"unknown spec: {spec_id}")


def shipping_for(vendor: Mapping[str, Any], zone: str) -> float:
    key = ZONE_SHIP.get(zone)
    if key is None:
        raise ValueError(f"unknown zone: {zone}")
    return float(vendor[key])


def lead_penalty(lead_days: int) -> float:
    return LEAD_PENALTY_USD_PER_DAY * max(0, int(lead_days) - LEAD_GRACE_DAYS)


def eligible(vendor: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    if vendor["sku"] != spec["sku"]:
        return False
    if int(spec["qty"]) < int(vendor["moq"]):
        return False
    if int(vendor["lead_days"]) > int(spec["need_by_days"]):
        return False
    return True


def quote_vendor(vendor: Mapping[str, Any], spec: Mapping[str, Any]) -> LandedQuote:
    qty = int(spec["qty"])
    zone = str(spec["zone"])
    unit = float(vendor["unit_price"])
    ship = shipping_for(vendor, zone)
    penalty = lead_penalty(int(vendor["lead_days"]))
    return LandedQuote(
        vendor_id=str(vendor["vendor_id"]),
        name=str(vendor["name"]),
        sku=str(vendor["sku"]),
        qty=qty,
        unit_price=unit,
        shipping=ship,
        lead_days=int(vendor["lead_days"]),
        penalty=penalty,
        landed=unit * qty + ship + penalty,
        floor=float(vendor["floor"]),
        moq=int(vendor["moq"]),
        zone=zone,
    )


def rank(
    spec: Mapping[str, Any],
    vendors: Sequence[Mapping[str, Any]] | None = None,
) -> list[LandedQuote]:
    """Rank by list-price landed cost. Reservation is draft/PO only."""
    rows = vendors if vendors is not None else load_vendors()
    quotes = [quote_vendor(v, spec) for v in rows if eligible(v, spec)]
    quotes.sort(key=lambda q: (q.landed, q.unit_price, q.vendor_id))
    return quotes


def format_rank_table(spec: Mapping[str, Any], quotes: Sequence[LandedQuote]) -> str:
    header = (
        f"{spec['id']}  sku={spec['sku']}  qty={spec['qty']}  "
        f"zone={spec['zone']}  need_by_days={spec['need_by_days']}"
    )
    lines = [
        header,
        f"{'rank':<5} {'vendor':<6} {'name':<22} {'unit':>8} {'ship':>8} "
        f"{'lead':>5} {'penalty':>8} {'landed':>10}",
    ]
    for i, q in enumerate(quotes, start=1):
        lines.append(
            f"{i:<5} {q.vendor_id:<6} {q.name:<22} {q.unit_price:8.2f} {q.shipping:8.2f} "
            f"{q.lead_days:5d} {q.penalty:8.2f} {q.landed:10.2f}"
        )
    if not quotes:
        lines.append("(no eligible vendors)")
    return "\n".join(lines)
