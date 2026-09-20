# Stage 04 — Water Pulse

Status: open only after 03 is frozen

## Goal

One field. Soil-moisture CSV + forecast precip → run/skip tonight and a 3-night plan. Human executes valves.

## Path

`domains/water/`  
Fixtures: `data/fixtures/water_moisture.csv`, `water_weather.csv`

## Domain model

Simple balance: deficit += ET; deficit -= precip; irrigate if deficit > threshold and forecast rain next 24h < skip_inches.

## Autonomy

Schedule file only. `actuate=true` escalate then blocked until a named device exists in POLICY.

## Eval

Wet fixture day → skip. Dry fixture day → run.

```
DOMAIN=water PASS=1 METRIC=plan_match VALUE=1.0 BASELINE=1.0 UNIT=frac
```

## Acceptance

- [ ] Opposite plans on wet vs dry fixtures
- [ ] Message draft to irrigator is local only
- [ ] `demos/water.md` works

## Build prompt

```text
Read AGENTS.md, POLICY.md, stages/04-water.md and data/fixtures/water_*.csv.
Plan domains/water/ water_balance.py, planner.py, cli, evals/water_harness.py.
No actuator client. Stop for approval.
```

## Hypothetical income

$8–20/acre/season or a share of measured kWh/water saved after one ranch pilot.
