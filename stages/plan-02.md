# Plan 02 — Landed-Cost Buyer

Status: **approved** (pins 2 and 5 stand; pin 3 = rank at list, reservation only on draft/PO)

Implement only the paths below. No watch / water / yard. No email.

## Pins

1. **Eligible vendors**: exact `sku` match **and** `qty >= moq`. Drop the rest.
2. **Lead-time**: penalty **$25 per day over 7** (`max(0, lead_days - 7)`). **Hard-drop** vendors with `lead_days > need_by_days`.
3. **Rank on list `unit_price`**. Draft and PO use reservation `0.90 * list`, never below `floor`. If `0.90 * list < floor`, target `floor` and walk rather than go under floor.
4. **PO artifact is markdown** `demos/out/po_<spec_id>.md`. No PDF library.
5. **Cap is optional**. If `--cap-usd` is set and PO total exceeds it → escalate, no file. Missing cap does not block an approved write.
6. **No chassis / POLICY.md edits.** `write_po` at `Tier.ACT_UNDER_CAP` with `goal.approved` from `--approve`. Never implement send.

Expected BOX-24 (qty 2000, zone A, need_by 10): **V-05 at 3610.00**. V-03 dropped (lead 12 > 10). Reservation V-05 **$1.512**.

## Layout

```
domains/buyer/__init__.py
domains/buyer/__main__.py          rank | draft | po
domains/buyer/landed_cost.py
domains/buyer/negotiate.py
domains/buyer/po.py
domains/buyer/README.md
evals/buyer_harness.py
tests/test_buyer.py
```

## Verify

```
python -m unittest tests.test_buyer tests.test_chassis tests.test_lane -q
python -m domains.buyer rank --spec BOX-24
python -m domains.buyer draft --spec BOX-24
python -m domains.buyer po --spec BOX-24
python -m domains.buyer po --spec BOX-24 --approve
python -m evals.buyer_harness
```
