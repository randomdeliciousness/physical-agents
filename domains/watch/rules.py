"""YAML rules loader and all-of fire-weather engine. No spread model."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from domains.watch.adapters import Day, Hotspot, Sourced

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "data" / "fixtures" / "watch_rules.yml"


@dataclass(frozen=True)
class AOI:
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Clause:
    name: str
    threshold: float


@dataclass(frozen=True)
class Rules:
    aoi: AOI
    clauses: tuple[Clause, ...]
    sources_required: tuple[str, ...]
    disclaimer: str


@dataclass(frozen=True)
class ClauseResult:
    name: str
    fired: bool
    observed: Sourced
    threshold: float
    operator: str


@dataclass(frozen=True)
class Evaluation:
    fire: bool
    clauses: tuple[ClauseResult, ...]
    missing_sources: tuple[str, ...]


def _parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _parse_map(items: list[tuple[int, str]], i: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while i < len(items):
        ind, line = items[i]
        if ind < indent:
            break
        if ind > indent:
            raise ValueError(f"unexpected indent at {line!r}")
        if line.startswith("- "):
            raise ValueError(f"expected mapping, got list item {line!r}")
        key, sep, rest = line.partition(":")
        if not sep:
            raise ValueError(f"expected key: value at {line!r}")
        key = key.strip()
        rest = rest.strip()
        i += 1
        if rest:
            result[key] = _parse_scalar(rest)
            continue
        if i >= len(items) or items[i][0] <= indent:
            result[key] = {}
            continue
        child_indent = items[i][0]
        if items[i][1].startswith("- "):
            value, i = _parse_list(items, i, child_indent)
        else:
            value, i = _parse_map(items, i, child_indent)
        result[key] = value
    return result, i


def _parse_list(items: list[tuple[int, str]], i: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while i < len(items):
        ind, line = items[i]
        if ind < indent:
            break
        if ind > indent:
            raise ValueError(f"unexpected indent in list at {line!r}")
        if not line.startswith("- "):
            break
        payload = line[2:].strip()
        i += 1
        if not payload:
            if i < len(items) and items[i][0] > indent:
                child_indent = items[i][0]
                if items[i][1].startswith("- "):
                    nested, i = _parse_list(items, i, child_indent)
                else:
                    nested, i = _parse_map(items, i, child_indent)
                result.append(nested)
            else:
                result.append({})
            continue
        if ":" in payload:
            k, _, v = payload.partition(":")
            k, v = k.strip(), v.strip()
            if v:
                result.append({k: _parse_scalar(v)})
            elif i < len(items) and items[i][0] > indent:
                child_indent = items[i][0]
                if items[i][1].startswith("- "):
                    nested, i = _parse_list(items, i, child_indent)
                else:
                    nested, i = _parse_map(items, i, child_indent)
                result.append({k: nested})
            else:
                result.append({k: {}})
        else:
            result.append(_parse_scalar(payload))
    return result, i


def parse_simple_yaml(text: str) -> dict[str, Any]:
    items: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = raw.split("#", 1)[0].rstrip()
        if not stripped.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        items.append((indent, stripped.strip()))
    if not items:
        return {}
    mapping, idx = _parse_map(items, 0, items[0][0])
    if idx != len(items):
        raise ValueError("yaml subset: trailing content")
    return mapping


def load_rules(path: Path | None = None) -> Rules:
    dest = path or RULES_PATH
    raw = parse_simple_yaml(dest.read_text(encoding="utf-8"))
    aoi_raw = raw["aoi"]
    clauses: list[Clause] = []
    for item in raw["alert_all_of"]:
        if not isinstance(item, dict) or len(item) != 1:
            raise ValueError(f"alert_all_of item must be a single-key mapping: {item!r}")
        name, threshold = next(iter(item.items()))
        clauses.append(Clause(name=str(name), threshold=float(threshold)))
    sources = tuple(str(s) for s in raw["sources_required"])
    disclaimer = str(raw["copy"]["disclaimer"])
    return Rules(
        aoi=AOI(name=str(aoi_raw["name"]), lat=float(aoi_raw["lat"]), lon=float(aoi_raw["lon"])),
        clauses=tuple(clauses),
        sources_required=sources,
        disclaimer=disclaimer,
    )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def hotspot_distance(hotspot: Hotspot, aoi: AOI) -> Sourced:
    if hotspot.km is not None:
        src = hotspot.source if hotspot.source else "unknown"
        return Sourced(hotspot.km, src)
    if hotspot.lat is None or hotspot.lon is None:
        return Sourced(None, "unknown")
    return Sourced(haversine_km(aoi.lat, aoi.lon, hotspot.lat, hotspot.lon), "haversine-aoi")


def _source_satisfied(req: str, day: Day) -> bool:
    if req == "nws_or_fixture":
        s = day.source.lower()
        return s != "unknown" and ("fixture" in s or "nws" in s)
    if req == "hotspot_or_fixture":
        s = day.hotspot_feed_source.lower()
        return s != "unknown" and ("fixture" in s or "hotspot" in s)
    return False


def _nearest_hotspot(day: Day, aoi: AOI) -> Sourced:
    best: Sourced | None = None
    for hs in day.hotspots:
        dist = hotspot_distance(hs, aoi)
        if not dist.known:
            continue
        if best is None or (best.value is not None and dist.value is not None and dist.value < best.value):
            best = dist
    if best is None:
        return Sourced(None, "unknown" if not day.hotspots else day.hotspots[0].source)
    return best


def _operator(name: str) -> str:
    if name.endswith("_within_km"):
        return "<="
    if name.endswith("_lt"):
        return "<"
    if name.endswith("_gt"):
        return ">"
    return "?"


def _clause_observed(clause: Clause, day: Day, aoi: AOI) -> Sourced:
    if clause.name == "hotspot_within_km":
        return _nearest_hotspot(day, aoi)
    if clause.name.startswith("rh_pct"):
        return day.rh_pct
    if clause.name.startswith("wind_mph"):
        return day.wind_mph
    if clause.name.startswith("precip_next_24h_in"):
        return day.precip_next_24h_in
    return Sourced(None, "unknown")


def _clause_fires(clause: Clause, observed: Sourced) -> bool:
    if not observed.known or observed.value is None:
        return False
    op = _operator(clause.name)
    value = observed.value
    if op == "<":
        return value < clause.threshold
    if op == ">":
        return value > clause.threshold
    if op == "<=":
        return value <= clause.threshold
    return False


def evaluate(rules: Rules, day: Day) -> Evaluation:
    missing = tuple(req for req in rules.sources_required if not _source_satisfied(req, day))
    clauses: list[ClauseResult] = []
    for clause in rules.clauses:
        observed = _clause_observed(clause, day, rules.aoi)
        fired = _clause_fires(clause, observed)
        clauses.append(
            ClauseResult(
                name=clause.name,
                fired=fired,
                observed=observed,
                threshold=clause.threshold,
                operator=_operator(clause.name),
            )
        )
    fire = (not missing) and all(c.fired for c in clauses) and bool(clauses)
    return Evaluation(fire=fire, clauses=tuple(clauses), missing_sources=missing)
