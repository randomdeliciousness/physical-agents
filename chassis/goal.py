from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Tier(str, Enum):
    OBSERVE = "observe"
    RECOMMEND = "recommend"
    ACT_UNDER_CAP = "act_under_cap"
    ESCALATE = "escalate"


@dataclass
class Goal:
    id: str
    domain: str
    text: str
    tier: Tier = Tier.RECOMMEND
    cap_usd: float | None = None
    cap_usd_per_mi: float | None = None
    approved: bool = False
    notify: list[str] = field(default_factory=lambda: ["operator@local"])
    extra: dict[str, Any] = field(default_factory=dict)
