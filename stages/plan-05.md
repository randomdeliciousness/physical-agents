# Plan 05 — Yard & Dock Pulse

Status: **approved** (tie-break pin: earliest start, then unused door, then lowest door.id)

Implement only `domains/yard/`, `evals/yard_harness.py`, `tests/test_yard.py`, and `domains/yard/README.md`. No wrap / `demos/PORTFOLIO.md`. No chassis / POLICY.md edits. **No live WMS. No dock hardware client.**

## Pins

1. **No chassis / POLICY.md edits.** `PolicyEngine` already ALLOWs `write_assignment` at default `recommend` and BLOCKs `actuate`. Ticket language “live dock hardware escalate” is the POLICY narrative; with no named door device, the coded verdict is `BLOCK`. Leave that as-is. Do not add a WMS/PLC/door module.

2. **Assignment file only, `recommend`.** Action `write_assignment`. No `--approve`, no `act_under_cap`, no `--actuate` flag. Human / existing WMS executes the door. Audit `action` is `write_assignment` (or `draft` for the overrun note, `compute` for confirm). Assignment JSON includes `"actuate": false`.

3. **Stdlib only.** `json` + `csv` + dataclasses. Fixtures only. No network, no WMS client, no new dependencies.

4. **Keep `demos/yard.md` as written.** CLI is:

```
python -m domains.yard assign --wave 06:00
python -m domains.yard dwell
python -m evals.yard_harness
```

Also ship `confirm --appointment --party driver|dock` (lane-shaped dual check-in). Demo does not call it; tests and the harness do.

5. **`--wave 06:00` is the whole morning inbound fixture.** Keep appointments with `arrive >= wave` (string `HH:MM`). The fixture wave is A-01..A-10. Unknown wave with zero appointments → `ValueError` (CLI exit 2).

6. **No live WMS.** Tests scan `domains/yard/*.py` for `requests`, `urllib.request`, `http.client`, `smtplib`, `twilio`, `pymodbus`, `gpio`, `serial`. Do not copy `--dest` onto `goal.notify`.

7. **Greedy tie-break** (operator pin): earliest `start`, then unused door (`free_at == open`), then lowest `door.id`. Do not use lowest-id-only. That is the table (A-09 D-08, A-10 D-12).

## Domain model (`assign.py`)

Numbers live here, not in a prompt.

Load `data/fixtures/yard_doors.json` and `yard_appointments.json`. Times are `HH:MM` on one civil day. Convert to minutes-from-midnight for arithmetic; display as `HH:MM`.

A door is feasible for an appointment iff `door.type == appointment.type` and the window fits:

```
start = max(arrive, door.free_at, door.open)
end   = start + unload_min
feasible iff end <= door.close
```

Initialize each `door.free_at = door.open`. After an assignment, `door.free_at = end`. No double-book.

### Greedy (`greedy_assign`)

Process appointments in `(arrive, id)` order. For each, among matching-type feasible doors, pick the **earliest `start`**. Tie-break: unused door (`free_at == open`), then lowest `door.id`. Do not use lowest-id-only. If none feasible → `ValueError`.

Worked 06:00 wave (all wait 0; total dwell = sum of `unload_min` = **470**):

| appt | type | arrive | door | start | end | dwell |
|---|---|---|---|---|---|---|
| A-01 | dry | 06:00 | D-01 | 06:00 | 06:45 | 45 |
| A-02 | dry | 06:00 | D-02 | 06:00 | 06:40 | 40 |
| A-03 | reefer | 06:00 | D-05 | 06:00 | 06:55 | 55 |
| A-04 | dry | 06:15 | D-03 | 06:15 | 06:50 | 35 |
| A-05 | dry | 06:15 | D-04 | 06:15 | 07:05 | 50 |
| A-06 | reefer | 06:20 | D-06 | 06:20 | 07:20 | 60 |
| A-07 | flatbed | 06:30 | D-09 | 06:30 | 07:10 | 40 |
| A-08 | dry | 06:30 | D-07 | 06:30 | 07:15 | 45 |
| A-09 | dry | 06:45 | D-08 | 06:45 | 07:15 | 30 |
| A-10 | reefer | 07:00 | D-12 | 07:00 | 08:10 | 70 |

Reefer only on D-05 / D-06 / D-12. Flatbed only on D-09. Dry never on those.

`dwell_min = (start - arrive) + unload_min`. `total_dwell(assignments) = sum(dwell_min)`.

### First-door-free baseline (`first_door_free`)

Harness comparator, still type-matched. For each appointment in the same order, use **only the first matching-type door in fixture order** (dry `D-01`, reefer `D-05`, flatbed `D-09`). Queue on that door until it is free. Do not spread.

Worked baseline total = **1090**.

`write_assignment(plan, dest) -> Path` writes `dest / f"assignment_{wave.replace(':','')}.json"` (Windows-safe: `assignment_0600.json`).

## Dwell (`dwell.py`)

Cap = **90 minutes** (`DWELL_CAP_MIN`) unless `Goal.extra["dwell_cap_min"]` says otherwise. Do not add fields to `Goal`.

Fixture event dwell: A-01 48 quiet, A-03 **125** overrun, A-07 33 quiet. One local draft on overrun. Dual confirm: `driver` + `dock` → `status="complete"`; one party is `recommend` only.

## Verify

```
python -m unittest tests.test_yard tests.test_chassis tests.test_water tests.test_watch tests.test_buyer tests.test_lane -q
python -m domains.yard assign --wave 06:00
python -m domains.yard dwell
python -m domains.yard confirm --appointment A-03 --party driver
python -m domains.yard confirm --appointment A-03 --party dock
python -m evals.yard_harness
```

Do not claim done without those outputs. Commit when tests pass. Do not start stage 06 in the same session.
