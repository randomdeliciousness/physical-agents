"""Soil-moisture + forecast balance in inches. No actuator, no network."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data" / "fixtures"

# Skip irrigation when forecast rain is at least this many inches.
SKIP_INCHES = 0.25


@dataclass(frozen=True)
class MoistureRow:
    date: date
    field_id: str
    moisture_frac: float
    et_in: float
    threshold_frac: float


@dataclass(frozen=True)
class WeatherRow:
    date: date
    field_id: str
    forecast_rain_in: float
    scenario: str


@dataclass(frozen=True)
class Carry:
    """Deficit at the start of `as_of`, after historical days only (no run refill)."""

    deficit: float
    et_in: float
    threshold: float
    moisture_frac: float | None


def load_moisture(path: Path | None = None) -> list[MoistureRow]:
    src = path or (FIXTURES / "water_moisture.csv")
    rows: list[MoistureRow] = []
    with src.open(encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            rows.append(
                MoistureRow(
                    date=date.fromisoformat(raw["date"]),
                    field_id=raw["field_id"],
                    moisture_frac=float(raw["moisture_frac"]),
                    et_in=float(raw["et_in"]),
                    threshold_frac=float(raw["threshold_frac"]),
                )
            )
    rows.sort(key=lambda r: (r.field_id, r.date))
    return rows


def load_weather(path: Path | None = None) -> list[WeatherRow]:
    src = path or (FIXTURES / "water_weather.csv")
    rows: list[WeatherRow] = []
    with src.open(encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            rows.append(
                WeatherRow(
                    date=date.fromisoformat(raw["date"]),
                    field_id=raw["field_id"],
                    forecast_rain_in=float(raw["forecast_rain_in"]),
                    scenario=raw["scenario"],
                )
            )
    rows.sort(key=lambda r: (r.field_id, r.date))
    return rows


def moisture_for_field(field_id: str, rows: list[MoistureRow] | None = None) -> list[MoistureRow]:
    src = rows if rows is not None else load_moisture()
    found = [r for r in src if r.field_id == field_id]
    if not found:
        raise KeyError(f"unknown field: {field_id}")
    return found


def weather_by_date(field_id: str, rows: list[WeatherRow] | None = None) -> dict[date, WeatherRow]:
    src = rows if rows is not None else load_weather()
    return {r.date: r for r in src if r.field_id == field_id}


def rain_on(weather: dict[date, WeatherRow], day: date) -> float:
    row = weather.get(day)
    return 0.0 if row is None else row.forecast_rain_in


def step_et(deficit: float, et_in: float) -> float:
    return deficit + et_in


def apply_skip_precip(deficit: float, precip_in: float) -> float:
    return max(0.0, deficit - precip_in)


def should_run(
    deficit: float,
    threshold: float,
    forecast_rain_in: float,
    skip_inches: float = SKIP_INCHES,
) -> bool:
    return deficit > threshold and forecast_rain_in < skip_inches


def decide_reason(
    deficit: float,
    threshold: float,
    forecast_rain_in: float,
    skip_inches: float = SKIP_INCHES,
) -> tuple[str, str]:
    if should_run(deficit, threshold, forecast_rain_in, skip_inches):
        return (
            "run",
            f"deficit {deficit:.2f} > threshold {threshold:.2f} and "
            f"forecast rain {forecast_rain_in:.2f} < skip {skip_inches:.2f}",
        )
    if forecast_rain_in >= skip_inches:
        return (
            "skip",
            f"forecast rain {forecast_rain_in:.2f} >= skip {skip_inches:.2f}",
        )
    return (
        "skip",
        f"deficit {deficit:.2f} <= threshold {threshold:.2f}",
    )


def _inputs_on(
    day: date,
    moisture: dict[date, MoistureRow],
    last_et: float,
    last_threshold: float,
    last_moisture: float | None,
) -> tuple[float, float, float | None]:
    row = moisture.get(day)
    if row is None:
        return last_et, last_threshold, None
    return row.et_in, row.threshold_frac, row.moisture_frac


def historical_carry(
    field_id: str,
    as_of: date,
    moisture_rows: list[MoistureRow] | None = None,
    weather_rows: list[WeatherRow] | None = None,
) -> Carry:
    """Roll deficit from the first moisture date through the day before `as_of`.

    Historical nights never refill. Rain still lands and cuts deficit.
    Moisture after `as_of` is ignored.
    """
    rows = [r for r in moisture_for_field(field_id, moisture_rows) if r.date <= as_of]
    if not rows:
        raise ValueError(f"no moisture on or before {as_of.isoformat()} for {field_id}")
    weather = weather_by_date(field_id, weather_rows)
    by_date = {r.date: r for r in rows}
    first = rows[0].date
    last_et = rows[0].et_in
    last_threshold = rows[0].threshold_frac
    last_moisture: float | None = rows[0].moisture_frac
    deficit = 0.0
    day = first
    while day < as_of:
        et_in, threshold, moisture_frac = _inputs_on(
            day, by_date, last_et, last_threshold, last_moisture
        )
        last_et, last_threshold = et_in, threshold
        if moisture_frac is not None:
            last_moisture = moisture_frac
        deficit = apply_skip_precip(step_et(deficit, et_in), rain_on(weather, day))
        day += timedelta(days=1)
    as_of_row = by_date.get(as_of)
    if as_of_row is not None:
        last_et = as_of_row.et_in
        last_threshold = as_of_row.threshold_frac
        last_moisture = as_of_row.moisture_frac
    return Carry(
        deficit=deficit,
        et_in=last_et,
        threshold=last_threshold,
        moisture_frac=last_moisture,
    )
