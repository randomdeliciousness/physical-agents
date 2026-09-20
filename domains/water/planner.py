"""3-night irrigation plan and local schedule file. Human executes valves."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from domains.water.water_balance import (
    SKIP_INCHES,
    Carry,
    MoistureRow,
    WeatherRow,
    apply_skip_precip,
    decide_reason,
    historical_carry,
    moisture_for_field,
    rain_on,
    step_et,
    weather_by_date,
)


@dataclass(frozen=True)
class Night:
    date: date
    action: str
    deficit_in: float
    et_in: float
    forecast_rain_in: float
    threshold: float
    moisture_frac: float | None
    reason: str


@dataclass(frozen=True)
class Plan:
    field_id: str
    as_of: date
    tonight: str
    nights: tuple[Night, ...]
    skip_inches: float = SKIP_INCHES
    actuate: bool = False


def _parse_as_of(as_of: date | str) -> date:
    if isinstance(as_of, date):
        return as_of
    return date.fromisoformat(as_of)


def plan_nights(
    field_id: str,
    as_of: date | str,
    n: int = 3,
    moisture_rows: list[MoistureRow] | None = None,
    weather_rows: list[WeatherRow] | None = None,
) -> Plan:
    day0 = _parse_as_of(as_of)
    if n < 1:
        raise ValueError("n must be >= 1")
    all_moisture = moisture_for_field(field_id, moisture_rows)
    moisture = [r for r in all_moisture if r.date <= day0]
    if not moisture:
        raise ValueError(f"no moisture on or before {day0.isoformat()} for {field_id}")
    weather = weather_by_date(field_id, weather_rows)
    by_date = {r.date: r for r in moisture}
    carry: Carry = historical_carry(field_id, day0, all_moisture, weather_rows)
    last_et = carry.et_in
    last_threshold = carry.threshold
    deficit = carry.deficit
    nights: list[Night] = []
    for i in range(n):
        day = day0 + timedelta(days=i)
        row = by_date.get(day)
        if row is not None:
            et_in = row.et_in
            threshold = row.threshold_frac
            moisture_frac: float | None = row.moisture_frac
        else:
            et_in = last_et
            threshold = last_threshold
            moisture_frac = None
        last_et, last_threshold = et_in, threshold
        rain = rain_on(weather, day)
        deficit_after_et = step_et(deficit, et_in)
        action, reason = decide_reason(deficit_after_et, threshold, rain, SKIP_INCHES)
        nights.append(
            Night(
                date=day,
                action=action,
                deficit_in=deficit_after_et,
                et_in=et_in,
                forecast_rain_in=rain,
                threshold=threshold,
                moisture_frac=moisture_frac,
                reason=reason,
            )
        )
        if action == "run":
            deficit = 0.0
        else:
            deficit = apply_skip_precip(deficit_after_et, rain)
    return Plan(
        field_id=field_id,
        as_of=day0,
        tonight=nights[0].action,
        nights=tuple(nights),
        skip_inches=SKIP_INCHES,
        actuate=False,
    )


def schedule_path(field_id: str, as_of: date, dest: Path) -> Path:
    return dest / f"schedule_{field_id}_{as_of.isoformat()}.json"


def _round(value: float) -> float:
    return round(value, 4)


def schedule_payload(plan: Plan) -> dict[str, object]:
    nights: list[dict[str, object]] = []
    for night in plan.nights:
        nights.append(
            {
                "date": night.date.isoformat(),
                "action": night.action,
                "deficit_in": _round(night.deficit_in),
                "et_in": _round(night.et_in),
                "forecast_rain_in": _round(night.forecast_rain_in),
                "threshold": _round(night.threshold),
                "moisture_frac": None
                if night.moisture_frac is None
                else _round(night.moisture_frac),
                "reason": night.reason,
            }
        )
    return {
        "field_id": plan.field_id,
        "as_of": plan.as_of.isoformat(),
        "tonight": plan.tonight,
        "actuate": False,
        "skip_inches": _round(plan.skip_inches),
        "nights": nights,
    }


def render_message(plan: Plan) -> str:
    tonight = plan.nights[0]
    lines = [
        f"Water Pulse — {plan.field_id} as of {plan.as_of.isoformat()}",
        f"Tonight: {plan.tonight.upper()}",
        f"Deficit {tonight.deficit_in:.2f} in, forecast rain {tonight.forecast_rain_in:.2f} in, "
        f"threshold {tonight.threshold:.2f} in.",
        "Human executes valves. No actuator.",
        "",
        "3-night plan:",
    ]
    for night in plan.nights:
        moisture = "n/a" if night.moisture_frac is None else f"{night.moisture_frac:.2f}"
        lines.append(
            f"- {night.date.isoformat()} {night.action}  deficit={night.deficit_in:.2f}in  "
            f"rain={night.forecast_rain_in:.2f}in  moisture={moisture}  {night.reason}"
        )
    lines.append("")
    return "\n".join(lines)


def write_schedule(plan: Plan, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    path = schedule_path(plan.field_id, plan.as_of, dest)
    payload = schedule_payload(plan)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
