"""Lane cost model: miles + grade → energy → USD. No network."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

CRUISE_MPH = 55.0
LATE_GRACE_MIN = 15
DIESEL_USD_PER_GAL = 4.25
KWH_USD = 0.16
GVW_LB = 80000.0
EMPTY_FACTOR = 0.85
WEIGHT_COEFF = 0.20
EARTH_MI = 3958.8
AT_DEST_MI = 25.0

GRADE_FACTOR = {
    "flat": 1.00,
    "desert": 1.08,
    "mixed": 1.12,
    "mountain": 1.28,
}


@dataclass(frozen=True)
class Quote:
    truck_id: str
    load_id: str
    deadhead_mi: float
    loaded_mi: float
    energy_amount: float
    energy_unit: str
    drive_h: float
    usd: float
    usd_per_mi: float
    fuel: str


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_MI * math.asin(min(1.0, math.sqrt(a)))


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def grade_factor(band: str) -> float:
    try:
        return GRADE_FACTOR[band]
    except KeyError as exc:
        raise ValueError(f"unknown grade_band: {band}") from exc


def weight_factor(weight_lb: float) -> float:
    return 1.0 + WEIGHT_COEFF * (weight_lb / GVW_LB)


def quote_truck(truck: Mapping[str, Any], load: Mapping[str, Any]) -> Quote:
    loaded_mi = float(load["miles_hint"])
    if loaded_mi <= 0:
        raise ValueError("miles_hint must be positive")
    deadhead_mi = haversine_mi(
        float(truck["lat"]),
        float(truck["lon"]),
        float(load["olat"]),
        float(load["olon"]),
    )
    grade = grade_factor(str(load["grade_band"]))
    wfac = weight_factor(float(load["weight_lb"]))
    fuel = str(truck["fuel"])
    if fuel == "battery":
        kpm = truck.get("kwh_per_mi")
        if kpm is None:
            raise ValueError(f"{truck['id']} battery truck missing kwh_per_mi")
        kpm_f = float(kpm)
        energy = (deadhead_mi * kpm_f) * grade * EMPTY_FACTOR + (loaded_mi * kpm_f) * grade * wfac
        unit = "kWh"
        energy_usd = energy * KWH_USD
    else:
        mpg = truck.get("mpg")
        if mpg is None:
            raise ValueError(f"{truck['id']} diesel truck missing mpg")
        mpg_f = float(mpg)
        energy = (deadhead_mi / mpg_f) * grade * EMPTY_FACTOR + (loaded_mi / mpg_f) * grade * wfac
        unit = "gal"
        energy_usd = energy * DIESEL_USD_PER_GAL
    drive_h = (deadhead_mi + loaded_mi) / CRUISE_MPH
    driver_usd = drive_h * float(truck["rate_driver_per_h"])
    usd = energy_usd + driver_usd + float(load["tolls_usd"])
    return Quote(
        truck_id=str(truck["id"]),
        load_id=str(load["id"]),
        deadhead_mi=deadhead_mi,
        loaded_mi=loaded_mi,
        energy_amount=energy,
        energy_unit=unit,
        drive_h=drive_h,
        usd=usd,
        usd_per_mi=usd / loaded_mi,
        fuel=fuel,
    )
