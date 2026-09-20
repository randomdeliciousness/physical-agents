"""Event dwell vs cap, one local overrun draft, dual check-in confirm."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data" / "fixtures"
OUT = ROOT / "demos" / "out"

DWELL_CAP_MIN = 90
PARTIES = frozenset({"driver", "dock"})


@dataclass(frozen=True)
class YardEvent:
    appointment_id: str
    event: str
    ts: datetime


@dataclass(frozen=True)
class DwellRow:
    appointment_id: str
    enter: datetime
    exit: datetime
    dwell_min: int

    def over_cap(self, cap: int = DWELL_CAP_MIN) -> bool:
        return self.dwell_min > cap


def parse_ts(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def load_events(path: Path | None = None) -> list[YardEvent]:
    src = path or (FIXTURES / "yard_events.csv")
    rows: list[YardEvent] = []
    with src.open(encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            rows.append(
                YardEvent(
                    appointment_id=str(raw["appointment_id"]),
                    event=str(raw["event"]),
                    ts=parse_ts(str(raw["ts"])),
                )
            )
    rows.sort(key=lambda e: (e.appointment_id, e.ts))
    return rows


def dwell_minutes(enter: datetime, exit: datetime) -> int:
    return int((exit - enter).total_seconds() // 60)


def event_dwells(events: Sequence[YardEvent] | None = None) -> list[DwellRow]:
    rows = list(events) if events is not None else load_events()
    enters: dict[str, datetime] = {}
    exits: dict[str, datetime] = {}
    for ev in rows:
        if ev.event == "enter":
            enters[ev.appointment_id] = ev.ts
        elif ev.event == "exit":
            exits[ev.appointment_id] = ev.ts
    dwells: list[DwellRow] = []
    for appt_id in sorted(set(enters) & set(exits)):
        enter = enters[appt_id]
        exit_ts = exits[appt_id]
        dwells.append(
            DwellRow(
                appointment_id=appt_id,
                enter=enter,
                exit=exit_ts,
                dwell_min=dwell_minutes(enter, exit_ts),
            )
        )
    return dwells


def overruns(rows: Sequence[DwellRow], cap: int = DWELL_CAP_MIN) -> list[DwellRow]:
    return [row for row in rows if row.over_cap(cap)]


def draft_overrun(rows: Sequence[DwellRow], cap: int = DWELL_CAP_MIN) -> str | None:
    """One local driver/dock text covering every overrun. None if all under cap."""
    bad = overruns(rows, cap)
    if not bad:
        return None
    lines = [
        "DOCK DRAFT (not sent)",
        "To: operator@local",
    ]
    for row in bad:
        lines.append(
            f"Appointment {row.appointment_id} dwell {row.dwell_min} min exceeds cap {cap} min "
            f"(enter {row.enter.isoformat()} exit {row.exit.isoformat()})."
        )
    lines.append("Driver/dock: check stall at assigned door. Do not send off-box.")
    lines.append("")
    return "\n".join(lines)


def run_record_path(appointment_id: str, root: Path | None = None) -> Path:
    return (root or OUT) / f"yard_run_{appointment_id}.json"


def confirm_checkin(appointment_id: str, party: str, root: Path | None = None) -> dict[str, Any]:
    if party not in PARTIES:
        raise ValueError(f"party must be driver or dock, got {party}")
    dest = root or OUT
    dest.mkdir(parents=True, exist_ok=True)
    path = run_record_path(appointment_id, dest)
    if path.exists():
        rec = json.loads(path.read_text(encoding="utf-8"))
    else:
        rec = {
            "appointment_id": appointment_id,
            "driver_confirmed": False,
            "dock_confirmed": False,
            "status": "open",
        }
    rec[f"{party}_confirmed"] = True
    if rec.get("driver_confirmed") and rec.get("dock_confirmed"):
        rec["status"] = "complete"
    else:
        rec["status"] = "recommend"
    path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec
