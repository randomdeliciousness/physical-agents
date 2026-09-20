"""Local watch brief and alert.json. Quote sources only. Never invent incident fields."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from domains.watch.adapters import Day, Sourced
from domains.watch.rules import Evaluation, Rules, hotspot_distance

BRIEF_NAME = "watch_brief.md"
ALERT_NAME = "alert.json"

FORBIDDEN_COPY = ("containment", "casualt", "evacuat", "acreage", "acres")


def _fmt_num(sourced: Sourced, unit: str) -> str:
    if not sourced.known or sourced.value is None:
        return f"unknown (source: {sourced.source or 'unknown'})"
    value = sourced.value
    if float(value).is_integer():
        shown = str(int(value))
    else:
        shown = f"{value:g}"
    if unit:
        return f"{shown} {unit} (source: {sourced.source})"
    return f"{shown} (source: {sourced.source})"


def render_brief(rules: Rules, day: Day, ev: Evaluation) -> str:
    lines = [
        "# Watch Officer brief",
        "",
        "Fusion of public or fixture feeds. Not a replacement for NOAA/USFS.",
        "",
        f"AOI: {rules.aoi.name} ({rules.aoi.lat}, {rules.aoi.lon})",
        f"Replay: {day.key}",
        f"Day: {day.day}",
        "",
        "## Observations",
        f"- Wind: {_fmt_num(day.wind_mph, 'mph')}",
        f"- RH: {_fmt_num(day.rh_pct, '%')}",
        f"- Precip next 24h: {_fmt_num(day.precip_next_24h_in, 'in')}",
    ]
    if day.hotspots:
        lines.append("- Hotspots:")
        for hs in day.hotspots:
            dist = hotspot_distance(hs, rules.aoi)
            if dist.known and dist.value is not None:
                km_txt = f"{dist.value:g} km"
            else:
                km_txt = "unknown km"
            lines.append(f"  - {hs.id}: {km_txt} (source: {dist.source})")
    else:
        lines.append("- Hotspots: none")
    if day.incidents:
        quoted = json.dumps(day.incidents, default=str)
        lines.append(f"- Incidents (quoted, not completed): {quoted}")
    else:
        lines.append("- Incidents: none")
    lines.extend(["", "## Rules (all_of)"])
    if ev.missing_sources:
        lines.append("- Missing required sources: " + ", ".join(ev.missing_sources))
    for clause in ev.clauses:
        status = "FIRED" if clause.fired else "miss"
        obs = _fmt_num(clause.observed, "")
        lines.append(
            f"- {clause.name}: {obs} {clause.operator} {clause.threshold:g} → {status}"
        )
    lines.extend(["", "## Decision"])
    if ev.fire:
        lines.append("ALERT (local file only). Do not page agencies.")
    else:
        lines.append("SILENT — rules did not fire.")
    lines.extend(["", rules.disclaimer, ""])
    body = "\n".join(lines)
    lowered = body.lower()
    for token in FORBIDDEN_COPY:
        if token in lowered:
            raise ValueError(f"brief must not contain {token!r}")
    return body


def alert_payload(rules: Rules, day: Day, ev: Evaluation, destination: str) -> dict[str, Any]:
    fired = [c.name for c in ev.clauses if c.fired]
    hotspots = []
    for hs in day.hotspots:
        dist = hotspot_distance(hs, rules.aoi)
        hotspots.append({"id": hs.id, "km": dist.value, "source": dist.source})
    payload = {
        "aoi": rules.aoi.name,
        "day": day.day,
        "destination": destination,
        "rules_fired": fired,
        "wind_mph": {"value": day.wind_mph.value, "source": day.wind_mph.source},
        "rh_pct": {"value": day.rh_pct.value, "source": day.rh_pct.source},
        "precip_next_24h_in": {
            "value": day.precip_next_24h_in.value,
            "source": day.precip_next_24h_in.source,
        },
        "hotspots": hotspots,
        "disclaimer": rules.disclaimer,
    }
    blob = json.dumps(payload).lower()
    for token in FORBIDDEN_COPY:
        if token in blob:
            raise ValueError(f"alert must not contain {token!r}")
    return payload


def render_notify(payload: dict[str, Any]) -> str:
    fired = ", ".join(payload.get("rules_fired") or [])
    spots = payload.get("hotspots") or []
    spot_txt = (
        "; ".join(f"{s.get('id')} {s.get('km')} km (source: {s.get('source')})" for s in spots)
        or "none"
    )
    wind = payload["wind_mph"]
    rh = payload["rh_pct"]
    precip = payload["precip_next_24h_in"]
    return (
        "Watch alert (fixture fusion, not official).\n"
        f"AOI: {payload['aoi']}\n"
        f"Day: {payload['day']}\n"
        f"Wind {wind['value']} mph (source: {wind['source']}); "
        f"RH {rh['value']} % (source: {rh['source']}); "
        f"precip {precip['value']} in (source: {precip['source']})\n"
        f"Hotspots: {spot_txt}\n"
        f"Rules fired: {fired}\n"
        f"{payload['disclaimer']}\n"
    )


def write_brief(text: str, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / BRIEF_NAME
    path.write_text(text, encoding="utf-8")
    return path


def write_alert(
    rules: Rules,
    day: Day,
    ev: Evaluation,
    *,
    destination: str,
    dest: Path,
) -> Path | None:
    if not ev.fire:
        return None
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / ALERT_NAME
    payload = alert_payload(rules, day, ev, destination)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
