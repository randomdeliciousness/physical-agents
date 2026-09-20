"""Lane eval: 10 fixture loads vs frozen oracle, T-07 draft only."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from domains.lane.exception import confirm_delivery, load_breadcrumbs, watch_draft
from domains.lane.matcher import get_load, load_loads, rank

ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "evals" / "lane_oracle.json"
BASELINE = 10.0


def _pct_err(value: float, oracle: float) -> float:
    if oracle == 0:
        return 0.0 if value == 0 else 100.0
    return abs(value - oracle) / abs(oracle) * 100.0


def freeze_oracle(path: Path | None = None) -> dict:
    rows: dict[str, dict] = {}
    for load in load_loads():
        best = rank(load)[0]
        rows[load["id"]] = {
            "truck_id": best.truck_id,
            "usd": round(best.usd, 6),
            "usd_per_mi": round(best.usd_per_mi, 8),
        }
    dest = path or ORACLE_PATH
    dest.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows


def main() -> int:
    if not ORACLE_PATH.exists():
        print("DOMAIN=lane PASS=0 METRIC=usd_per_mi_err VALUE=100 BASELINE=10 UNIT=pct")
        print(f"missing oracle {ORACLE_PATH}", file=sys.stderr)
        return 1
    oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
    crumbs = load_breadcrumbs()
    loads = load_loads()
    errs: list[float] = []
    for load in loads:
        quotes = rank(load)
        if not quotes:
            print("DOMAIN=lane PASS=0 METRIC=usd_per_mi_err VALUE=100 BASELINE=10 UNIT=pct")
            print(f"no quotes for {load['id']}", file=sys.stderr)
            return 1
        best = quotes[0]
        o = oracle[load["id"]]
        errs.append(_pct_err(best.usd_per_mi, float(o["usd_per_mi"])))
    value = max(errs) if errs else 100.0

    late_ok = watch_draft(get_load("L-07"), "T-07", crumbs) is not None
    on_time_ok = all(
        watch_draft(get_load(lid), tid, crumbs) is None
        for tid, lid in (("T-01", "L-01"), ("T-02", "L-02"), ("T-08", "L-01"))
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        one = confirm_delivery("L-07", "driver", root)
        two = confirm_delivery("L-07", "receiver", root)
        confirm_ok = one["status"] != "delivered" and two["status"] == "delivered"

    passed = value <= BASELINE and late_ok and on_time_ok and confirm_ok and len(loads) == 10
    flag = 1 if passed else 0
    print(
        f"DOMAIN=lane PASS={flag} METRIC=usd_per_mi_err VALUE={value:.4f} "
        f"BASELINE={BASELINE:.0f} UNIT=pct"
    )
    if not passed:
        print(
            f"late_ok={late_ok} on_time_ok={on_time_ok} confirm_ok={confirm_ok} loads={len(loads)}",
            file=sys.stderr,
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
