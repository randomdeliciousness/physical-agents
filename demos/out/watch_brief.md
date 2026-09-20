# Watch Officer brief

Fusion of public or fixture feeds. Not a replacement for NOAA/USFS.

AOI: Santa Clara County demo (37.22, -121.75)
Replay: hot
Day: 2026-09-08

## Observations
- Wind: 31 mph (source: fixture-hot)
- RH: 11 % (source: fixture-hot)
- Precip next 24h: 0 in (source: fixture-hot)
- Hotspots:
  - hs-1: 14 km (source: fixture-hotspot)
- Incidents: none

## Rules (all_of)
- hotspot_within_km: 14 (source: fixture-hotspot) <= 25 → FIRED
- rh_pct_lt: 11 (source: fixture-hot) < 15 → FIRED
- wind_mph_gt: 31 (source: fixture-hot) > 25 → FIRED
- precip_next_24h_in_lt: 0 (source: fixture-hot) < 0.05 → FIRED

## Decision
ALERT (local file only). Do not page agencies.

Fusion of public or fixture feeds. Not an official forecast. Do not page agencies.
