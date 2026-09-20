# Demo — Landed-Cost Buyer (~3 min)

1. `PYTHONPATH=. python -m domains.buyer rank --spec BOX-24`
2. Show landed-cost table. Note shipping + lead penalty, not unit price alone.
3. `PYTHONPATH=. python -m domains.buyer draft --spec BOX-24`
4. Show reservation 10% off list. Confirm no email left the box.
5. `PYTHONPATH=. python -m domains.buyer po --spec BOX-24`  → must refuse.
6. `PYTHONPATH=. python -m domains.buyer po --spec BOX-24 --approve`
7. Open `demos/out/` PO artifact.
8. `PYTHONPATH=. python -m evals.buyer_harness`
