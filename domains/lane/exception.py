"""Late-to-appointment checks, one local SMS draft, dual delivery confirm."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from domains.lane.cost_model import (
    AT_DEST_MI,
    CRUISE_MPH,
    LATE_GRACE_MIN,
    haversine_mi,
    parse_ts,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data" / "fixtures"
OUT = ROOT / "demos" / "out"

PARTIES = frozenset({"driver", "receiver"})


@dataclass(frozen=True)
class Crumb:
    truck_id: str
    ts: datetime
    lat: float
    lon: float
    note: str


@dataclass(frozen=True)
class LateCheck:
    late: bool
    kind: str  # pickup | delivery | ok | no_crumb
    eta: datetime | None
    appointment: datetime | None
    note: str


def load_breadcrumbs(path: Path | None = None) -> list[Crumb]:
    src = path or (FIXTURES / "gps_breadcrumbs.csv")
    rows: list[Crumb] = []
    with src.open(encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            rows.append(
                Crumb(
                    truck_id=raw["truck_id"],
                    ts=parse_ts(raw["ts"]),
                    lat=float(raw["lat"]),
                    lon=float(raw["lon"]),
                    note=raw.get("note") or "",
                )
            )
    rows.sort(key=lambda c: (c.truck_id, c.ts))
    return rows


def crumbs_for(truck_id: str, crumbs: Sequence[Crumb] | None = None) -> list[Crumb]:
    rows = crumbs if crumbs is not None else load_breadcrumbs()
    return [c for c in rows if c.truck_id == truck_id]


def _eta(ts: datetime, miles: float) -> datetime:
    return ts + timedelta(hours=miles / CRUISE_MPH)


def is_late(
    load: Mapping[str, Any],
    crumbs: Sequence[Crumb],
) -> LateCheck:
    """Pickup+15 first. A Dallas delivery ETA must not hide a missed pickup."""
    if not crumbs:
        return LateCheck(False, "no_crumb", None, None, "no breadcrumbs")
    last = crumbs[-1]
    dest_mi = haversine_mi(last.lat, last.lon, float(load["dlat"]), float(load["dlon"]))
    pickup = parse_ts(str(load["pickup"]))
    delivery = parse_ts(str(load["delivery"]))
    grace = timedelta(minutes=LATE_GRACE_MIN)
    at_dest = dest_mi <= AT_DEST_MI
    if not at_dest:
        origin_mi = haversine_mi(last.lat, last.lon, float(load["olat"]), float(load["olon"]))
        eta_pu = _eta(last.ts, origin_mi)
        if eta_pu > pickup + grace:
            return LateCheck(
                True,
                "pickup",
                eta_pu,
                pickup,
                f"late to pickup (eta {eta_pu.isoformat()} > {pickup.isoformat()} + {LATE_GRACE_MIN}m)",
            )
    eta_del = _eta(last.ts, dest_mi)
    if eta_del > delivery + grace:
        return LateCheck(
            True,
            "delivery",
            eta_del,
            delivery,
            f"late to delivery (eta {eta_del.isoformat()} > {delivery.isoformat()} + {LATE_GRACE_MIN}m)",
        )
    return LateCheck(False, "ok", eta_del, delivery, "on time")


def draft_sms(load: Mapping[str, Any], truck_id: str, last: Crumb, check: LateCheck) -> str:
    return (
        "SMS DRAFT (not sent)\n"
        "To: operator@local\n"
        f"Load {load['id']} {load['origin']} -> {load['dest']}\n"
        f"Truck {truck_id} last seen {last.ts.isoformat()} {last.lat},{last.lon} ({last.note})\n"
        f"{check.note}\n"
        "Do not send off-box.\n"
    )


def watch_draft(
    load: Mapping[str, Any],
    truck_id: str,
    crumbs: Sequence[Crumb] | None = None,
) -> str | None:
    """At most one draft per (load, truck), using the last crumb only."""
    mine = crumbs_for(truck_id, crumbs)
    check = is_late(load, mine)
    if not check.late:
        return None
    return draft_sms(load, truck_id, mine[-1], check)


def run_record_path(load_id: str, root: Path | None = None) -> Path:
    return (root or OUT) / f"lane_run_{load_id}.json"


def confirm_delivery(load_id: str, party: str, root: Path | None = None) -> dict[str, Any]:
    if party not in PARTIES:
        raise ValueError(f"party must be driver or receiver, got {party}")
    dest = root or OUT
    dest.mkdir(parents=True, exist_ok=True)
    path = run_record_path(load_id, dest)
    if path.exists():
        rec = json.loads(path.read_text(encoding="utf-8"))
    else:
        rec = {
            "load_id": load_id,
            "driver_confirmed": False,
            "receiver_confirmed": False,
            "status": "open",
        }
    rec[f"{party}_confirmed"] = True
    if rec.get("driver_confirmed") and rec.get("receiver_confirmed"):
        rec["status"] = "delivered"
    else:
        rec["status"] = "recommend"
    path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec
