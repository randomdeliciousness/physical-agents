# POLICY.md — physical-agents

Source of truth for autonomy. `chassis/policy.py` must stay consistent with this file.
Grok Bot **Policy** reviews actions against this document. When they disagree, this file wins until Paul edits it.

Last updated: 2026-09-14

## Autonomy tiers

| Tier | Meaning | Default |
|---|---|---|
| `observe` | Read fixtures, feeds, logs. Write nothing external. | always allowed |
| `recommend` | Compute, rank, draft messages and artifacts locally. | **default** |
| `act_under_cap` | Perform a named action inside a numeric cap on a Goal | only if Goal.cap is set and Policy allows the action type |
| `escalate` | Stop and ask Paul (or Policy Bot → Paul) | anything irreversible or unknown |

There is no “fully autonomous / ignore the human” tier in this repo.

## Action catalog

### Always allowed (observe / recommend)

- Read files under `data/fixtures/`, `demos/`, `evals/`
- Run domain models and unit tests
- Write run artifacts under `demos/out/` and audit rows
- Draft SMS, email, voice scripts, POs, briefs, resource-request text
- Pull **public** weather and incident feeds in Watch *adapters* when a stage ticket says so (not inside unit tests)

### Require Paul for this specific action (`escalate`)

- Any SMS, email, Slack, or voice call to a real outside party
- Connecting Twilio, Gmail send, or any dialer
- Any spend, refund, booking, tender, or PO sent to a vendor
- Any pump, valve, door, or equipment command (`actuate=true`)
- Adding a notify destination that is not already on the allowlist below
- Weakening this file or `chassis/policy.py`
- Creating a new Grok Bot

### Blocked (never, including in demos)

- 911, NIFC, USFS, Cal Fire, county OES / duty-officer desks, official radio
- Claims that this stack predicts ignition or spread better than NOAA / USFS
- Live DAT / Truckstop / broker booking that spends or commits a truck
- Live payment rails (cards, ACH, crypto)
- Trading, brokerage order placement, or “alpha” agents
- Scraping behind logins that are not Paul’s test accounts
- Storing SSNs, bank accounts, driver’s license images, or unredacted bills of lading with personal data in git

## Notify allowlist (Watch Officer and exception channels)

Until Paul extends this list in writing, the only legal notify targets are:

- `operator@local` (file / console sink)
- Project Grok Bot channel (Floor PM / Ops)
- Addresses Paul types interactively in a session

`chassis/policy.py` must reject any other destination.

## Caps (used with `act_under_cap`)

These are demo/sandbox caps. They do not authorize live money.

| Domain | Cap | Notes |
|---|---|---|
| Lane | auto-book only if `goal.cap_usd_per_mi` is set AND destination is synthetic | still no live broker |
| Buyer | PO file write if `goal.approved is True` and `total <= goal.cap_usd` | send is still escalate |
| Watch | alert file write; send is escalate | allowlist only |
| Water | schedule file write | `actuate` is escalate then blocked until a named device exists |
| Yard | assignment file write | live dock hardware escalate |

If a cap is missing, the engine must `escalate`, not guess.

## Dual confirmation

Lane delivery and Yard check-in are not complete until two parties confirm in the run record (`driver` + `receiver`, or `driver` + `dock`). One confirmation is `recommend` only.

## Public-safety language

Watch Officer may quote public feeds and apply YAML rules. It must label every number with its source or `unknown`. It must not:

- Issue evacuation orders
- Assign crews
- Page agencies
- Invent containment %, casualties, or acreage

## Data retention

- Audit log: `data/audit.jsonl` (append-only)
- Do not commit secrets. Use environment variables for any future API keys.
- Fixtures are synthetic or public-domain extracts. Do not check in live ELD streams.

## Review protocol

1. Engineer Bot or Grok Build proposes an action.
2. If the action type is allow-listed above, proceed and audit.
3. If it is “require Paul”, Policy Bot replies `ESCALATE` and Floor PM pings Paul.
4. If it is blocked, Policy Bot replies `BLOCK` and work stops.
5. Paul may grant a one-time exception in the project channel. Log it. Do not encode one-time exceptions as new defaults without editing this file.

## Income and sales claims

Demos may show a *hypothetical* fee model. They must not collect payment or promise official-agency contracts.
