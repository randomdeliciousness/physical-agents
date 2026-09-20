# domains/yard

Yard & Dock Pulse. Greedy door assign for a morning inbound wave (match type, earliest start, unused door, then lowest id). Event dwell over 90 min drafts one local driver/dock note. Check-in complete needs driver and dock confirm. No WMS. No dock hardware.

```
python -m domains.yard assign --wave 06:00
python -m domains.yard dwell
python -m domains.yard confirm --appointment A-03 --party driver
python -m evals.yard_harness
```

Assignment file write is `recommend`. `actuate` is BLOCK. First-door-free baseline (queue on the first matching door) lives in the harness comparator.
