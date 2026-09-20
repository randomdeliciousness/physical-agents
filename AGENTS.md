# AGENTS.md — physical-agents

Instructions for Grok Build (and any coding agent) working in this repository.
Read `POLICY.md` before writing code that sends messages, spends, books, pages, or actuates.

## Mission

Portfolio of **physical-efficiency cloud agents**. Each domain takes a goal, uses a
domain model for numbers, writes an audit row, and returns an artifact. Chat is
a channel, not the product.

Domains, in order. Do not start the next until the current stage ticket is green.

0. `chassis/` — shared Goal, Policy, Tool, Channel, RunLog
1. `domains/lane/` — Lane Cost & Exception (freight)
2. `domains/buyer/` — Landed-Cost Buyer
3. `domains/watch/` — Watch Officer (wildfire fusion + notify you only)
4. `domains/water/` — Water Pulse (irrigation schedule, no actuator)
5. `domains/yard/` — Yard & Dock Pulse
6. Portfolio wrap — `demos/` + eval scoreboard

## Non-goals

- Two-sided marketplaces (no public load board, no vendor social network)
- Trading or “money-printing” bots
- Live 911 / NIFC / USFS / county duty-desk pages
- Live freight booking or live payment
- Live pump, valve, or equipment actuation unless POLICY.md and a human allow that exact action
- Rewriting chassis interfaces inside a domain to dodge policy

## How numbers vs language split

- **Domain models compute** distance, energy, landed cost, water balance, dwell, fire-weather rules.
- **The agent decides** which tool to call, whether a cap applies, what to draft, when to escalate.
- Do not put cost, moisture, or fire-weather arithmetic only inside a prompt.

## Layout

physical-agents/
AGENTS.md              this file
POLICY.md              autonomy, allowlists, blocked actions
bots/                  Grok Bot paste-in descriptions
stages/                tickets Build should execute one at a time
chassis/               shared runtime
domains//        one product
data/fixtures/         synthetic truth for demos and evals
evals/                 physical-unit harnesses
demos/                 timed walkthrough scripts
.grok/skills/          reusable Build skills
.grok/workflows/       saved fan-out jobs


## Session protocol (Grok Build)

1. Read this file, `POLICY.md`, and the open stage ticket in `stages/`.
2. Start in **plan mode**. Write or update `stages/plan-<id>.md`. Stop for approval.
3. Implement only the paths named in the ticket.
4. Run the tests named in the ticket. Do not claim done without the command output.
5. Commit when tests pass. Do not start the next domain in the same session unless the operator says so.
6. If POLICY.md would be violated by a requested feature, stop and say so. Do not weaken POLICY.md to make the feature pass.

Use `/goal` when the ticket has a testable claim and you should keep going until evidence exists.
Use `/workflows` only to fan out independent fixtures (N loads, N vendors, N replay days). Do not use workflows to design architecture.

## Coding conventions

- Python 3.11+ for chassis and domain models. Keep domains importable without a web framework.
- Standard library first. Add a dependency only if the stage ticket names it.
- Type hints on public functions. One module, one job.
- Tests live in `tests/` and `evals/`. Fixtures live in `data/fixtures/`. Do not fetch live networks inside unit tests.
- Every successful or blocked run appends one JSON object to `data/audit.jsonl` via `chassis.audit`.
- Domain CLIs, if any: `python -m domains.<name>` with subcommands `quote|plan|brief|assign` and `--approve` only where POLICY allows.

## Policy hooks in code

Import caps from `chassis.policy` which reads `POLICY.md` rules encoded in `chassis/policy.py`.
If you add a new irreversible action type, add it to **both** POLICY.md and `chassis/policy.py` in the same change.

Default tier is `recommend`. `act_under_cap` requires an explicit cap in the Goal. `escalate` is the only legal path for anything on the blocked or approval lists.

## Eval standard

Each domain ships `evals/<name>_harness.py` that prints a single summary line: DOMAIN= PASS=<0|1> METRIC= VALUE= BASELINE= UNIT= 

Physical units only: USD, USD_per_mi, gallons, kWh, minutes, dwell_min, inch, acre_ft, alerts.

## What “done” means for a stage

- Ticket acceptance checks all pass
- Eval harness exits 0
- Demo script in `demos/<name>.md` can be followed in one sitting
- No new POLICY exceptions unless the operator added them in writing

## Operator

Paul Loupe. Grok Bot Floor PM assigns tickets. Grok Build Engineer implements.
You (the coding agent) never merge to a protected branch and never send external messages.
