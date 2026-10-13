# Physical-efficiency agents

Five narrow agents that compute a physical outcome, write a local artifact, and stop. A shared policy engine decides whether that write is allowed. Chat is a channel, not the product.

This is a portfolio of **policy-gated domain models and fixture evals**. It is not a live marketplace, a trading system, or a self-improving agent. Scores below are against fixtures written for this repo, not against a market or a field deployment.

## Scoreboard

Last fixture run (all `PASS=1`):

```
DOMAIN=lane  PASS=1 METRIC=usd_per_mi_err     VALUE=0.0000 BASELINE=10   UNIT=pct
DOMAIN=buyer PASS=1 METRIC=rank_acc          VALUE=1.0    BASELINE=1.0  UNIT=frac
DOMAIN=watch PASS=1 METRIC=alert_precision   VALUE=1.0    BASELINE=1.0  UNIT=frac
DOMAIN=water PASS=1 METRIC=plan_match        VALUE=1.0    BASELINE=1.0  UNIT=frac
DOMAIN=yard  PASS=1 METRIC=dwell_min         VALUE=470    BASELINE=1090 UNIT=min
```

Read these as written. Lane `0.0000` is error against an oracle generated from the same cost model, not against a broker. Yard `470` vs `1090` is greedy assignment versus a first-door-free strawman on one fixture wave, in minutes, not a billed saving. Buyer, watch, and water `1.0` are fixture-hit fractions. No derived percentages.

Full table, artifacts, and non-goals: [`demos/PORTFOLIO.md`](demos/PORTFOLIO.md).

## What a run does

```
Goal → Policy check → domain model → local artifact → one audit row
```

Arithmetic lives in Python. The agent decides which tool to call and whether a cap applies. Every run appends one JSON object to `data/audit.jsonl`. Default tier is `recommend`. There is no “ignore the human” tier.

| Domain | Outcome | Autonomy | Artifact |
|---|---|---|---|
| Lane Cost & Exception | Quote all-in USD/mi; draft one late-to-pickup note | `recommend` | `demos/out/` file sink |
| Landed-Cost Buyer | Rank by landed cost; PO only with `--approve` | `act_under_cap` to write; send is not implemented | `demos/out/po_BOX-24.md` |
| Watch Officer | Fuse fixture feeds; alert only on allowlist | `recommend` | `demos/out/alert.json` |
| Water Pulse | Skip or run tonight from moisture + forecast | `recommend` | schedule JSON, `"actuate": false` |
| Yard & Dock Pulse | Assign doors; one dwell overrun draft | `recommend` | `demos/out/assignment_0600.json` |

## Policy

[`POLICY.md`](POLICY.md) is the source of truth. [`chassis/policy.py`](chassis/policy.py) enforces the same rules. They must change together.

Blocked, including in demos: 911, NIFC, USFS, Cal Fire, county duty desks, live freight booking, live payment, trading, live pump/valve/door commands. Watch is fixture fusion, not a replacement for NOAA or USFS, and it must not page agencies. A destination such as `nifc@example.gov` returns `BLOCK` and writes no alert.

Hypothetical fee notes in `PORTFOLIO.md` are not revenue and do not promise a contract.

## Layout

```
chassis/          Goal, Policy, Tool, Channel, audit
domains/          lane, buyer, watch, water, yard
evals/            one harness per domain; prints one DOMAIN= line
data/fixtures/    synthetic inputs
demos/            walkthroughs and PORTFOLIO.md
POLICY.md         autonomy, allowlist, blocked actions
AGENTS.md         rules for a coding agent working in this repo
bots/             role briefs (Floor PM, Engineer, Ops, Policy, Demo)
stages/           original build tickets
```

## Run

Python 3.11+. Standard library only. No network in unit tests or harnesses.

```bash
python -m unittest discover -s tests -q
python -m evals.lane_harness
python -m evals.buyer_harness
python -m evals.watch_harness
python -m evals.water_harness
python -m evals.yard_harness
```

Walkthroughs are in `demos/*.md`. Examples:

```bash
python -m domains.lane quote --load L-07
python -m domains.lane watch --load L-07 --truck T-07
python -m domains.buyer rank --spec BOX-24
python -m domains.buyer po --spec BOX-24            # ESCALATE, no file
python -m domains.buyer po --spec BOX-24 --approve
python -m domains.watch brief --replay calm        # no alert
python -m domains.watch brief --replay hot
python -m domains.watch brief --replay hot --dest nifc@example.gov   # BLOCK
python -m domains.water plan --date 2026-09-13     # skip
python -m domains.water plan --date 2026-09-14     # run
python -m domains.yard assign --wave 06:00
python -m domains.yard dwell
```

## Non-goals

- Two-sided marketplaces
- Trading or money-printing bots
- Live 911 / agency pages
- Live freight booking or payment
- Live equipment actuation
- Rewriting the chassis to dodge policy
- Self-improvement loops against these harnesses (the oracles were generated from the same models)

## Stack note

Domain code was written with Grok Build against the tickets in `stages/`. The `bots/` briefs are for a Grok Bot channel that can read this repo and run the harnesses. Neither tool is required to run the Python.
