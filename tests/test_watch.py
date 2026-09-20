from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chassis.goal import Goal
from chassis.policy import PolicyEngine
from domains.watch.adapters import (
    Day,
    FixtureAdapter,
    Hotspot,
    PublicHotspotAdapter,
    PublicWeatherAdapter,
    Sourced,
)
from domains.watch.brief import render_brief, write_alert, write_brief
from domains.watch.rules import evaluate, haversine_km, hotspot_distance, load_rules
from domains.watch.__main__ import main

WATCH_PY = Path(__file__).resolve().parents[1] / "domains" / "watch"
FORBIDDEN = ("containment", "casualt", "evacuat", "acreage", "acres")


def _day(**kwargs: object) -> Day:
    fields: dict[str, object] = {
        "key": "x",
        "day": "2026-09-08",
        "wind_mph": Sourced(31.0, "fixture-hot"),
        "rh_pct": Sourced(11.0, "fixture-hot"),
        "precip_next_24h_in": Sourced(0.0, "fixture-hot"),
        "hotspots": [
            Hotspot(id="hs-1", lat=37.18, lon=-121.62, km=14.0, source="fixture-hotspot")
        ],
        "incidents": [],
        "source": "fixture-hot",
        "hotspot_feed_source": "fixture",
    }
    fields.update(kwargs)
    return Day(
        key=str(fields["key"]),
        day=str(fields["day"]),
        wind_mph=fields["wind_mph"],  # type: ignore[arg-type]
        rh_pct=fields["rh_pct"],  # type: ignore[arg-type]
        precip_next_24h_in=fields["precip_next_24h_in"],  # type: ignore[arg-type]
        hotspots=list(fields["hotspots"]),  # type: ignore[arg-type]
        incidents=list(fields["incidents"]),  # type: ignore[arg-type]
        source=str(fields["source"]),
        hotspot_feed_source=str(fields["hotspot_feed_source"]),
    )


class RulesTests(unittest.TestCase):
    def test_yaml_thresholds(self) -> None:
        rules = load_rules()
        self.assertEqual(rules.aoi.name, "Santa Clara County demo")
        names = [c.name for c in rules.clauses]
        self.assertEqual(
            names,
            ["hotspot_within_km", "rh_pct_lt", "wind_mph_gt", "precip_next_24h_in_lt"],
        )
        by_name = {c.name: c.threshold for c in rules.clauses}
        self.assertEqual(by_name["hotspot_within_km"], 25)
        self.assertEqual(by_name["rh_pct_lt"], 15)
        self.assertEqual(by_name["wind_mph_gt"], 25)
        self.assertEqual(by_name["precip_next_24h_in_lt"], 0.05)
        self.assertIn("nws_or_fixture", rules.sources_required)
        self.assertIn("Do not page agencies", rules.disclaimer)

    def test_calm_does_not_fire(self) -> None:
        ev = evaluate(load_rules(), FixtureAdapter().load_day("calm"))
        self.assertFalse(ev.fire)
        self.assertEqual(ev.missing_sources, ())
        self.assertFalse(any(c.fired and c.name == "wind_mph_gt" for c in ev.clauses))

    def test_hot_fires_all_of(self) -> None:
        ev = evaluate(load_rules(), FixtureAdapter().load_day("hot"))
        self.assertTrue(ev.fire)
        self.assertEqual(ev.missing_sources, ())
        self.assertEqual([c.name for c in ev.clauses if c.fired], [c.name for c in ev.clauses])
        self.assertEqual(len(ev.clauses), 4)

    def test_unknown_source_does_not_alert(self) -> None:
        day = _day(
            wind_mph=Sourced(31.0, "unknown"),
            rh_pct=Sourced(11.0, "unknown"),
            precip_next_24h_in=Sourced(0.0, "unknown"),
            source="unknown",
            hotspot_feed_source="unknown",
        )
        ev = evaluate(load_rules(), day)
        self.assertFalse(ev.fire)
        self.assertTrue(ev.missing_sources)

    def test_stub_adapters_fail_closed(self) -> None:
        rules = load_rules()
        weather = PublicWeatherAdapter().fetch(rules.aoi)
        spots, feed = PublicHotspotAdapter().fetch(rules.aoi)
        self.assertEqual(weather.source, "unknown")
        self.assertFalse(weather.wind_mph.known)
        self.assertEqual(spots, [])
        self.assertEqual(feed, "unknown")
        day = Day(
            key="stub",
            day="2026-09-08",
            wind_mph=weather.wind_mph,
            rh_pct=weather.rh_pct,
            precip_next_24h_in=weather.precip_next_24h_in,
            hotspots=spots,
            incidents=[],
            source=weather.source,
            hotspot_feed_source=feed,
        )
        self.assertFalse(evaluate(rules, day).fire)

    def test_fixture_km_kept(self) -> None:
        rules = load_rules()
        hs = Hotspot(id="hs-1", lat=37.18, lon=-121.62, km=14.0, source="fixture-hotspot")
        dist = hotspot_distance(hs, rules.aoi)
        self.assertEqual(dist.value, 14.0)
        self.assertEqual(dist.source, "fixture-hotspot")

    def test_missing_km_uses_haversine(self) -> None:
        rules = load_rules()
        hs = Hotspot(id="hs-1", lat=37.18, lon=-121.62, km=None, source="fixture-hotspot")
        dist = hotspot_distance(hs, rules.aoi)
        expected = haversine_km(rules.aoi.lat, rules.aoi.lon, 37.18, -121.62)
        self.assertEqual(dist.source, "haversine-aoi")
        self.assertAlmostEqual(dist.value or 0.0, expected, places=6)
        ev = evaluate(rules, _day(hotspots=[hs]))
        self.assertTrue(ev.fire)


class BriefTests(unittest.TestCase):
    def test_brief_has_disclaimer_and_sources(self) -> None:
        rules = load_rules()
        day = FixtureAdapter().load_day("hot")
        ev = evaluate(rules, day)
        body = render_brief(rules, day, ev)
        self.assertIn("Fusion of public or fixture feeds", body)
        self.assertIn("Not a replacement for NOAA/USFS", body)
        self.assertIn("source: fixture-hot", body)
        self.assertIn("source: fixture-hotspot", body)
        self.assertIn("Do not page agencies", body)
        self.assertIn("ALERT", body)
        lowered = body.lower()
        for token in FORBIDDEN:
            self.assertNotIn(token, lowered)

    def test_calm_brief_silent(self) -> None:
        rules = load_rules()
        day = FixtureAdapter().load_day("calm")
        body = render_brief(rules, day, evaluate(rules, day))
        self.assertIn("SILENT", body)
        self.assertIn("Hotspots: none", body)
        lowered = body.lower()
        for token in FORBIDDEN:
            self.assertNotIn(token, lowered)

    def test_write_alert_only_when_firing(self) -> None:
        rules = load_rules()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            calm = FixtureAdapter().load_day("calm")
            self.assertIsNone(
                write_alert(
                    rules,
                    calm,
                    evaluate(rules, calm),
                    destination="operator@local",
                    dest=dest,
                )
            )
            self.assertEqual(list(dest.glob("alert.json")), [])
            hot = FixtureAdapter().load_day("hot")
            path = write_alert(
                rules,
                hot,
                evaluate(rules, hot),
                destination="operator@local",
                dest=dest,
            )
            self.assertIsNotNone(path)
            assert path is not None
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["destination"], "operator@local")
            self.assertEqual(len(payload["rules_fired"]), 4)
            blob = json.dumps(payload).lower()
            for token in FORBIDDEN:
                self.assertNotIn(token, blob)


class PolicyTests(unittest.TestCase):
    def test_nifc_blocked_random_blocked_allowlist_ok(self) -> None:
        engine = PolicyEngine()
        goal = Goal(id="w1", domain="watch", text="alert")
        self.assertEqual(
            engine.check(goal, "write_alert", destination="nifc@example.gov").verdict,
            "BLOCK",
        )
        self.assertEqual(
            engine.check(goal, "write_alert", destination="random@example.com").verdict,
            "BLOCK",
        )
        self.assertEqual(
            engine.check(goal, "write_alert", destination="operator@local").verdict,
            "ALLOW",
        )

    def test_no_mailer_or_live_fetch(self) -> None:
        text = "\n".join(p.read_text(encoding="utf-8") for p in WATCH_PY.glob("*.py"))
        self.assertNotIn("smtplib", text)
        self.assertNotIn("twilio", text)
        self.assertNotIn("urllib.request", text)
        self.assertNotRegex(text, r"(?m)^\s*import requests\b")
        self.assertNotIn("goal.notify.append", text)
        self.assertNotIn("goal.notify =", text)


class CliTests(unittest.TestCase):
    def test_cli_hot_writes_brief_and_alert(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.watch.__main__.OUT", dest):
                code = main(["brief", "--replay", "hot"])
            self.assertEqual(code, 0)
            self.assertTrue((dest / "watch_brief.md").exists())
            self.assertTrue((dest / "alert.json").exists())
            self.assertTrue((dest / "operator@local.txt").exists())
            brief = (dest / "watch_brief.md").read_text(encoding="utf-8")
            self.assertIn("NOAA/USFS", brief)
            out = buf.getvalue()
            self.assertIn("ALLOW", out)
            self.assertIn("operator@local", out)

    def test_cli_calm_writes_brief_no_alert(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.watch.__main__.OUT", dest):
                code = main(["brief", "--replay", "calm"])
            self.assertEqual(code, 0)
            self.assertTrue((dest / "watch_brief.md").exists())
            self.assertFalse((dest / "alert.json").exists())
            self.assertFalse((dest / "operator@local.txt").exists())
            self.assertIn("alert=none", buf.getvalue())
            self.assertIn("SILENT", (dest / "watch_brief.md").read_text(encoding="utf-8"))

    def test_cli_nifc_blocked_no_alert(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.watch.__main__.OUT", dest):
                code = main(["brief", "--replay", "hot", "--dest", "nifc@example.gov"])
            self.assertEqual(code, 1)
            self.assertTrue((dest / "watch_brief.md").exists())
            self.assertFalse((dest / "alert.json").exists())
            self.assertEqual(list(dest.glob("nifc*")), [])
            self.assertIn("BLOCK", buf.getvalue())

    def test_cli_random_dest_blocked(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.watch.__main__.OUT", dest):
                code = main(["brief", "--replay", "hot", "--dest", "random@example.com"])
            self.assertEqual(code, 1)
            self.assertFalse((dest / "alert.json").exists())
            self.assertIn("BLOCK", buf.getvalue())

    def test_write_brief_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            path = write_brief("hello", dest)
            self.assertEqual(path.read_text(encoding="utf-8"), "hello")


if __name__ == "__main__":
    unittest.main()
