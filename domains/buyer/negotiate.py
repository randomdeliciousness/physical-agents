"""Mandate numbers and local negotiation draft. Never send."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from domains.buyer.landed_cost import LandedQuote

# Encoded from mandates/default.md — do not parse the markdown for arithmetic.
RESERVATION_OFF = 0.10
MAX_ROUNDS = 3
LEAD_PENALTY_USD_PER_DAY = 25.0
LEAD_GRACE_DAYS = 7


@dataclass(frozen=True)
class Reservation:
    unit: float
    list_price: float
    floor: float
    meets_ten_percent: bool
    walk_if_not_met: bool


def reservation_unit(list_price: float, floor: float | None) -> Reservation:
    """10% off list, never below floor. Walk rather than breach floor."""
    target = float(list_price) * (1.0 - RESERVATION_OFF)
    floor_v = float(floor) if floor is not None else 0.0
    if target < floor_v:
        return Reservation(
            unit=floor_v,
            list_price=float(list_price),
            floor=floor_v,
            meets_ten_percent=False,
            walk_if_not_met=True,
        )
    return Reservation(
        unit=target,
        list_price=float(list_price),
        floor=floor_v,
        meets_ten_percent=True,
        walk_if_not_met=True,
    )


def draft_counter(spec: Mapping[str, object], quote: LandedQuote) -> str:
    res = reservation_unit(quote.unit_price, quote.floor)
    if res.meets_ten_percent:
        stance = (
            f"Hold reservation ${res.unit:.4f} for {MAX_ROUNDS} rounds, then walk. "
            "Do not go below floor."
        )
    else:
        list_cut = quote.unit_price * (1.0 - RESERVATION_OFF)
        stance = (
            f"10% off list is ${list_cut:.4f}, below floor ${res.floor:.4f}. "
            "Target floor and walk; do not go under cost."
        )
    return (
        "NEGOTIATION DRAFT (not sent)\n"
        f"Spec {spec['id']} sku={spec['sku']} qty={spec['qty']} zone={spec['zone']}\n"
        f"Vendor {quote.vendor_id} {quote.name}\n"
        f"List unit ${quote.unit_price:.4f}  floor ${quote.floor:.4f}\n"
        f"Reservation ${res.unit:.4f} ({RESERVATION_OFF:.0%} off list or walk)\n"
        f"Max rounds: {MAX_ROUNDS}\n"
        f"Round 1: counter at ${res.unit:.4f}\n"
        f"Round 2: hold ${res.unit:.4f}\n"
        f"Round 3: ${res.unit:.4f} or walk\n"
        f"{stance}\n"
        "Do not send off-box. Do not email.\n"
    )
