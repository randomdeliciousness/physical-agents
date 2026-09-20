"""Water eval: wet fixture night skips, dry fixture night runs."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from chassis.goal import Goal
from chassis.policy import PolicyEngine
from domains.water.planner import plan_nights, write_schedule

BASELINE = 1.0
WET = "2026-09-13"
DRY = "2026-09-14"


def main() -> int:
    hits = 0
    wet = plan_nights("F-01", WET)
    dry = plan_nights("F-01", DRY)
    if wet.tonight == "skip":
        hits += 1
    if dry.tonight == "run":
        hits += 1
    value = hits / 2.0

    engine = PolicyEngine()
    goal = Goal(id="water-eval", domain="water", text="plan")
    blocked = engine.check(goal, "actuate")
    allowed = engine.check(goal, "write_schedule")

    actuate_false = False
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = write_schedule(dry, root)
        leftover = list(root.glob("schedule_*.json"))
        if path.exists() and leftover == [path]:
            payload = json.loads(path.read_text(encoding="utf-8"))
            actuate_false = payload.get("actuate") is False and payload.get("tonight") == "run"

    passed = (
        value >= BASELINE
        and wet.tonight == "skip"
        and dry.tonight == "run"
        and wet.tonight != dry.tonight
        and blocked.verdict == "BLOCK"
        and allowed.verdict == "ALLOW"
        and actuate_false
    )
    flag = 1 if passed else 0
    print(
        f"DOMAIN=water PASS={flag} METRIC=plan_match VALUE={value:.1f} "
        f"BASELINE={BASELINE:.1f} UNIT=frac"
    )
    if not passed:
        print(
            f"wet={wet.tonight} dry={dry.tonight} actuate_false={actuate_false} "
            f"block={blocked.verdict} allow={allowed.verdict} hits={hits}",
            file=sys.stderr,
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
