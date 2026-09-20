# Portfolio — physical-efficiency agents

Shared chassis: Goal → Policy check → Tool → Channel → one `data/audit.jsonl` row.
Each domain computes numbers in code, writes a local artifact, and stops. Chat is a
channel, not the product.

Fees below are **hypothetical**. They do not collect payment and do not promise
official-agency contracts (`POLICY.md`).

## Eval summary (verbatim)

```
DOMAIN=lane PASS=1 METRIC=usd_per_mi_err VALUE=0.0000 BASELINE=10 UNIT=pct
DOMAIN=buyer PASS=1 METRIC=rank_acc VALUE=1.0 BASELINE=1.0 UNIT=frac
DOMAIN=watch PASS=1 METRIC=alert_precision VALUE=1.0 BASELINE=1.0 UNIT=frac
DOMAIN=water PASS=1 METRIC=plan_match VALUE=1.0 BASELINE=1.0 UNIT=frac
DOMAIN=yard PASS=1 METRIC=dwell_min VALUE=470 BASELINE=1090 UNIT=min
```

Lane `VALUE=0.0000` is max percent error vs `evals/lane_oracle.json` (same cost model,
10 fixture loads), not vs a market. Yard `VALUE=470` / `BASELINE=1090` are total dwell
minutes on the 06:00 fixture wave (greedy vs first-door-free). Buyer, watch, and water
`VALUE=1.0` are fixture-hit fractions. No derived savings percentages.

## Scoreboard

| Domain | Metric | Artifact path | Autonomy tier | Hypothetical fee |
|---|---|---|---|---|
| Lane Cost & Exception | `usd_per_mi_err` VALUE=0.0000 BASELINE=10 UNIT=pct | `demos/out/operator@local.txt` (T-07 / L-07 SMS draft from `lane watch`; file sink, not sent) | `recommend` | $15–40 / truck / month watch layer, or $3–8 per handled exception, after one carrier pilot. |
| Landed-Cost Buyer | `rank_acc` VALUE=1.0 BASELINE=1.0 UNIT=frac | `demos/out/po_BOX-24.md` | `act_under_cap` (`po --approve`; send still escalate) | 5–15% of documented tail-spend savings or $1–3k/month per buyer desk. |
| Watch Officer | `alert_precision` VALUE=1.0 BASELINE=1.0 UNIT=frac | `demos/out/alert.json` (brief also at `demos/out/watch_brief.md`) | `recommend` | $500–2,000/month per county or utility watch desk for briefing time, after a fire-safe council pilot. No agency-page contracts from this demo. |
| Water Pulse | `plan_match` VALUE=1.0 BASELINE=1.0 UNIT=frac | `demos/out/schedule_F-01_2026-09-14.json` (dry/run night; 2026-09-13 is skip) | `recommend` | $8–20/acre/season or a share of measured kWh/water saved after one ranch pilot. |
| Yard & Dock Pulse | `dwell_min` VALUE=470 BASELINE=1090 UNIT=min | `demos/out/assignment_0600.json` | `recommend` | $2–5k/month per site after a DC pilot, sold against detention and overtime. |

Default autonomy is `recommend`. Buyer PO is the only demo artifact written at
`act_under_cap`. Lane `book` is not in `demos/lane.md`. `demos/out/operator@local.txt`
is a shared FileChannel sink (last writer wins). Watch is fixture fusion, not an
official forecast.

## Non-goals (POLICY)

From `AGENTS.md`:

- Two-sided marketplaces (no public load board, no vendor social network)
- Trading or “money-printing” bots
- Live 911 / NIFC / USFS / county duty-desk pages
- Live freight booking or live payment
- Live pump, valve, or equipment actuation unless POLICY.md and a human allow that exact action
- Rewriting chassis interfaces inside a domain to dodge policy

From `POLICY.md` blocked (never, including in demos):

- 911, NIFC, USFS, Cal Fire, county OES / duty-officer desks, official radio
- Claims that this stack predicts ignition or spread better than NOAA / USFS
- Live DAT / Truckstop / broker booking that spends or commits a truck
- Live payment rails (cards, ACH, crypto)
- Trading, brokerage order placement, or “alpha” agents
- Scraping behind logins that are not Paul’s test accounts
- Storing SSNs, bank accounts, driver’s license images, or unredacted bills of lading with personal data in git

Notify allowlist until Paul extends it in writing: `operator@local` (file / console
sink), the project Grok Bot channel, and addresses Paul types interactively.

There is no “fully autonomous / ignore the human” tier.

## Reproduce

```
python -m domains.lane quote --load L-07
python -m domains.lane watch --load L-07 --truck T-07
python -m evals.lane_harness

python -m domains.buyer rank --spec BOX-24
python -m domains.buyer draft --spec BOX-24
python -m domains.buyer po --spec BOX-24 --approve
python -m evals.buyer_harness

python -m domains.watch brief --replay calm
python -m domains.watch brief --replay hot
python -m evals.watch_harness

python -m domains.water plan --date 2026-09-13
python -m domains.water plan --date 2026-09-14
python -m evals.water_harness

python -m domains.yard assign --wave 06:00
python -m domains.yard dwell
python -m evals.yard_harness
```

Walkthroughs: `demos/lane.md`, `demos/buyer.md`, `demos/watch.md`, `demos/water.md`,
`demos/yard.md`.
