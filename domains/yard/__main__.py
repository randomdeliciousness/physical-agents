"""CLI: python -m domains.yard assign|dwell|confirm."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from chassis.agent import Agent
from chassis.channels import FileChannel
from chassis.goal import Goal, Tier
from chassis.tools import FunctionTool
from domains.yard.assign import (
    assign_wave,
    format_door_map,
    get_appointment,
    write_assignment,
)
from domains.yard.dwell import (
    DWELL_CAP_MIN,
    confirm_checkin,
    draft_overrun,
    event_dwells,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "demos" / "out"


def _agent() -> Agent:
    return Agent("yard")


def cmd_assign(wave: str) -> int:
    plan = assign_wave(wave)
    OUT.mkdir(parents=True, exist_ok=True)
    goal = Goal(
        id=f"yard-assign-{wave}",
        domain="yard",
        text=f"assign wave {wave}",
        tier=Tier.RECOMMEND,
    )
    agent = _agent()
    agent.register(FunctionTool("assignment", lambda: write_assignment(plan, OUT)))
    decision, result = agent.act(
        goal,
        action="write_assignment",
        tool_name="assignment",
    )
    print(format_door_map(plan))
    if not decision.ok or result is None or not result.ok:
        print(f"verdict={decision.verdict} note={decision.note}", file=sys.stderr)
        return 1
    print(f"verdict={decision.verdict} artifact={result.data}")
    return 0


def cmd_dwell(cap_min: int) -> int:
    rows = event_dwells()
    draft = draft_overrun(rows, cap_min)
    goal = Goal(
        id="yard-dwell",
        domain="yard",
        text="flag dwell over cap",
        tier=Tier.RECOMMEND,
        extra={"dwell_cap_min": cap_min},
    )
    agent = _agent()
    for row in rows:
        flag = "overrun" if row.over_cap(cap_min) else "quiet"
        extra = f" cap={cap_min}" if flag == "overrun" else ""
        print(f"{row.appointment_id} dwell={row.dwell_min} min {flag}{extra}")
    if draft is None:
        decision, _ = agent.act(goal, action="compute")
        print("overruns=0")
        if not decision.ok:
            print(f"verdict={decision.verdict} note={decision.note}", file=sys.stderr)
            return 1
        print(f"verdict={decision.verdict}")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    decision, result = agent.act(
        goal,
        action="draft",
        destination="operator@local",
        channel=FileChannel(OUT),
        message=draft,
    )
    print(f"overruns={draft.count('Appointment ')}")
    print(draft.rstrip())
    if not decision.ok:
        print(f"verdict={decision.verdict} note={decision.note}", file=sys.stderr)
        return 1
    print(f"verdict={decision.verdict} dest=operator@local")
    return 0


def cmd_confirm(appointment_id: str, party: str) -> int:
    get_appointment(appointment_id)
    agent = _agent()
    agent.register(
        FunctionTool("confirm", lambda: confirm_checkin(appointment_id, party, OUT))
    )
    goal = Goal(
        id=f"yard-confirm-{appointment_id}-{party}",
        domain="yard",
        text=f"confirm {party} {appointment_id}",
        tier=Tier.RECOMMEND,
    )
    decision, result = agent.act(goal, action="compute", tool_name="confirm")
    if not decision.ok or result is None or not result.ok:
        print(f"verdict={decision.verdict} note={decision.note}", file=sys.stderr)
        return 1
    rec = result.data
    print(
        f"status={rec['status']} appointment={appointment_id} party={party} "
        f"driver={rec['driver_confirmed']} dock={rec['dock_confirmed']}"
    )
    print(f"verdict={decision.verdict} artifact={OUT / f'yard_run_{appointment_id}.json'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m domains.yard")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_assign = sub.add_parser("assign", help="greedy door map for a morning inbound wave")
    p_assign.add_argument("--wave", required=True, help="wave clock HH:MM, e.g. 06:00")

    p_dwell = sub.add_parser("dwell", help="flag event dwell over cap; one local draft")
    p_dwell.add_argument("--cap-min", type=int, default=DWELL_CAP_MIN)

    p_confirm = sub.add_parser("confirm", help="driver or dock check-in confirm")
    p_confirm.add_argument("--appointment", required=True)
    p_confirm.add_argument("--party", required=True, choices=["driver", "dock"])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "assign":
            return cmd_assign(args.wave)
        if args.cmd == "dwell":
            return cmd_dwell(args.cap_min)
        if args.cmd == "confirm":
            return cmd_confirm(args.appointment, args.party)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
