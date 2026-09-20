"""Rank synthetic trucks for a load. Exact equip only; no hos_h filter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from domains.lane.cost_model import Quote, quote_truck

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data" / "fixtures"


def load_trucks(path: Path | None = None) -> list[dict[str, Any]]:
    src = path or (FIXTURES / "trucks.json")
    data = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("trucks.json must be a list")
    return data


def load_loads(path: Path | None = None) -> list[dict[str, Any]]:
    src = path or (FIXTURES / "loads.json")
    data = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("loads.json must be a list")
    return data


def get_load(load_id: str, loads: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    rows = loads if loads is not None else load_loads()
    for row in rows:
        if row["id"] == load_id:
            return dict(row)
    raise KeyError(f"unknown load: {load_id}")


def get_truck(truck_id: str, trucks: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    rows = trucks if trucks is not None else load_trucks()
    for row in rows:
        if row["id"] == truck_id:
            return dict(row)
    raise KeyError(f"unknown truck: {truck_id}")


def rank(
    load: Mapping[str, Any],
    trucks: Sequence[Mapping[str, Any]] | None = None,
) -> list[Quote]:
    """Quote every same-equip truck. Do not drop on remaining hos_h."""
    fleet = trucks if trucks is not None else load_trucks()
    wanted = load["equip"]
    quotes = [quote_truck(truck, load) for truck in fleet if truck["equip"] == wanted]
    quotes.sort(key=lambda q: (q.usd_per_mi, q.deadhead_mi, q.truck_id))
    return quotes


def format_rank_table(load: Mapping[str, Any], quotes: Sequence[Quote]) -> str:
    header = (
        f"{load['id']}  {load['origin']} -> {load['dest']}  "
        f"{load['miles_hint']} mi  {load['grade_band']}"
    )
    lines = [
        header,
        f"{'rank':<5} {'truck':<6} {'deadhead_mi':>12} {'energy':>14} "
        f"{'drive_h':>8} {'usd':>10} {'usd_per_mi':>10}",
    ]
    for i, q in enumerate(quotes, start=1):
        energy = f"{q.energy_amount:.1f} {q.energy_unit}"
        lines.append(
            f"{i:<5} {q.truck_id:<6} {q.deadhead_mi:12.1f} {energy:>14} "
            f"{q.drive_h:8.2f} {q.usd:10.2f} {q.usd_per_mi:10.3f}"
        )
    if not quotes:
        lines.append("(no matching equipment)")
    return "\n".join(lines)
