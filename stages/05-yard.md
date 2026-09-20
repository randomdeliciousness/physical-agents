# Stage 05 — Yard & Dock Pulse

Status: open only after 04 is frozen

## Goal

Assign doors for a morning inbound wave. Flag dwell over cap. Draft one driver/dock text on overrun. Dual confirm for check-in complete.

## Path

`domains/yard/`  
Fixtures: `data/fixtures/yard_doors.json`, `yard_appointments.json`, `yard_events.csv`

## Domain model

Greedy assign: matching door type (reefer/dry), earliest feasible window, no double-book. Dwell = exit - enter. Cap = 90 minutes unless Goal says otherwise.

## Autonomy

Assignment file write = recommend. Hardware command = escalate.

## Eval

Beat first-available-door baseline on total dwell minutes for the fixture wave.

```
DOMAIN=yard PASS=1 METRIC=dwell_min VALUE=<n> BASELINE=<m> UNIT=min
```

PASS if VALUE < BASELINE.

## Acceptance

- [ ] Assignments for the 06:00 wave
- [ ] One overrun in yard_events.csv produces one draft
- [ ] Baseline comparator lives in the harness
- [ ] `demos/yard.md` works

## Build prompt

```text
Read AGENTS.md, POLICY.md, stages/05-yard.md and data/fixtures/yard_*.
Plan domains/yard/ assign.py, dwell.py, cli, evals/yard_harness.py including a first-door-free baseline.
No live WMS. Stop for approval.
```

## Hypothetical income

$2–5k/month per site after a DC pilot, sold against detention and overtime.
