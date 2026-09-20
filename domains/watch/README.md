# domains/watch

Watch Officer. Fuses fixture weather and hotspot rows for one AOI, applies YAML `alert_all_of` rules, and writes a local brief. Emits `alert.json` only when every clause fires. Notify allowlist is `operator@local` (file sink). No SMS. Agency destinations are BLOCK.

```
python -m domains.watch brief --replay calm
python -m domains.watch brief --replay hot
python -m domains.watch brief --replay hot --dest nifc@example.gov
python -m evals.watch_harness
```

Public NWS/hotspot adapters are stubs (unknown values, no network). Numbers carry `source` or `unknown`. This is fusion, not a replacement for NOAA/USFS. Do not page agencies.
