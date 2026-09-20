from __future__ import annotations

import argparse
from pathlib import Path

from chassis.agent import Agent
from chassis.audit import DEFAULT_LOG
from chassis.channels import FileChannel
from chassis.goal import Goal, Tier
from chassis.tools import FunctionTool

OUT = Path(__file__).resolve().parents[1] / "demos" / "out"


def main() -> None:
    parser = argparse.ArgumentParser(description="Chassis smoke demo")
    parser.add_argument("--goal", default="ping")
    args = parser.parse_args()

    goal = Goal(id="echo-1", domain="chassis", text=args.goal, tier=Tier.RECOMMEND)
    agent = Agent("chassis")
    agent.register(FunctionTool("echo", lambda text: f"echo:{text}"))

    decision, result = agent.act(
        goal,
        action="compute",
        tool_name="echo",
        tool_kwargs={"text": args.goal},
        destination="operator@local",
        channel=FileChannel(OUT),
        message=f"echo demo received: {args.goal}",
    )
    print(f"verdict={decision.verdict} result={None if result is None else result.data}")
    print(DEFAULT_LOG.read_text(encoding="utf-8").strip().splitlines()[-1])


if __name__ == "__main__":
    main()
