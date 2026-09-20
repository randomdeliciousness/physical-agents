# Demo — Water Pulse (~2 min)

1. `PYTHONPATH=. python -m domains.water plan --date 2026-09-13` → skip (rain).
2. `PYTHONPATH=. python -m domains.water plan --date 2026-09-14` → run.
3. Show 3-night plan file in `demos/out/`.
4. Confirm no actuator call in the audit row.
5. `PYTHONPATH=. python -m evals.water_harness`
