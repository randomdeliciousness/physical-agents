"""CLI: python -m domains.lane quote|watch|book|confirm."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from chassis.agent import Agent
from chassis.audit import RunLog, append_audit
from chassis.channels import FileChannel
from chassis.goal import Goal, Tier
from chassis.tools import FunctionTool
from domains.lane.cost_model import Quote, quote_truck
from domains.lane.exception import confirm_delivery, watch_draft
from domains.lane.matcher import format_rank_table, get_load, get_truck, load_trucks, rank

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "demos" / "out"


def _agent() -> Agent:
    return Agent("lane")


def cmd_quote(load_id: str) -> int:
    load = get_load(load_id)
    agent = _agent()
    agent.register(FunctionTool("quote", lambda: rank(load)))
    goal = Goal(id=f"lane-quote-{load_id}", domain="lane", text=f"quote {load_id}", tier=Tier.RECOMMEND)
    decision, result = agent.act(goal, action="compute", tool_name="quote")
    if not decision.ok or result is None or not result.ok:
        print(f"verdict={decision.verdict} note={decision.note}", file=sys.stderr)
        return 1
    quotes: list[Quote] = result.data
    print(format_rank_table(load, quotes))
    return 0


def cmd_watch(load_id: str, truck_id: str) -> int:
    load = get_load(load_id)
    get_truck(truck_id)  # fixture-only
    draft = watch_draft(load, truck_id)
    goal = Goal(
        id=f"lane-watch-{load_id}-{truck_id}",
        domain="lane",
        text=f"watch {truck_id} on {load_id}",
        tier=Tier.RECOMMEND,
    )
    agent = _agent()
    OUT.mkdir(parents=True, exist_ok=True)
    if draft is None:
        decision, _ = agent.act(goal, action="compute")
        print(f"on time: {truck_id} / {load_id} (no draft) verdict={decision.verdict}")
        return 0
    decision, _ = agent.act(
        goal,
        action="draft",
        destination="operator@local",
        channel=FileChannel(OUT),
        message=draft,
    )
    print(draft.rstrip())
    print(f"verdict={decision.verdict} artifact={OUT / 'operator@local.txt'}")
    return 0


def _write_book(load: dict[str, Any], truck: dict[str, Any], quote: Quote, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"book_{load['id']}_{truck['id']}.json"
    payload = {
        "load_id": load["id"],
        "truck_id": truck["id"],
        "usd": round(quote.usd, 4),
        "usd_per_mi": round(quote.usd_per_mi, 6),
        "synthetic": True,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def cmd_book(load_id: str, truck_id: str, cap_usd_per_mi: float | None) -> int:
    load = get_load(load_id)
    goal = Goal(
        id=f"lane-book-{load_id}-{truck_id}",
        domain="lane",
        text=f"book {truck_id} on {load_id}",
        tier=Tier.ACT_UNDER_CAP,
        cap_usd_per_mi=cap_usd_per_mi,
    )
    agent = _agent()
    try:
        truck = get_truck(truck_id)
    except KeyError:
        append_audit(
            RunLog(
                goal_id=goal.id,
                domain="lane",
                action="book_synthetic",
                verdict="ESCALATE",
                note=f"{truck_id} is not a synthetic fixture truck",
            )
        )
        print(f"verdict=ESCALATE note={truck_id} is not a synthetic fixture truck")
        return 1
    quote = quote_truck(truck, load)
    if cap_usd_per_mi is not None and quote.usd_per_mi > cap_usd_per_mi:
        append_audit(
            RunLog(
                goal_id=goal.id,
                domain="lane",
                action="book_synthetic",
                verdict="ESCALATE",
                note=f"usd_per_mi {quote.usd_per_mi:.4f} exceeds cap {cap_usd_per_mi}",
            )
        )
        print(
            f"verdict=ESCALATE note=usd_per_mi {quote.usd_per_mi:.4f} exceeds cap {cap_usd_per_mi}"
        )
        return 1
    agent.register(
        FunctionTool("book", lambda: _write_book(load, truck, quote, OUT))
    )
    decision, result = agent.act(goal, action="book_synthetic", tool_name="book")
    if not decision.ok:
        print(f"verdict={decision.verdict} note={decision.note}")
        return 1
    path = None if result is None else result.data
    print(f"verdict={decision.verdict} artifact={path} usd_per_mi={quote.usd_per_mi:.3f}")
    return 0


def cmd_confirm(load_id: str, party: str) -> int:
    get_load(load_id)
    agent = _agent()
    agent.register(FunctionTool("confirm", lambda: confirm_delivery(load_id, party, OUT)))
    goal = Goal(
        id=f"lane-confirm-{load_id}-{party}",
        domain="lane",
        text=f"confirm {party} {load_id}",
        tier=Tier.RECOMMEND,
    )
    decision, result = agent.act(goal, action="compute", tool_name="confirm")
    if not decision.ok or result is None or not result.ok:
        print(f"verdict={decision.verdict} note={decision.note}", file=sys.stderr)
        return 1
    rec = result.data
    print(json.dumps(rec))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m domains.lane")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_quote = sub.add_parser("quote", help="rank trucks for a load")
    p_quote.add_argument("--load", required=True)

    p_watch = sub.add_parser("watch", help="draft one SMS if late to pickup/delivery")
    p_watch.add_argument("--load", required=True)
    p_watch.add_argument("--truck", required=True)

    p_book = sub.add_parser("book", help="local book artifact under cap_usd_per_mi")
    p_book.add_argument("--load", required=True)
    p_book.add_argument("--truck", required=True)
    p_book.add_argument("--cap-usd-per-mi", type=float, default=None)

    p_confirm = sub.add_parser("confirm", help="driver or receiver confirm")
    p_confirm.add_argument("--load", required=True)
    p_confirm.add_argument("--party", required=True, choices=["driver", "receiver"])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "quote":
            return cmd_quote(args.load)
        if args.cmd == "watch":
            return cmd_watch(args.load, args.truck)
        if args.cmd == "book":
            return cmd_book(args.load, args.truck, args.cap_usd_per_mi)
        if args.cmd == "confirm":
            return cmd_confirm(args.load, args.party)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
