"""Watch eval: calm silent, hot exactly one allowlist alert, agency dest BLOCK."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from chassis.goal import Goal
from chassis.policy import PolicyEngine
from domains.watch.adapters import FixtureAdapter
from domains.watch.brief import write_alert
from domains.watch.rules import evaluate, load_rules

BASELINE = 1.0


def main() -> int:
    rules = load_rules()
    fx = FixtureAdapter()
    hits = 0

    calm = evaluate(rules, fx.load_day("calm"))
    if not calm.fire:
        hits += 1

    hot_day = fx.load_day("hot")
    hot = evaluate(rules, hot_day)
    dest_ok = False
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = write_alert(
            rules, hot_day, hot, destination="operator@local", dest=root
        )
        leftover = list(root.glob("alert.json"))
        if hot.fire and path is not None and path.exists() and leftover == [path]:
            payload = json.loads(path.read_text(encoding="utf-8"))
            dest_ok = (
                payload.get("destination") == "operator@local"
                and payload.get("day") == "2026-09-08"
                and len(payload.get("rules_fired") or []) == 4
            )
    if dest_ok:
        hits += 1

    value = hits / 2.0
    engine = PolicyEngine()
    goal = Goal(id="watch-eval", domain="watch", text="alert")
    blocked = engine.check(goal, "write_alert", destination="nifc@example.gov")
    allowed = engine.check(goal, "write_alert", destination="operator@local")
    passed = (
        value >= BASELINE
        and dest_ok
        and not calm.fire
        and hot.fire
        and blocked.verdict == "BLOCK"
        and allowed.verdict == "ALLOW"
    )
    flag = 1 if passed else 0
    print(
        f"DOMAIN=watch PASS={flag} METRIC=alert_precision VALUE={value:.1f} "
        f"BASELINE={BASELINE:.1f} UNIT=frac"
    )
    if not passed:
        print(
            f"calm_fire={calm.fire} hot_fire={hot.fire} dest_ok={dest_ok} "
            f"block={blocked.verdict} allow={allowed.verdict} hits={hits}",
            file=sys.stderr,
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
