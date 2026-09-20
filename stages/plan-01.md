# Plan 01 — Lane Cost & Exception

Status: **approved with two pins** (implementing)

## Pins (operator)

1. Late rule: **pickup + 15 minutes first**. Do not let ETA-to-Dallas hide a missed L-07 pickup. T-07/L-07 is the only draft.
2. Do **not** hard-filter matcher on `hos_h` this stage (multi-day loaded miles).

## Layout

```
domains/__init__.py
domains/lane/__init__.py
domains/lane/__main__.py         quote | watch | book | confirm
domains/lane/cost_model.py
domains/lane/matcher.py
domains/lane/exception.py
evals/lane_harness.py
evals/lane_oracle.json           freeze from the same formulas
tests/test_lane.py
```

No chassis / POLICY.md edits. No DAT, Truckstop, or network.

## Formulas

Loaded miles = `miles_hint`. Deadhead = haversine(truck → origin). Grade: flat 1.00, desert 1.08, mixed 1.12, mountain 1.28. Weight `1 + 0.20 * (weight_lb / 80000)`; empty deadhead 0.85. Diesel gal from mpg; battery kWh from `kwh_per_mi`. USD = energy ($4.25/gal or $0.16/kWh) + drive_h * driver rate + tolls. `drive_h = (deadhead + loaded) / 55`. `usd_per_mi = usd / loaded_mi`.

Matcher: exact `equip` only; rank by usd_per_mi; **no hos_h filter**.

Late: last crumb. If not already at dest, check pickup ETA vs pickup+15 first; only then delivery. One SMS draft via FileChannel to `operator@local`. Dual confirm in `demos/out/lane_run_<load>.json`.

Book: `book_synthetic` only if `cap_usd_per_mi` set, truck is a fixture, and quoted usd_per_mi <= cap.

## Verify

```
python -m unittest tests.test_lane tests.test_chassis -q
python -m domains.lane quote --load L-07
python -m domains.lane watch --load L-07 --truck T-07
python -m evals.lane_harness
```

No buyer in this session.
