"""CLI: python -m domains.water plan --date YYYY-MM-DD."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Sequence

from chassis.agent import Agent
from chassis.channels import FileChannel
from chassis.goal import Goal, Tier
from chassis.tools import FunctionTool
from domains.water.planner import plan_nights, render_message, write_schedule

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "demos" / "out"
DEFAULT_FIELD = "F-01"


def _agent() -> Agent:
    return Agent("water")


def cmd_plan(as_of: date, field_id: str) -> int:
    plan = plan_nights(field_id, as_of)
    tonight = plan.nights[0]
    OUT.mkdir(parents=True, exist_ok=True)
    message = render_message(plan)
    goal = Goal(
        id=f"water-plan-{field_id}-{as_of.isoformat()}",
        domain="water",
        text=f"plan {field_id} {as_of.isoformat()}",
        tier=Tier.RECOMMEND,
    )
    agent = _agent()
    agent.register(FunctionTool("schedule", lambda: write_schedule(plan, OUT)))
    decision, result = agent.act(
        goal,
        action="write_schedule",
        tool_name="schedule",
        destination="operator@local",
        channel=FileChannel(OUT),
        message=message,
    )
    print(
        f"tonight={plan.tonight} field={plan.field_id} date={plan.as_of.isoformat()} "
        f"rain={tonight.forecast_rain_in:.2f}"
    )
    nights = ",".join(f"{n.date.isoformat()}:{n.action}" for n in plan.nights)
    print(f"nights={nights}")
    if not decision.ok or result is None or not result.ok:
        print(f"verdict={decision.verdict} note={decision.note}", file=sys.stderr)
        return 1
    print(f"verdict={decision.verdict} artifact={result.data} dest=operator@local")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m domains.water")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_plan = sub.add_parser("plan", help="tonight run/skip plus a 3-night local schedule")
    p_plan.add_argument("--date", required=True, help="plan date YYYY-MM-DD")
    p_plan.add_argument("--field", default=DEFAULT_FIELD)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "plan":
            as_of = date.fromisoformat(args.date)
            return cmd_plan(as_of, args.field)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
