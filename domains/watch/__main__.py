"""CLI: python -m domains.watch brief --replay calm|hot [--dest]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from chassis.agent import Agent
from chassis.channels import FileChannel
from chassis.goal import Goal, Tier
from chassis.tools import FunctionTool
from domains.watch.adapters import FixtureAdapter
from domains.watch.brief import (
    alert_payload,
    render_brief,
    render_notify,
    write_alert,
    write_brief,
)
from domains.watch.rules import evaluate, load_rules

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "demos" / "out"


def _agent() -> Agent:
    return Agent("watch")


def cmd_brief(replay: str, destination: str) -> int:
    rules = load_rules()
    day = FixtureAdapter().load_day(replay)
    ev = evaluate(rules, day)
    body = render_brief(rules, day, ev)
    OUT.mkdir(parents=True, exist_ok=True)

    # Destination is a policy argument only. Never copy it onto goal.notify.
    goal = Goal(
        id=f"watch-brief-{replay}",
        domain="watch",
        text=f"brief {replay}",
        tier=Tier.RECOMMEND,
    )
    agent = _agent()
    agent.register(FunctionTool("brief", lambda: write_brief(body, OUT)))
    decision, result = agent.act(goal, action="draft", tool_name="brief")
    if not decision.ok or result is None or not result.ok:
        print(f"verdict={decision.verdict} note={decision.note}", file=sys.stderr)
        return 1
    print(body.rstrip())
    print(f"verdict={decision.verdict} artifact={result.data}")

    if not ev.fire:
        print("alert=none")
        return 0

    agent.register(
        FunctionTool(
            "alert",
            lambda: write_alert(rules, day, ev, destination=destination, dest=OUT),
        )
    )
    notify = render_notify(alert_payload(rules, day, ev, destination))
    decision2, result2 = agent.act(
        goal,
        action="write_alert",
        tool_name="alert",
        destination=destination,
        channel=FileChannel(OUT),
        message=notify,
    )
    if not decision2.ok:
        print(f"verdict={decision2.verdict} note={decision2.note}")
        return 1
    path = None if result2 is None else result2.data
    print(f"verdict={decision2.verdict} artifact={path} dest={destination}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m domains.watch")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_brief = sub.add_parser("brief", help="fuse one replay day into a local brief")
    p_brief.add_argument("--replay", required=True, help="calm or hot (fixture key)")
    p_brief.add_argument("--dest", default="operator@local")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "brief":
            return cmd_brief(args.replay, args.dest)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
