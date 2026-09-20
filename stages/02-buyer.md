# Stage 02 — Landed-Cost Buyer

Status: open only after 01 is frozen

## Goal

Spec in → rank fixture vendors by landed cost → draft a negotiation inside the mandate → write a PO PDF/markdown only if `approved=true`.

## Path

`domains/buyer/`  
Fixtures: `data/fixtures/vendors.csv`, `buyer_specs.json`, `mandates/default.md`

## Domain model

`landed = unit_price * qty + shipping(zone) + lead_time_penalty_per_day * days`

Mandate: 10% off list or walk; max 3 rounds; never send.

## Autonomy

`recommend` drafts. PO file write requires `goal.approved is True` and total <= `cap_usd` if cap set. Send = escalate (not implemented).

## Eval

15 specs in `buyer_specs.json`. Harness asserts the cheapest landed vendor wins each time. Unapproved runs create no PO file.

```
DOMAIN=buyer PASS=1 METRIC=rank_acc VALUE=1.0 BASELINE=1.0 UNIT=frac
```

## Acceptance

- [ ] Rank table for spec BOX-24
- [ ] Draft counter uses reservation price from mandate
- [ ] No PO without approved flag
- [ ] `demos/buyer.md` works

## Build prompt

```text
Read AGENTS.md, POLICY.md, stages/02-buyer.md, data/fixtures/vendors.csv, data/fixtures/buyer_specs.json, mandates/default.md.
Plan domains/buyer/ with landed_cost.py, negotiate.py, po.py, cli, evals/buyer_harness.py.
PO write gated on approved=true.
No email send. Stop for approval.
```

## Hypothetical income

5–15% of documented tail-spend savings or $1–3k/month per buyer desk.
