# Plan 04 — Water Pulse

Status: **approved**

Implement only `domains/water/`, `evals/water_harness.py`, `tests/test_water.py`, and `domains/water/README.md`. No yard. No chassis / POLICY.md edits. **No actuator client.**

## Pins

1. **No chassis / POLICY.md edits.** `PolicyEngine` already BLOCKs `actuate` (`BLOCKED_ACTIONS`) and allows `write_schedule` at default `recommend`. Do not add a named device. Ticket language “escalate then blocked until a named device exists” is the POLICY narrative; with no device, the coded verdict is `BLOCK`. Leave that as-is.

2. **Schedule file only, `recommend`.** Action `write_schedule`. No `--approve`, no `act_under_cap`, no `--actuate` flag, no valve/pump/modbus/GPIO client. Human executes valves. Audit `action` is `write_schedule` (or `draft` for the local irrigator note), never `actuate`. Schedule JSON includes `"actuate": false`.

3. **Stdlib only.** `csv` + dataclasses. Fixtures only. No network.

4. **One field.** Default `F-01` from `data/fixtures/water_moisture.csv` and `water_weather.csv`. Unknown field or a plan date before the first moisture row → `KeyError` / `ValueError` (CLI exit 2).

5. **Keep `demos/water.md` as written.** CLI is `python -m domains.water plan --date YYYY-MM-DD`.

## Domain model (`water_balance.py`)

Numbers live here, not in a prompt.

Constants:

- `SKIP_INCHES = 0.25` (not in the CSV; 0.55 wet ≥ skip, 0.00 and 0.10 dry < skip)
- Deficit threshold = that day’s `threshold_frac` from moisture (fixture value **0.18**). Same number, inches of allowed deficit. Call this out: it is a unit pun on the column name; do not invent a second threshold.

State is inches:

```
deficit = 0.0 at the start of the moisture series
# each calendar day:
deficit += et_in
# decide using post-ET deficit and the day's forecast (rain has not fallen yet)
run if deficit > threshold and forecast_rain_in < SKIP_INCHES
# after the decision:
#   run  → deficit = 0          (plan assumes the recommended set is followed)
#   skip → deficit = max(0, deficit - forecast_rain_in)
```

Rules:

- **Precip source:** `forecast_rain_in` from weather when a row exists, else `0`. No observed-precip column.
- **No future moisture leak:** for plan date `D`, moisture/ET/threshold rows with `date <= D` only. Weather on `D..D+2` is forecast, so those rows are allowed.
- **Historical days (`date < D`):** apply the same skip/precip update. Do **not** apply `run` refill historically (those nights were not this plan).
- **Horizon days without a moisture row:** carry last `et_in` and last `threshold_frac` from moisture `<= D`.
- **`moisture_frac`:** recorded on the night row and in the irrigator draft; it is not the irrigate predicate. The predicate is deficit + skip, as the ticket states.

Worked fixture (field `F-01`):

| date | et_in | rain | role on `--date 2026-09-13` | deficit after ET | tonight |
|---|---|---|---|---|---|
| 09-10 | 0.22 | 0 | history | 0.22 | — |
| 09-11 | 0.23 | 0 | history | 0.45 | — |
| 09-12 | 0.24 | 0 | history | 0.69 | — |
| 09-13 | 0.25 | 0.55 | night 0 | 0.94 | **skip** (rain ≥ 0.25); then deficit 0.39 |
| 09-14 | carry 0.25 | 0.00 | night 1 | 0.64 | run, refill 0 |
| 09-15 | carry 0.25 | 0.00 | night 2 | 0.25 | run |

`--date 2026-09-14` history includes 09-13 as a skip (rain applied, no refill) → deficit 0.39; tonight `+ 0.26` (moisture row) → **0.65 → run**. Nights 09-15 and 09-16 carry `et_in=0.26` and both **run**.

Eval only locks tonight: wet skip / dry run. Consecutive dry nights can still be `run` because daily ET (~0.25) > threshold (0.18).

## Planner (`planner.py`)

- `plan_nights(field_id, as_of, n=3) -> Plan` using the balance above.
- `render_message(plan) -> str` local irrigator draft: tonight run/skip, 3-night table, “human executes valves”, no actuator language that implies a send.
- `write_schedule(plan, dest) -> Path` writes `dest / f"schedule_{field}_{as_of}.json"` (demo: `demos/out/schedule_F-01_2026-09-13.json` and `...-09-14.json`).

JSON shape:

```json
{
  "field_id": "F-01",
  "as_of": "2026-09-13",
  "tonight": "skip",
  "actuate": false,
  "skip_inches": 0.25,
  "nights": [
    {
      "date": "2026-09-13",
      "action": "skip",
      "deficit_in": 0.94,
      "et_in": 0.25,
      "forecast_rain_in": 0.55,
      "threshold": 0.18,
      "moisture_frac": 0.17,
      "reason": "forecast rain 0.55 >= skip 0.25"
    }
  ]
}
```

## CLI (`domains/water/__main__.py`)

```
python -m domains.water plan --date 2026-09-13 [--field F-01]
```

- `Goal` tier `recommend`. `Agent.act(..., action="write_schedule")` writes the JSON; same act (or a follow-up `draft`) sends the irrigator note through `FileChannel` to `operator@local` only. Do not copy any dest onto `goal.notify`.
- Print tonight first so the demo is obvious, e.g. `tonight=skip field=F-01 date=2026-09-13 rain=0.55` then `verdict=ALLOW artifact=...`.
- Exit 0 on ALLOW, 1 on BLOCK/ESCALATE, 2 on bad input.

## Eval (`evals/water_harness.py`)

Import the planner (no live CLI, no network). Wet date `2026-09-13` → `skip`. Dry date `2026-09-14` → `run`. `VALUE = hits/2`. Also assert `PolicyEngine.check(goal, "actuate")` is `BLOCK` and a temp `write_schedule` produces a file with `"actuate": false`.

```
DOMAIN=water PASS=1 METRIC=plan_match VALUE=1.0 BASELINE=1.0 UNIT=frac
```

Exit 0 on pass, 1 otherwise.

## Tests (`tests/test_water.py`)

- Wet CLI/planner skip, dry run; opposite plans.
- 3-night length 3; 09-13 nights `skip, run, run`; 09-14 nights `run, run, run`.
- `actuate` policy BLOCK; blocked action does not write a schedule (mirror chassis agent test).
- Water package has no actuator client: no `pymodbus`, `gpio`, `serial`, `smtplib`, `twilio`, `urllib.request`, `requests`.
- Irrigator draft is local (`operator@local.txt`); schedule JSON has `"actuate": false`.
- CLI writes `schedule_F-01_<date>.json` under a patched `OUT`.

## Layout

```
domains/water/__init__.py
domains/water/__main__.py          plan --date [--field]
domains/water/water_balance.py     CSV load + inch balance + run/skip
domains/water/planner.py           3-night plan, draft, schedule JSON
domains/water/README.md
evals/water_harness.py
tests/test_water.py
```

Do not add `actuator.py` or any device module.

## Out of scope

- Yard / stage 05
- Live weather
- Pump, valve, or equipment commands
- New POLICY exceptions or named devices
- Weakening `actuate` in `chassis/policy.py`

## Verify

```
python -m unittest tests.test_water tests.test_chassis tests.test_watch tests.test_buyer tests.test_lane -q
python -m domains.water plan --date 2026-09-13
python -m domains.water plan --date 2026-09-14
python -m evals.water_harness
```

Do not claim done without those outputs. Commit when tests pass. Do not start stage 05 in this session.
