# Stage 00 — Chassis

Status: **ready to open** (interfaces already exist; Build should extend, not replace)

## Goal

A reusable runtime: Goal → Policy check → Tool → Channel → audit row.
Prove it with the echo demo and pytest.

## Path

`chassis/`, `tests/test_chassis.py`

## Autonomy

`recommend` only. No network.

## Fixtures

None required.

## Eval / tests

```bash
python -m pytest tests/test_chassis.py -q
python -m chassis.demo_echo --goal "ping"
```

Expect demo to print an audit-style record and write a line to `data/audit.jsonl`.

## Acceptance

- [x] Goal, Policy, Tool, Channel, RunLog exist
- [x] `demo_echo` run succeeds on a clean checkout
- [x] Cap missing + act_under_cap requested → escalate, no tool side effect
- [x] Blocked destination rejected
- [x] Engineer does not start stage 01 in this session

## Build prompt (paste into Grok Build plan mode)

```text
Read AGENTS.md, POLICY.md, and stages/00-chassis.md.
Inspect chassis/ and tests/test_chassis.py.
Plan only: list gaps vs the ticket acceptance box. Do not rewrite working modules unless a test fails.
If tests already pass, add only what the ticket still marks open (demo_echo CLI if missing, audit file create).
Stop for approval before editing.
```

## After approval

```text
Implement the approved gaps. Keep POLICY.md and chassis/policy.py in sync.
Run python -m pytest tests/test_chassis.py -q
Do not open domains/.
```

## Income note

None. This is infrastructure.
