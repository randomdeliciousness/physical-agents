"""Greedy door assign and first-door-free baseline. No WMS."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from domains.yard.dwell import DWELL_CAP_MIN

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data" / "fixtures"


def hhmm_to_min(raw: str) -> int:
    hours, minutes = raw.split(":")
    return int(hours) * 60 + int(minutes)


def min_to_hhmm(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


@dataclass(frozen=True)
class Appointment:
    id: str
    type: str
    arrive: str
    unload_min: int

    @property
    def arrive_min(self) -> int:
        return hhmm_to_min(self.arrive)


@dataclass
class Door:
    id: str
    type: str
    open: str
    close: str
    free_at: int

    @property
    def open_min(self) -> int:
        return hhmm_to_min(self.open)

    @property
    def close_min(self) -> int:
        return hhmm_to_min(self.close)


@dataclass(frozen=True)
class Assignment:
    appointment_id: str
    door_id: str
    type: str
    arrive: str
    start: str
    end: str
    unload_min: int
    wait_min: int
    dwell_min: int

    @property
    def start_min(self) -> int:
        return hhmm_to_min(self.start)

    @property
    def end_min(self) -> int:
        return hhmm_to_min(self.end)


@dataclass(frozen=True)
class AssignPlan:
    wave: str
    assignments: tuple[Assignment, ...]
    dwell_cap_min: int = DWELL_CAP_MIN
    actuate: bool = False

    @property
    def total_dwell_min(self) -> int:
        return total_dwell(self.assignments)


def load_doors(path: Path | None = None) -> list[Door]:
    src = path or (FIXTURES / "yard_doors.json")
    raw = json.loads(src.read_text(encoding="utf-8"))
    doors: list[Door] = []
    for row in raw:
        open_clock = str(row["open"])
        doors.append(
            Door(
                id=str(row["id"]),
                type=str(row["type"]),
                open=open_clock,
                close=str(row["close"]),
                free_at=hhmm_to_min(open_clock),
            )
        )
    return doors


def load_appointments(path: Path | None = None) -> list[Appointment]:
    src = path or (FIXTURES / "yard_appointments.json")
    raw = json.loads(src.read_text(encoding="utf-8"))
    return [
        Appointment(
            id=str(row["id"]),
            type=str(row["type"]),
            arrive=str(row["arrive"]),
            unload_min=int(row["unload_min"]),
        )
        for row in raw
    ]


def get_appointment(appointment_id: str, rows: Sequence[Appointment] | None = None) -> Appointment:
    appts = list(rows) if rows is not None else load_appointments()
    for appt in appts:
        if appt.id == appointment_id:
            return appt
    raise KeyError(f"unknown appointment {appointment_id}")


def wave_appointments(
    wave: str,
    appointments: Sequence[Appointment] | None = None,
) -> list[Appointment]:
    appts = list(appointments) if appointments is not None else load_appointments()
    chosen = [a for a in appts if a.arrive >= wave]
    if not chosen:
        raise ValueError(f"no appointments at or after wave {wave}")
    return chosen


def total_dwell(assignments: Sequence[Assignment]) -> int:
    return sum(a.dwell_min for a in assignments)


def _fresh_doors(doors: Sequence[Door]) -> list[Door]:
    return [
        Door(id=d.id, type=d.type, open=d.open, close=d.close, free_at=d.open_min)
        for d in doors
    ]


def _sorted_appts(appointments: Sequence[Appointment]) -> list[Appointment]:
    return sorted(appointments, key=lambda a: (a.arrive_min, a.id))


def _window(door: Door, appt: Appointment) -> tuple[int, int] | None:
    start = max(appt.arrive_min, door.free_at, door.open_min)
    end = start + appt.unload_min
    if end > door.close_min:
        return None
    return start, end


def _place(door: Door, appt: Appointment, start: int, end: int) -> Assignment:
    wait = start - appt.arrive_min
    door.free_at = end
    return Assignment(
        appointment_id=appt.id,
        door_id=door.id,
        type=appt.type,
        arrive=appt.arrive,
        start=min_to_hhmm(start),
        end=min_to_hhmm(end),
        unload_min=appt.unload_min,
        wait_min=wait,
        dwell_min=wait + appt.unload_min,
    )


def greedy_assign(
    appointments: Sequence[Appointment],
    doors: Sequence[Door],
) -> list[Assignment]:
    """Earliest start, then unused door (free_at == open), then lowest door.id."""
    pool = _fresh_doors(doors)
    rows: list[Assignment] = []
    for appt in _sorted_appts(appointments):
        best: tuple[tuple[int, int, str], Door, int, int] | None = None
        for door in pool:
            if door.type != appt.type:
                continue
            window = _window(door, appt)
            if window is None:
                continue
            start, end = window
            unused = 0 if door.free_at == door.open_min else 1
            key = (start, unused, door.id)
            if best is None or key < best[0]:
                best = (key, door, start, end)
        if best is None:
            raise ValueError(f"no feasible {appt.type} door for {appt.id}")
        _, door, start, end = best
        rows.append(_place(door, appt, start, end))
    return rows


def first_door_free(
    appointments: Sequence[Appointment],
    doors: Sequence[Door],
) -> list[Assignment]:
    """Queue on the first matching-type door in fixture order. Do not spread."""
    pool = _fresh_doors(doors)
    first: dict[str, Door] = {}
    for door in pool:
        first.setdefault(door.type, door)
    rows: list[Assignment] = []
    for appt in _sorted_appts(appointments):
        door = first.get(appt.type)
        if door is None:
            raise ValueError(f"no {appt.type} door for {appt.id}")
        window = _window(door, appt)
        if window is None:
            raise ValueError(f"first {appt.type} door {door.id} cannot take {appt.id}")
        start, end = window
        rows.append(_place(door, appt, start, end))
    return rows


def assign_wave(
    wave: str,
    policy: str = "greedy",
    appointments: Sequence[Appointment] | None = None,
    doors: Sequence[Door] | None = None,
    dwell_cap_min: int = DWELL_CAP_MIN,
) -> AssignPlan:
    appts = wave_appointments(wave, appointments)
    door_rows = list(doors) if doors is not None else load_doors()
    if policy == "greedy":
        assigned = greedy_assign(appts, door_rows)
    elif policy == "first_door_free":
        assigned = first_door_free(appts, door_rows)
    else:
        raise ValueError(f"unknown policy {policy}")
    return AssignPlan(
        wave=wave,
        assignments=tuple(assigned),
        dwell_cap_min=dwell_cap_min,
        actuate=False,
    )


def assignment_path(wave: str, dest: Path) -> Path:
    stamp = wave.replace(":", "")
    return dest / f"assignment_{stamp}.json"


def assignment_payload(plan: AssignPlan) -> dict[str, object]:
    return {
        "wave": plan.wave,
        "actuate": False,
        "dwell_cap_min": plan.dwell_cap_min,
        "total_dwell_min": plan.total_dwell_min,
        "assignments": [
            {
                "appointment_id": row.appointment_id,
                "door_id": row.door_id,
                "type": row.type,
                "arrive": row.arrive,
                "start": row.start,
                "end": row.end,
                "unload_min": row.unload_min,
                "wait_min": row.wait_min,
                "dwell_min": row.dwell_min,
            }
            for row in plan.assignments
        ],
    }


def format_door_map(plan: AssignPlan) -> str:
    header = (
        f"{'appt':<5} {'type':<8} {'door':<5} {'arrive':<6} "
        f"{'start':<6} {'end':<6} {'wait':>4} {'dwell':>5}"
    )
    lines = [header]
    for row in plan.assignments:
        lines.append(
            f"{row.appointment_id:<5} {row.type:<8} {row.door_id:<5} {row.arrive:<6} "
            f"{row.start:<6} {row.end:<6} {row.wait_min:>4} {row.dwell_min:>5}"
        )
    lines.append(f"total_dwell_min={plan.total_dwell_min} actuate={str(plan.actuate).lower()}")
    return "\n".join(lines)


def write_assignment(plan: AssignPlan, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    path = assignment_path(plan.wave, dest)
    path.write_text(json.dumps(assignment_payload(plan), indent=2) + "\n", encoding="utf-8")
    return path
