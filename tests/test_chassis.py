from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from chassis.agent import Agent
from chassis.channels import FileChannel
from chassis.goal import Goal, Tier
from chassis.policy import PolicyEngine
from chassis.tools import FunctionTool


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = PolicyEngine()

    def test_recommend_compute_allowed(self) -> None:
        goal = Goal(id="g1", domain="chassis", text="ping")
        d = self.engine.check(goal, "compute")
        self.assertEqual(d.verdict, "ALLOW")

    def test_agency_destination_blocked(self) -> None:
        goal = Goal(id="g2", domain="watch", text="alert")
        d = self.engine.check(goal, "write_alert", destination="nifc-duty@example.gov")
        self.assertEqual(d.verdict, "BLOCK")

    def test_unknown_destination_blocked(self) -> None:
        goal = Goal(id="g3", domain="watch", text="alert")
        d = self.engine.check(goal, "write_alert", destination="random@example.com")
        self.assertEqual(d.verdict, "BLOCK")

    def test_allowlist_destination_ok(self) -> None:
        goal = Goal(id="g4", domain="watch", text="alert")
        d = self.engine.check(goal, "write_alert", destination="operator@local")
        self.assertEqual(d.verdict, "ALLOW")

    def test_act_under_cap_without_cap_escalates(self) -> None:
        goal = Goal(id="g5", domain="lane", text="book", tier=Tier.ACT_UNDER_CAP)
        d = self.engine.check(goal, "book_synthetic")
        self.assertEqual(d.verdict, "ESCALATE")

    def test_po_without_approval_escalates(self) -> None:
        goal = Goal(id="g6", domain="buyer", text="po", tier=Tier.ACT_UNDER_CAP)
        d = self.engine.check(goal, "write_po")
        self.assertEqual(d.verdict, "ESCALATE")

    def test_external_sms_escalates(self) -> None:
        goal = Goal(id="g7", domain="lane", text="sms")
        d = self.engine.check(goal, "sms_external")
        self.assertEqual(d.verdict, "ESCALATE")

    def test_trade_blocked(self) -> None:
        goal = Goal(id="g8", domain="x", text="nope")
        d = self.engine.check(goal, "place_trade")
        self.assertEqual(d.verdict, "BLOCK")


class AgentTests(unittest.TestCase):
    def test_echo_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            goal = Goal(id="echo-t", domain="chassis", text="ping")
            agent = Agent("chassis")
            agent.register(FunctionTool("echo", lambda text: f"echo:{text}"))
            decision, result = agent.act(
                goal,
                action="compute",
                tool_name="echo",
                tool_kwargs={"text": "ping"},
                destination="operator@local",
                channel=FileChannel(out),
                message="hello",
            )
            self.assertEqual(decision.verdict, "ALLOW")
            assert result is not None
            self.assertEqual(result.data, "echo:ping")
            self.assertTrue((out / "operator@local.txt").exists())

    def test_blocked_action_does_not_run_tool(self) -> None:
        ran = {"n": 0}

        def boom() -> str:
            ran["n"] += 1
            return "nope"

        goal = Goal(id="x", domain="chassis", text="no")
        agent = Agent("chassis")
        agent.register(FunctionTool("boom", boom))
        decision, result = agent.act(goal, action="place_trade", tool_name="boom")
        self.assertEqual(decision.verdict, "BLOCK")
        self.assertIsNone(result)
        self.assertEqual(ran["n"], 0)


if __name__ == "__main__":
    unittest.main()
