from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG = Path(__file__).resolve().parents[1] / "data" / "audit.jsonl"


@dataclass
class RunLog:
    goal_id: str
    domain: str
    action: str
    verdict: str
    note: str
    artifact: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def append_audit(row: RunLog, path: Path | None = None) -> Path:
    log_path = path or DEFAULT_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(row), default=str) + "\n")
    return log_path
