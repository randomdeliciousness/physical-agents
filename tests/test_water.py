from __future__ import annotations

import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from chassis.agent import Agent
from chassis.goal import Goal
from chassis.policy import PolicyEngine
from chassis.tools import FunctionTool
from domains.water.planner import plan_nights, render_message, write_schedule
from domains.water.water_balance import SKIP_INCHES, historical_carry, should_run
from domains.water.__main__ import main


WATER_PY = Path(__file__).resolve().parents[1] / "domains" / "water"
FORBIDDEN = (
    "pymodbus",
    "gpio",
    "serial",
    "smtplib",
    "twilio",
    "urllib.request",
)


class BalanceTests(unittest.TestCase):
    def test_skip_inches_constant(self) -> None:
        self.assertEqual(SKIP_INCHES, 0.25)
        self.assertFalse(should_run(0.94, 0.18, 0.55))
        self.assertTrue(should_run(0.65, 0.18, 0.00))

    def test_wet_skips_dry_runs(self) -> None:
        wet = plan_nights("F-01", "2026-09-13")
        dry = plan_nights("F-01", "2026-09-14")
        self.assertEqual(wet.tonight, "skip")
        self.assertEqual(dry.tonight, "run")
        self.assertNotEqual(wet.tonight, dry.tonight)

    def test_three_night_wet(self) -> None:
        plan = plan_nights("F-01", date(2026, 9, 13))
        self.assertEqual(len(plan.nights), 3)
        self.assertEqual([n.action for n in plan.nights], ["skip", "run", "run"])
        self.assertEqual([n.date.isoformat() for n in plan.nights], [
            "2026-09-13",
            "2026-09-14",
            "2026-09-15",
        ])
        self.assertAlmostEqual(plan.nights[0].deficit_in, 0.94, places=4)
        self.assertAlmostEqual(plan.nights[1].deficit_in, 0.64, places=4)
        self.assertAlmostEqual(plan.nights[2].deficit_in, 0.25, places=4)
        self.assertEqual(plan.nights[0].moisture_frac, 0.17)
        self.assertIsNone(plan.nights[1].moisture_frac)
        self.assertFalse(plan.actuate)

    def test_three_night_dry(self) -> None:
        plan = plan_nights("F-01", "2026-09-14")
        self.assertEqual([n.action for n in plan.nights], ["run", "run", "run"])
        self.assertEqual([n.date.isoformat() for n in plan.nights], [
            "2026-09-14",
            "2026-09-15",
            "2026-09-16",
        ])
        self.assertAlmostEqual(plan.nights[0].deficit_in, 0.65, places=4)
        self.assertAlmostEqual(plan.nights[1].et_in, 0.26, places=4)
        self.assertAlmostEqual(plan.nights[2].forecast_rain_in, 0.10, places=4)

    def test_no_future_moisture_leak(self) -> None:
        wet = plan_nights("F-01", "2026-09-13")
        self.assertAlmostEqual(wet.nights[1].et_in, 0.25, places=4)
        dry = plan_nights("F-01", "2026-09-14")
        self.assertAlmostEqual(dry.nights[0].et_in, 0.26, places=4)

    def test_history_does_not_refill(self) -> None:
        carry = historical_carry("F-01", date(2026, 9, 13))
        self.assertAlmostEqual(carry.deficit, 0.69, places=4)
        carry_dry = historical_carry("F-01", date(2026, 9, 14))
        self.assertAlmostEqual(carry_dry.deficit, 0.39, places=4)

    def test_unknown_field(self) -> None:
        with self.assertRaises(KeyError):
            plan_nights("F-99", "2026-09-13")

    def test_date_before_series(self) -> None:
        with self.assertRaises(ValueError):
            plan_nights("F-01", "2026-09-01")


class ScheduleTests(unittest.TestCase):
    def test_write_schedule_actuate_false(self) -> None:
        plan = plan_nights("F-01", "2026-09-13")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            path = write_schedule(plan, dest)
            self.assertEqual(path.name, "schedule_F-01_2026-09-13.json")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["tonight"], "skip")
            self.assertIs(payload["actuate"], False)
            self.assertEqual(payload["skip_inches"], 0.25)
            self.assertEqual(len(payload["nights"]), 3)

    def test_message_is_local_human_executes(self) -> None:
        body = render_message(plan_nights("F-01", "2026-09-14"))
        self.assertIn("Tonight: RUN", body)
        self.assertIn("Human executes valves", body)
        self.assertIn("No actuator", body)
        self.assertNotIn("opening valve", body.lower())


class PolicyTests(unittest.TestCase):
    def test_actuate_blocked_write_schedule_allowed(self) -> None:
        engine = PolicyEngine()
        goal = Goal(id="w1", domain="water", text="plan")
        self.assertEqual(engine.check(goal, "actuate").verdict, "BLOCK")
        self.assertEqual(engine.check(goal, "write_schedule").verdict, "ALLOW")

    def test_blocked_actuate_does_not_write(self) -> None:
        ran = {"n": 0}

        def boom() -> str:
            ran["n"] += 1
            return "nope"

        goal = Goal(id="x", domain="water", text="no")
        agent = Agent("water")
        agent.register(FunctionTool("valve", boom))
        decision, result = agent.act(goal, action="actuate", tool_name="valve")
        self.assertEqual(decision.verdict, "BLOCK")
        self.assertIsNone(result)
        self.assertEqual(ran["n"], 0)

    def test_no_actuator_client(self) -> None:
        text = "\n".join(p.read_text(encoding="utf-8") for p in WATER_PY.glob("*.py"))
        lowered = text.lower()
        for token in FORBIDDEN:
            self.assertNotIn(token, lowered)
        self.assertNotRegex(text, r"(?m)^\s*import requests\b")
        self.assertNotIn("goal.notify.append", text)
        self.assertNotIn("goal.notify =", text)
        self.assertFalse((WATER_PY / "actuator.py").exists())


class CliTests(unittest.TestCase):
    def test_cli_wet_skip(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.water.__main__.OUT", dest):
                code = main(["plan", "--date", "2026-09-13"])
            self.assertEqual(code, 0)
            out = buf.getvalue()
            self.assertIn("tonight=skip", out)
            self.assertIn("ALLOW", out)
            path = dest / "schedule_F-01_2026-09-13.json"
            self.assertTrue(path.exists())
            self.assertTrue((dest / "operator@local.txt").exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertIs(payload["actuate"], False)
            note = (dest / "operator@local.txt").read_text(encoding="utf-8")
            self.assertIn("Human executes valves", note)

    def test_cli_dry_run(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.water.__main__.OUT", dest):
                code = main(["plan", "--date", "2026-09-14"])
            self.assertEqual(code, 0)
            self.assertIn("tonight=run", buf.getvalue())
            self.assertTrue((dest / "schedule_F-01_2026-09-14.json").exists())

    def test_cli_unknown_field(self) -> None:
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stderr", err), patch("domains.water.__main__.OUT", dest):
                code = main(["plan", "--date", "2026-09-13", "--field", "F-99"])
            self.assertEqual(code, 2)
            self.assertEqual(list(dest.glob("schedule_*.json")), [])


if __name__ == "__main__":
    unittest.main()
