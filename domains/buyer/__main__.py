"""CLI: python -m domains.buyer rank|draft|po."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from chassis.agent import Agent
from chassis.audit import RunLog, append_audit
from chassis.goal import Goal, Tier
from chassis.tools import FunctionTool
from domains.buyer.landed_cost import format_rank_table, get_spec, rank
from domains.buyer.negotiate import draft_counter
from domains.buyer.po import po_total, write_po

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "demos" / "out"


def _agent() -> Agent:
    return Agent("buyer")


def cmd_rank(spec_id: str) -> int:
    spec = get_spec(spec_id)
    agent = _agent()
    agent.register(FunctionTool("rank", lambda: rank(spec)))
    goal = Goal(
        id=f"buyer-rank-{spec_id}",
        domain="buyer",
        text=f"rank {spec_id}",
        tier=Tier.RECOMMEND,
    )
    decision, result = agent.act(goal, action="compute", tool_name="rank")
    if not decision.ok or result is None or not result.ok:
        print(f"verdict={decision.verdict} note={decision.note}", file=sys.stderr)
        return 1
    print(format_rank_table(spec, result.data))
    return 0


def cmd_draft(spec_id: str) -> int:
    spec = get_spec(spec_id)
    quotes = rank(spec)
    if not quotes:
        print(f"error: no eligible vendors for {spec_id}", file=sys.stderr)
        return 2
    draft = draft_counter(spec, quotes[0])
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"draft_{spec_id}.txt"

    def _write() -> Path:
        dest.write_text(draft, encoding="utf-8")
        return dest

    agent = _agent()
    agent.register(FunctionTool("draft", _write))
    goal = Goal(
        id=f"buyer-draft-{spec_id}",
        domain="buyer",
        text=f"draft {spec_id}",
        tier=Tier.RECOMMEND,
    )
    decision, result = agent.act(goal, action="draft", tool_name="draft")
    if not decision.ok or result is None or not result.ok:
        print(f"verdict={decision.verdict} note={decision.note}", file=sys.stderr)
        return 1
    print(draft.rstrip())
    print(f"verdict={decision.verdict} artifact={dest}")
    return 0


def cmd_po(spec_id: str, approved: bool, cap_usd: float | None) -> int:
    spec = get_spec(spec_id)
    quotes = rank(spec)
    goal = Goal(
        id=f"buyer-po-{spec_id}",
        domain="buyer",
        text=f"po {spec_id}",
        tier=Tier.ACT_UNDER_CAP,
        cap_usd=cap_usd,
        approved=approved,
    )
    agent = _agent()
    if not quotes:
        append_audit(
            RunLog(
                goal_id=goal.id,
                domain="buyer",
                action="write_po",
                verdict="ESCALATE",
                note=f"no eligible vendors for {spec_id}",
            )
        )
        print(f"verdict=ESCALATE note=no eligible vendors for {spec_id}")
        return 1
    quote = quotes[0]
    if not approved:
        decision, _ = agent.act(goal, action="write_po")
        print(f"verdict={decision.verdict} note={decision.note}")
        return 1
    total = po_total(quote)
    if cap_usd is not None and total > cap_usd:
        append_audit(
            RunLog(
                goal_id=goal.id,
                domain="buyer",
                action="write_po",
                verdict="ESCALATE",
                note=f"po total {total:.2f} exceeds cap {cap_usd}",
            )
        )
        print(f"verdict=ESCALATE note=po total {total:.2f} exceeds cap {cap_usd}")
        return 1
    agent.register(
        FunctionTool(
            "po",
            lambda: write_po(spec, quote, approved=True, dest=OUT, cap_usd=cap_usd),
        )
    )
    decision, result = agent.act(goal, action="write_po", tool_name="po")
    if not decision.ok:
        print(f"verdict={decision.verdict} note={decision.note}")
        return 1
    path = None if result is None else result.data
    if path is None:
        print("verdict=ESCALATE note=write_po returned no file")
        return 1
    print(f"verdict={decision.verdict} artifact={path} total={total:.2f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m domains.buyer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rank = sub.add_parser("rank", help="rank vendors by list landed cost")
    p_rank.add_argument("--spec", required=True)

    p_draft = sub.add_parser("draft", help="draft a local counter (not sent)")
    p_draft.add_argument("--spec", required=True)

    p_po = sub.add_parser("po", help="write a local PO markdown if approved")
    p_po.add_argument("--spec", required=True)
    p_po.add_argument("--approve", action="store_true")
    p_po.add_argument("--cap-usd", type=float, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "rank":
            return cmd_rank(args.spec)
        if args.cmd == "draft":
            return cmd_draft(args.spec)
        if args.cmd == "po":
            return cmd_po(args.spec, args.approve, args.cap_usd)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
