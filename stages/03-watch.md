# Stage 03 — Watch Officer

Status: open only after 02 is frozen

## Goal

Fuse fixture (and later public) feeds for one AOI into a brief. Emit `alert.json` only when YAML rules fire. Notify allowlist only (`operator@local` / this channel).

## Path

`domains/watch/`  
Fixtures: `data/fixtures/watch_rules.yml`, `watch_replay.json`

## Domain model

Rules engine over wind, RH, hotspot distance, precip. No new spread model. Numbers must carry `source` or `unknown`.

## Autonomy

Alert file write = `recommend`. Any real SMS = escalate. Agency destinations = BLOCK.

## Eval

Replay "calm" day → 0 alerts. Replay "hot-dry-windy + hotspot" day → exactly 1 alert to allowlist.

```
DOMAIN=watch PASS=1 METRIC=alert_precision VALUE=1.0 BASELINE=1.0 UNIT=frac
```

## Acceptance

- [ ] `python -m domains.watch brief --replay hot` writes `demos/out/watch_brief.md`
- [ ] Calm replay silent
- [ ] Destination not on allowlist rejected by chassis.policy
- [ ] Copy states this is fusion, not a replacement for NOAA/USFS
- [ ] `demos/watch.md` works

## Build prompt

```text
Read AGENTS.md, POLICY.md, stages/03-watch.md, data/fixtures/watch_rules.yml, data/fixtures/watch_replay.json.
Plan domains/watch/ adapters (fixture now, public feed stubs later), rules engine, brief renderer, evals/watch_harness.py.
Hard-block destinations outside POLICY allowlist.
Do not invent containment or casualties.
Stop for approval.
```

## Hypothetical income

$500–2,000/month per county or utility watch desk for briefing time, after a fire-safe council pilot. No agency-page contracts from this demo.
