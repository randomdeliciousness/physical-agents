"""Buyer eval: cheapest list-landed vendor wins; unapproved PO writes nothing."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from domains.buyer.landed_cost import load_specs, rank
from domains.buyer.po import po_path, write_po

BASELINE = 1.0


def main() -> int:
    specs = load_specs()
    hits = 0
    for spec in specs:
        quotes = rank(spec)
        if not quotes:
            print("DOMAIN=buyer PASS=0 METRIC=rank_acc VALUE=0.0 BASELINE=1.0 UNIT=frac")
            print(f"no eligible vendors for {spec['id']}", file=sys.stderr)
            return 1
        cheapest = min(q.landed for q in quotes)
        if quotes[0].landed == cheapest:
            hits += 1
    n = len(specs)
    value = hits / n if n else 0.0

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        spec = specs[0]
        quotes = rank(spec)
        blocked = write_po(spec, quotes[0], approved=False, dest=root, cap_usd=None)
        leftover = list(root.glob("po_*.md"))
        written = write_po(spec, quotes[0], approved=True, dest=root, cap_usd=None)
        approved_ok = written is not None and written.exists()
        unapproved_ok = blocked is None and leftover == []
        expected = po_path(str(spec["id"]), root)
        approved_ok = approved_ok and written == expected

    passed = value >= BASELINE and n == 15 and unapproved_ok and approved_ok
    flag = 1 if passed else 0
    print(
        f"DOMAIN=buyer PASS={flag} METRIC=rank_acc VALUE={value:.1f} "
        f"BASELINE={BASELINE:.1f} UNIT=frac"
    )
    if not passed:
        print(
            f"n={n} hits={hits} unapproved_ok={unapproved_ok} approved_ok={approved_ok}",
            file=sys.stderr,
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
