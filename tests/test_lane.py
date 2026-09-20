from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chassis.policy import PolicyEngine
from chassis.goal import Goal, Tier
from domains.lane.cost_model import GRADE_FACTOR, quote_truck
from domains.lane.exception import confirm_delivery, load_breadcrumbs, watch_draft
from domains.lane.matcher import get_load, get_truck, load_trucks, rank
from domains.lane.__main__ import main


def _base_truck(**over: object) -> dict:
    row = {
        "id": "T-X",
        "equip": "dry53",
        "lat": 34.0,
        "lon": -117.0,
        "city": "X",
        "hos_h": 1.0,
        "mpg": 6.0,
        "kwh_per_mi": None,
        "fuel": "diesel",
        "rate_driver_per_h": 40,
    }
    row.update(over)
    return row


def _base_load(**over: object) -> dict:
    row = {
        "id": "L-X",
        "equip": "dry53",
        "origin": "A",
        "dest": "B",
        "olat": 34.0,
        "olon": -117.0,
        "dlat": 33.0,
        "dlon": -112.0,
        "weight_lb": 40000,
        "pickup": "2026-09-17T06:00:00-07:00",
        "delivery": "2026-09-18T08:00:00-07:00",
        "tolls_usd": 10,
        "grade_band": "flat",
        "miles_hint": 100,
    }
    row.update(over)
    return row


class CostModelTests(unittest.TestCase):
    def test_mountain_uses_more_energy_than_flat(self) -> None:
        truck = _base_truck()
        flat = quote_truck(truck, _base_load(grade_band="flat"))
        mountain = quote_truck(truck, _base_load(grade_band="mountain"))
        self.assertGreater(mountain.energy_amount, flat.energy_amount)
        self.assertEqual(flat.energy_unit, "gal")
        self.assertAlmostEqual(
            mountain.energy_amount / flat.energy_amount,
            GRADE_FACTOR["mountain"] / GRADE_FACTOR["flat"],
            places=6,
        )

    def test_battery_quotes_kwh(self) -> None:
        truck = _base_truck(fuel="battery", mpg=None, kwh_per_mi=2.0)
        q = quote_truck(truck, _base_load())
        self.assertEqual(q.energy_unit, "kWh")
        self.assertGreater(q.usd_per_mi, 0)


class MatcherTests(unittest.TestCase):
    def test_l07_includes_t07_and_ignores_hos(self) -> None:
        load = get_load("L-07")
        trucks = load_trucks()
        quotes = rank(load, trucks)
        ids = [q.truck_id for q in quotes]
        self.assertIn("T-07", ids)
        self.assertNotIn("T-03", ids)  # reefer
        self.assertNotIn("T-06", ids)  # flatbed
        t07 = get_truck("T-07", trucks)
        self.assertLess(t07["hos_h"], 25)
        self.assertTrue(any(q.drive_h > t07["hos_h"] for q in quotes if q.truck_id == "T-07"))

    def test_wrong_equip_excluded(self) -> None:
        load = get_load("L-05")  # flatbed
        ids = {q.truck_id for q in rank(load)}
        self.assertTrue(ids <= {"T-06", "T-19"})


class ExceptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.crumbs = load_breadcrumbs()

    def test_t07_l07_late_to_pickup_not_hidden_by_dallas(self) -> None:
        draft = watch_draft(get_load("L-07"), "T-07", self.crumbs)
        self.assertIsNotNone(draft)
        assert draft is not None
        self.assertIn("late to pickup", draft)
        self.assertNotIn("late to delivery", draft)
        self.assertEqual(draft.count("SMS DRAFT"), 1)

    def test_on_time_trucks_no_draft(self) -> None:
        pairs = (("T-01", "L-01"), ("T-02", "L-02"), ("T-08", "L-01"))
        for truck_id, load_id in pairs:
            with self.subTest(truck=truck_id, load=load_id):
                self.assertIsNone(watch_draft(get_load(load_id), truck_id, self.crumbs))

    def test_dual_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            one = confirm_delivery("L-07", "driver", root)
            self.assertNotEqual(one["status"], "delivered")
            self.assertTrue(one["driver_confirmed"])
            two = confirm_delivery("L-07", "receiver", root)
            self.assertEqual(two["status"], "delivered")
            rec = json.loads((root / "lane_run_L-07.json").read_text(encoding="utf-8"))
            self.assertEqual(rec["status"], "delivered")


class BookPolicyTests(unittest.TestCase):
    def test_book_without_cap_escalates(self) -> None:
        engine = PolicyEngine()
        goal = Goal(id="b1", domain="lane", text="book", tier=Tier.ACT_UNDER_CAP)
        d = engine.check(goal, "book_synthetic")
        self.assertEqual(d.verdict, "ESCALATE")

    def test_cli_book_without_cap_writes_no_file(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["book", "--load", "L-07", "--truck", "T-07"])
        self.assertEqual(code, 1)
        self.assertIn("ESCALATE", buf.getvalue())
        self.assertFalse((Path("demos/out") / "book_L-07_T-07.json").exists())

    def test_live_freight_unused(self) -> None:
        engine = PolicyEngine()
        goal = Goal(id="b2", domain="lane", text="nope")
        d = engine.check(goal, "book_live_freight")
        self.assertEqual(d.verdict, "BLOCK")


class CliTests(unittest.TestCase):
    def test_quote_l07_prints_ranked_trucks(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["quote", "--load", "L-07"])
        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIn("T-07", out)
        self.assertIn("usd_per_mi", out)
        self.assertIn("L-07", out)


if __name__ == "__main__":
    unittest.main()
