"""Yard eval: greedy dwell beats first-door-free on the fixture wave."""

from __future__ import annotations

import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from chassis.goal import Goal
from chassis.policy import PolicyEngine
from domains.yard.assign import (
    assign_wave,
    first_door_free,
    greedy_assign,
    load_appointments,
    load_doors,
    total_dwell,
    write_assignment,
)
from domains.yard.dwell import confirm_checkin, draft_overrun, event_dwells, overruns

WAVE = "06:00"
LOCK_VALUE = 470
LOCK_BASELINE = 1090


def _no_double_book(assignments) -> bool:
    by_door: dict[str, list] = defaultdict(list)
    for row in assignments:
        by_door[row.door_id].append(row)
    for rows in by_door.values():
        rows.sort(key=lambda r: r.start_min)
        for prev, cur in zip(rows, rows[1:]):
            if cur.start_min < prev.end_min:
                return False
    return True


def _types_match(assignments, appointments) -> bool:
    by_id = {a.id: a for a in appointments}
    doors = {d.id: d for d in load_doors()}
    for row in assignments:
        appt = by_id[row.appointment_id]
        door = doors[row.door_id]
        if row.type != appt.type or door.type != appt.type:
            return False
    return True


def main() -> int:
    appts = load_appointments()
    doors = load_doors()
    wave = [a for a in appts if a.arrive >= WAVE]
    greedy = greedy_assign(wave, doors)
    baseline_rows = first_door_free(wave, doors)
    value = total_dwell(greedy)
    baseline = total_dwell(baseline_rows)

    dwells = event_dwells()
    by_id = {r.appointment_id: r for r in dwells}
    a03 = by_id.get("A-03")
    a01 = by_id.get("A-01")
    a07 = by_id.get("A-07")
    draft = draft_overrun(dwells)
    overrun_ids = {r.appointment_id for r in overruns(dwells)}

    engine = PolicyEngine()
    goal = Goal(id="yard-eval", domain="yard", text="assign")
    blocked = engine.check(goal, "actuate")
    allowed = engine.check(goal, "write_assignment")

    actuate_false = False
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        plan = assign_wave(WAVE)
        path = write_assignment(plan, root)
        leftover = list(root.glob("assignment_*.json"))
        if path.exists() and leftover == [path]:
            payload = json.loads(path.read_text(encoding="utf-8"))
            actuate_false = payload.get("actuate") is False and payload.get("wave") == WAVE

        one = confirm_checkin("A-03", "driver", root)
        two = confirm_checkin("A-03", "dock", root)
        confirm_ok = one["status"] != "complete" and two["status"] == "complete"

    passed = (
        value < baseline
        and value == LOCK_VALUE
        and baseline == LOCK_BASELINE
        and _types_match(greedy, wave)
        and _no_double_book(greedy)
        and a03 is not None
        and a03.dwell_min == 125
        and a01 is not None
        and a01.dwell_min == 48
        and a07 is not None
        and a07.dwell_min == 33
        and overrun_ids == {"A-03"}
        and draft is not None
        and draft.count("Appointment ") == 1
        and "A-03" in draft
        and "A-01" not in draft
        and "A-07" not in draft
        and confirm_ok
        and blocked.verdict == "BLOCK"
        and allowed.verdict == "ALLOW"
        and actuate_false
    )
    flag = 1 if passed else 0
    print(f"DOMAIN=yard PASS={flag} METRIC=dwell_min VALUE={value} BASELINE={baseline} UNIT=min")
    if not passed:
        print(
            f"value={value} baseline={baseline} overruns={sorted(overrun_ids)} "
            f"confirm_ok={confirm_ok} actuate_false={actuate_false} "
            f"block={blocked.verdict} allow={allowed.verdict}",
            file=sys.stderr,
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
