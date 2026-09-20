from __future__ import annotations

from typing import Any

from chassis.audit import RunLog, append_audit
from chassis.channels import Channel
from chassis.goal import Goal
from chassis.policy import PolicyEngine
from chassis.tools import Tool, ToolResult


class Agent:
    def __init__(self, domain: str, policy: PolicyEngine | None = None):
        self.domain = domain
        self.policy = policy or PolicyEngine()
        self.tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def act(
        self,
        goal: Goal,
        action: str,
        tool_name: str | None = None,
        destination: str | None = None,
        channel: Channel | None = None,
        tool_kwargs: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> tuple[Any, ToolResult | None]:
        decision = self.policy.check(goal, action, destination)
        artifact = None
        result = None
        if decision.ok and tool_name:
            tool = self.tools[tool_name]
            result = tool.run(**(tool_kwargs or {}))
            artifact = tool_name
        if decision.ok and channel and destination and message is not None:
            channel.send(destination, message)
            artifact = destination
        append_audit(
            RunLog(
                goal_id=goal.id,
                domain=self.domain,
                action=action,
                verdict=decision.verdict,
                note=decision.note,
                artifact=artifact,
                extra={"tool_ok": None if result is None else result.ok},
            )
        )
        return decision, result
