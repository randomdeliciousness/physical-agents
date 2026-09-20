# Demo — Watch Officer (~3 min)

1. `PYTHONPATH=. python -m domains.watch brief --replay calm` → no alert file.
2. `PYTHONPATH=. python -m domains.watch brief --replay hot` → brief + one alert to operator@local.
3. Attempt a destination `nifc@example.gov` in a dry run if the CLI supports `--dest`; expect BLOCK.
4. Read the disclaimer in the brief: fusion, not official forecast.
5. `PYTHONPATH=. python -m evals.watch_harness`
