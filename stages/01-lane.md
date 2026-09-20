# Stage 01 — Lane Cost & Exception

Status: open only after 00 is frozen

## Goal

Quote all-in cost for a load against synthetic trucks. If breadcrumbs show the assigned truck late to pickup or delivery, draft one SMS (file sink). Dual confirm required before "delivered."

## Path

`domains/lane/`  
Fixtures: `data/fixtures/trucks.json`, `loads.json`, `gps_breadcrumbs.csv`

## Domain model (code, not prompt)

- Miles + elevation band → energy (diesel gal or kWh)
- Energy + driver hours + tolls + deadhead → USD and USD/mi
- Late if projected arrival > appointment + 15 minutes

## Autonomy

Default `recommend`. `act_under_cap` may write a local "book" artifact only if `cap_usd_per_mi` is set and the truck is synthetic. No live broker.

## Eval

`evals/lane_harness.py` must cover the 10 fixture loads.

```
DOMAIN=lane PASS=1 METRIC=usd_per_mi_err VALUE=<pct> BASELINE=10 UNIT=pct
```

Also: late truck (see breadcrumbs for truck T-07) produces exactly one draft; on-time trucks produce zero.

## Acceptance

- [ ] `python -m domains.lane quote --load L-07` prints ranked trucks
- [ ] Cost within 10% of the oracle in `evals/lane_oracle.json` (Build should generate the oracle from the same formulas, then freeze it)
- [ ] Exception draft only for T-07
- [ ] Delivered state requires driver + receiver confirm
- [ ] Demo script `demos/lane.md` works

## Build prompt

```text
Read AGENTS.md, POLICY.md, stages/01-lane.md, and data/fixtures/{trucks.json,loads.json,gps_breadcrumbs.csv}.
Plan domains/lane/: cost_model.py, matcher.py, exception.py, cli, evals/lane_harness.py.
Use chassis for Goal, Policy, audit.
No live network. No DAT/Truckstop.
Stop for approval.
```

## Hypothetical income

$15–40 / truck / month watch layer, or $3–8 per handled exception, after one carrier pilot.
