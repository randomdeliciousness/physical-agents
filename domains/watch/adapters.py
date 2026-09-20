"""Watch feed adapters. Fixture now; public stubs return unknown and do not network."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REPLAY_PATH = ROOT / "data" / "fixtures" / "watch_replay.json"


@dataclass(frozen=True)
class Sourced:
    value: float | None
    source: str

    @property
    def known(self) -> bool:
        return self.value is not None and self.source.lower() != "unknown"


@dataclass(frozen=True)
class Hotspot:
    id: str
    lat: float | None
    lon: float | None
    km: float | None
    source: str


@dataclass
class Day:
    key: str
    day: str
    wind_mph: Sourced
    rh_pct: Sourced
    precip_next_24h_in: Sourced
    hotspots: list[Hotspot]
    incidents: list[dict[str, Any]]
    source: str
    hotspot_feed_source: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WeatherObs:
    wind_mph: Sourced
    rh_pct: Sourced
    precip_next_24h_in: Sourced
    source: str


def _sourced_number(row: dict[str, Any], key: str, source: str) -> Sourced:
    if key not in row or row[key] is None:
        return Sourced(None, "unknown")
    try:
        return Sourced(float(row[key]), source)
    except (TypeError, ValueError):
        return Sourced(None, "unknown")


def _hotspot(raw: dict[str, Any]) -> Hotspot:
    km = raw.get("km")
    lat = raw.get("lat")
    lon = raw.get("lon")
    src = str(raw.get("source") or "unknown")
    return Hotspot(
        id=str(raw.get("id") or "unknown"),
        lat=None if lat is None else float(lat),
        lon=None if lon is None else float(lon),
        km=None if km is None else float(km),
        source=src,
    )


class FixtureAdapter:
    def __init__(self, path: Path | None = None):
        self.path = path or REPLAY_PATH

    def load_day(self, key: str) -> Day:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if key not in payload:
            raise KeyError(f"unknown replay {key!r}")
        row = payload[key]
        source = str(row.get("source") or "unknown")
        hotspots = [_hotspot(h) for h in (row.get("hotspots") or [])]
        incidents = [dict(item) for item in (row.get("incidents") or [])]
        return Day(
            key=key,
            day=str(row.get("day") or "unknown"),
            wind_mph=_sourced_number(row, "wind_mph", source),
            rh_pct=_sourced_number(row, "rh_pct", source),
            precip_next_24h_in=_sourced_number(row, "precip_next_24h_in", source),
            hotspots=hotspots,
            incidents=incidents,
            source=source,
            hotspot_feed_source="fixture",
        )


class PublicWeatherAdapter:
    """Stub. No network. Unknown values so rules fail closed."""

    def fetch(self, aoi: Any = None) -> WeatherObs:
        unk = Sourced(None, "unknown")
        return WeatherObs(unk, unk, unk, "unknown")


class PublicHotspotAdapter:
    """Stub. No network. Empty list, unknown feed source."""

    def fetch(self, aoi: Any = None) -> tuple[list[Hotspot], str]:
        return [], "unknown"
