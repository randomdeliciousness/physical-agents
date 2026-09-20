# Plan 03 — Watch Officer

Status: **approved**

Implement only `domains/watch/`, `evals/watch_harness.py`, `tests/test_watch.py`, and `domains/watch/README.md`. No water / yard. No live feeds. No SMS.

## Pins

1. **No chassis / POLICY.md edits.** `PolicyEngine` already BLOCKs agency tokens (`nifc`, `usfs`, `911`, `calfire`, `oes`, duty-desk) and any destination not in `ALLOWLIST` (`operator@local`, `channel:physical-agents`) or `goal.notify`. Watch must call `chassis.policy` before any notify/alert write. Do not copy `--dest` onto `goal.notify` (that would add a notify target = escalate / policy dodge).
2. **Alert file write is `recommend`.** Action `write_alert`. No `--approve`, no `act_under_cap`, no send. Real SMS/email = not implemented (would ESCALATE). Agency dest = BLOCK, no `alert.json`.
3. **Stdlib only.** No PyYAML. `load_rules()` is a schema-specific reader for `data/fixtures/watch_rules.yml` (this fixture’s maps/lists). No new dependencies.
4. **Fail closed on unknown.** Every number is `{value, source}` or `source="unknown"`. If a required observation is unknown, or a `sources_required` adapter did not run, that condition does not fire. No alert.
5. **Do not invent containment %, casualties, acreage, evacuations, or crew assignments.** Brief and `alert.json` only quote fixture fields plus rule hits. `incidents` in replay is empty; pass through as-is, never fill.
6. **No spread model.** Use fixture hotspot `km` when present (keep its `source`). If `km` is missing, haversine from AOI lat/lon and label `source="haversine-aoi"`. Never invent km.
7. **Both replays write `demos/out/watch_brief.md`.** Only a firing day writes `demos/out/alert.json` and FileChannel `operator@local`. Calm is silent on alerts.

## Layout

```
domains/watch/__init__.py
domains/watch/__main__.py          brief [--replay calm|hot] [--dest]
domains/watch/adapters.py          fixture loader + public stubs (no network)
domains/watch/rules.py             YAML load + all_of engine
domains/watch/brief.py             markdown brief + alert.json
domains/watch/README.md
evals/watch_harness.py
tests/test_watch.py
```

Keep `demos/watch.md` as written; only edit if CLI flags diverge.

## Verify

```
python -m unittest tests.test_watch tests.test_chassis tests.test_buyer tests.test_lane -q
python -m domains.watch brief --replay calm
python -m domains.watch brief --replay hot
python -m domains.watch brief --replay hot --dest nifc@example.gov
python -m evals.watch_harness
```

Do not claim done without those outputs. Commit when tests pass. Do not start stage 04 in this session.
