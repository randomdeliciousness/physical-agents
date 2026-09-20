# Demo — Lane Cost & Exception (~3 min)

Preconditions: stage 01 green.

1. `PYTHONPATH=. python -m domains.lane quote --load L-07`
2. Show top 3 trucks and USD/mi. Confirm T-07 is a candidate (same region + dry53).
3. `PYTHONPATH=. python -m domains.lane watch --load L-07 --truck T-07`
4. Expect one draft under `demos/out/` for the late breadcrumbs.
5. `PYTHONPATH=. python -m evals.lane_harness`
6. Read the `DOMAIN=lane ...` line aloud. Autonomy: recommend. No broker called.
