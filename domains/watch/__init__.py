"""Watch Officer — fuse fixture feeds, fire YAML rules, brief allowlist only."""

from domains.watch.adapters import (
    Day,
    FixtureAdapter,
    Hotspot,
    PublicHotspotAdapter,
    PublicWeatherAdapter,
    Sourced,
)
from domains.watch.brief import alert_payload, render_brief, write_alert, write_brief
from domains.watch.rules import Evaluation, Rules, evaluate, load_rules

__all__ = [
    "Day",
    "Evaluation",
    "FixtureAdapter",
    "Hotspot",
    "PublicHotspotAdapter",
    "PublicWeatherAdapter",
    "Rules",
    "Sourced",
    "alert_payload",
    "evaluate",
    "load_rules",
    "render_brief",
    "write_alert",
    "write_brief",
]
