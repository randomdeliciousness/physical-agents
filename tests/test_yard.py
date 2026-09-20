from __future__ import annotations

import io
import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

from chassis.agent import Agent
from chassis.goal import Goal
from chassis.policy import PolicyEngine
from chassis.tools import FunctionTool
from domains.yard.assign import (
    assign_wave,
    first_door_free,
    greedy_assign,
    load_appointments,
    load_doors,
    total_dwell,
    write_assignment,
)
from domains.yard.dwell import (
    DWELL_CAP_MIN,
    confirm_checkin,
    draft_overrun,
    event_dwells,
    overruns,
)
from domains.yard.__main__ import main

YARD_PY = Path(__file__).resolve().parents[1] / "domains" / "yard"
FORBIDDEN = (
    "pymodbus",
    "gpio",
    "serial",
    "smtplib",
    "twilio",
    "urllib.request",
    "http.client",
)

GREEDY_DOORS = {
    "A-01": "D-01",
    "A-02": "D-02",
    "A-03": "D-05",
    "A-04": "D-03",
    "A-05": "D-04",
    "A-06": "D-06",
    "A-07": "D-09",
    "A-08": "D-07",
    "A-09": "D-08",
    "A-10": "D-12",
}


def _wave():
    return [a for a in load_appointments() if a.arrive >= "06:00"]


class AssignTests(unittest.TestCase):
    def test_greedy_door_map(self) -> None:
        rows = greedy_assign(_wave(), load_doors())
        got = {r.appointment_id: r.door_id for r in rows}
        self.assertEqual(got, GREEDY_DOORS)
        self.assertEqual(total_dwell(rows), 470)
        self.assertTrue(all(r.wait_min == 0 for r in rows))
        a09 = next(r for r in rows if r.appointment_id == "A-09")
        a10 = next(r for r in rows if r.appointment_id == "A-10")
        self.assertEqual(a09.door_id, "D-08")
        self.assertEqual(a10.door_id, "D-12")

    def test_reefer_only_on_reefer_doors(self) -> None:
        doors = {d.id: d for d in load_doors()}
        rows = greedy_assign(_wave(), load_doors())
        for row in rows:
            self.assertEqual(doors[row.door_id].type, row.type)
            if row.type == "reefer":
                self.assertIn(row.door_id, {"D-05", "D-06", "D-12"})

    def test_no_double_book(self) -> None:
        rows = greedy_assign(_wave(), load_doors())
        by_door: dict[str, list] = defaultdict(list)
        for row in rows:
            by_door[row.door_id].append(row)
        for door_rows in by_door.values():
            door_rows.sort(key=lambda r: r.start_min)
            for prev, cur in zip(door_rows, door_rows[1:]):
                self.assertGreaterEqual(cur.start_min, prev.end_min)

    def test_first_door_free_queues_on_first_matching(self) -> None:
        rows = first_door_free(_wave(), load_doors())
        self.assertEqual(total_dwell(rows), 1090)
        self.assertGreater(total_dwell(rows), 470)
        dry = [r for r in rows if r.type == "dry"]
        reefer = [r for r in rows if r.type == "reefer"]
        self.assertTrue(all(r.door_id == "D-01" for r in dry))
        self.assertTrue(all(r.door_id == "D-05" for r in reefer))
        self.assertEqual(next(r for r in rows if r.appointment_id == "A-07").door_id, "D-09")

    def test_write_assignment_actuate_false(self) -> None:
        plan = assign_wave("06:00")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            path = write_assignment(plan, dest)
            self.assertEqual(path.name, "assignment_0600.json")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertIs(payload["actuate"], False)
            self.assertEqual(payload["total_dwell_min"], 470)
            self.assertEqual(payload["wave"], "06:00")
            self.assertEqual(len(payload["assignments"]), 10)

    def test_unknown_wave(self) -> None:
        with self.assertRaises(ValueError):
            assign_wave("23:00")


class DwellTests(unittest.TestCase):
    def test_event_dwells_and_one_overrun(self) -> None:
        self.assertEqual(DWELL_CAP_MIN, 90)
        rows = event_dwells()
        by_id = {r.appointment_id: r for r in rows}
        self.assertEqual(by_id["A-01"].dwell_min, 48)
        self.assertEqual(by_id["A-03"].dwell_min, 125)
        self.assertEqual(by_id["A-07"].dwell_min, 33)
        self.assertEqual([r.appointment_id for r in overruns(rows)], ["A-03"])
        draft = draft_overrun(rows)
        self.assertIsNotNone(draft)
        assert draft is not None
        self.assertIn("A-03", draft)
        self.assertNotIn("A-01", draft)
        self.assertNotIn("A-07", draft)
        self.assertEqual(draft.count("Appointment "), 1)
        self.assertIn("DOCK DRAFT (not sent)", draft)
        self.assertIn("operator@local", draft)

    def test_dual_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            one = confirm_checkin("A-03", "driver", root)
            self.assertEqual(one["status"], "recommend")
            self.assertTrue(one["driver_confirmed"])
            self.assertFalse(one["dock_confirmed"])
            two = confirm_checkin("A-03", "dock", root)
            self.assertEqual(two["status"], "complete")
            rec = json.loads((root / "yard_run_A-03.json").read_text(encoding="utf-8"))
            self.assertEqual(rec["status"], "complete")

    def test_bad_party(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                confirm_checkin("A-03", "receiver", Path(tmp))


class PolicyTests(unittest.TestCase):
    def test_actuate_blocked_write_assignment_allowed(self) -> None:
        engine = PolicyEngine()
        goal = Goal(id="y1", domain="yard", text="assign")
        self.assertEqual(engine.check(goal, "actuate").verdict, "BLOCK")
        self.assertEqual(engine.check(goal, "write_assignment").verdict, "ALLOW")

    def test_blocked_actuate_does_not_write(self) -> None:
        ran = {"n": 0}

        def boom() -> str:
            ran["n"] += 1
            return "nope"

        goal = Goal(id="x", domain="yard", text="no")
        agent = Agent("yard")
        agent.register(FunctionTool("door", boom))
        decision, result = agent.act(goal, action="actuate", tool_name="door")
        self.assertEqual(decision.verdict, "BLOCK")
        self.assertIsNone(result)
        self.assertEqual(ran["n"], 0)

    def test_no_wms_or_hardware_client(self) -> None:
        text = "\n".join(p.read_text(encoding="utf-8") for p in YARD_PY.glob("*.py"))
        lowered = text.lower()
        for token in FORBIDDEN:
            self.assertNotIn(token, lowered)
        self.assertNotRegex(text, r"(?m)^\s*import requests\b")
        self.assertNotIn("goal.notify.append", text)
        self.assertNotIn("goal.notify =", text)
        self.assertFalse((YARD_PY / "actuator.py").exists())
        self.assertFalse((YARD_PY / "wms.py").exists())


class CliTests(unittest.TestCase):
    def test_cli_assign_wave(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.yard.__main__.OUT", dest):
                code = main(["assign", "--wave", "06:00"])
            self.assertEqual(code, 0)
            out = buf.getvalue()
            self.assertIn("ALLOW", out)
            self.assertIn("D-05", out)
            self.assertIn("D-06", out)
            self.assertIn("D-12", out)
            self.assertIn("A-09", out)
            path = dest / "assignment_0600.json"
            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertIs(payload["actuate"], False)
            reefers = {
                row["appointment_id"]: row["door_id"]
                for row in payload["assignments"]
                if row["type"] == "reefer"
            }
            self.assertEqual(reefers, {"A-03": "D-05", "A-06": "D-06", "A-10": "D-12"})

    def test_cli_dwell_one_draft(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.yard.__main__.OUT", dest):
                code = main(["dwell"])
            self.assertEqual(code, 0)
            out = buf.getvalue()
            self.assertIn("A-03 dwell=125 min overrun", out)
            self.assertIn("A-01 dwell=48 min quiet", out)
            self.assertIn("A-07 dwell=33 min quiet", out)
            self.assertIn("overruns=1", out)
            note = (dest / "operator@local.txt").read_text(encoding="utf-8")
            self.assertIn("A-03", note)
            self.assertNotIn("A-01", note)
            self.assertNotIn("A-07", note)

    def test_cli_confirm_dual(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.yard.__main__.OUT", dest):
                code1 = main(["confirm", "--appointment", "A-03", "--party", "driver"])
                code2 = main(["confirm", "--appointment", "A-03", "--party", "dock"])
            self.assertEqual(code1, 0)
            self.assertEqual(code2, 0)
            rec = json.loads((dest / "yard_run_A-03.json").read_text(encoding="utf-8"))
            self.assertEqual(rec["status"], "complete")
            self.assertIn("status=recommend", buf.getvalue())
            self.assertIn("status=complete", buf.getvalue())

    def test_cli_unknown_wave(self) -> None:
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stderr", err), patch("domains.yard.__main__.OUT", dest):
                code = main(["assign", "--wave", "23:00"])
            self.assertEqual(code, 2)
            self.assertEqual(list(dest.glob("assignment_*.json")), [])

    def test_cli_unknown_appointment(self) -> None:
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stderr", err), patch("domains.yard.__main__.OUT", dest):
                code = main(["confirm", "--appointment", "A-99", "--party", "driver"])
            self.assertEqual(code, 2)
            self.assertEqual(list(dest.glob("yard_run_*.json")), [])


if __name__ == "__main__":
    unittest.main()
