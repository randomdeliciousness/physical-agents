# domains/water

Water Pulse. One field: soil-moisture CSV + forecast precip → tonight run/skip and a 3-night schedule. Human executes valves. No actuator client.

```
python -m domains.water plan --date 2026-09-13
python -m domains.water plan --date 2026-09-14
python -m evals.water_harness
```

Deficit accumulates ET and subtracts forecast rain. Irrigate when deficit > threshold (CSV `threshold_frac`, inches) and next-24h rain < 0.25 in. Wet fixture night (2026-09-13) skips; dry (2026-09-14) runs. Writes `demos/out/schedule_<field>_<date>.json` and a local irrigator note to `operator@local`. `actuate` is BLOCK.
