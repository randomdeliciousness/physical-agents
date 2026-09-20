# domains/buyer

Landed-Cost Buyer. Ranks fixture vendors by list landed cost (unit × qty + zone shipping + $25/day over 7, dropping MOQ misses and lead past need-by). Drafts a 10%-off-or-walk counter. Writes a local PO markdown only when `approved=true`. No email, no send.

```
python -m domains.buyer rank --spec BOX-24
python -m domains.buyer draft --spec BOX-24
python -m domains.buyer po --spec BOX-24
python -m domains.buyer po --spec BOX-24 --approve
python -m evals.buyer_harness
```

Default autonomy is `recommend`. `po --approve` is `act_under_cap` and writes `demos/out/po_<spec>.md` only. Optional `--cap-usd` blocks the write if the reservation total exceeds the cap.
