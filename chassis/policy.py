from __future__ import annotations

from dataclasses import dataclass

from chassis.goal import Goal, Tier

ALLOWLIST = frozenset({"operator@local", "channel:physical-agents"})

BLOCKED_DEST_TOKENS = (
    "911",
    "nifc",
    "usfs",
    "calfire",
    "cal fire",
    "oes",
    "duty desk",
    "duty-officer",
)

BLOCKED_ACTIONS = frozenset(
    {
        "page_agency",
        "book_live_freight",
        "charge_payment",
        "place_trade",
        "actuate",
    }
)

APPROVAL_ACTIONS = frozenset(
    {
        "sms_external",
        "email_external",
        "voice_external",
        "send_po",
        "spend",
        "add_notify_target",
        "weaken_policy",
        "create_bot",
    }
)


@dataclass
class Decision:
    verdict: str  # ALLOW | BLOCK | ESCALATE
    rule: str
    note: str

    @property
    def ok(self) -> bool:
        return self.verdict == "ALLOW"


class PolicyEngine:
    """Keep this aligned with POLICY.md."""

    def check(
        self,
        goal: Goal,
        action: str,
        destination: str | None = None,
    ) -> Decision:
        dest = (destination or "").strip().lower()
        action_l = action.strip().lower()

        if action_l in BLOCKED_ACTIONS:
            return Decision("BLOCK", "Blocked actions", f"{action} is never allowed")

        if dest and any(tok in dest for tok in BLOCKED_DEST_TOKENS):
            return Decision("BLOCK", "Notify allowlist", f"blocked destination: {destination}")

        if action_l in APPROVAL_ACTIONS and not goal.approved:
            return Decision("ESCALATE", "Require Paul", f"{action} needs an explicit yes")

        if destination and dest not in {d.lower() for d in ALLOWLIST} and dest not in {
            n.lower() for n in goal.notify
        }:
            # operator may put extra names on the goal; still no agency tokens
            if dest not in {n.lower() for n in goal.notify}:
                return Decision("BLOCK", "Notify allowlist", f"{destination} not allowlisted")

        if goal.tier == Tier.ACT_UNDER_CAP:
            if action_l in {"book_synthetic", "write_po", "write_alert", "write_schedule", "write_assignment"}:
                if action_l == "book_synthetic" and goal.cap_usd_per_mi is None:
                    return Decision("ESCALATE", "Caps", "book_synthetic requires cap_usd_per_mi")
                if action_l == "write_po" and not goal.approved:
                    return Decision("ESCALATE", "Caps", "write_po requires approved=true")
            else:
                return Decision("ESCALATE", "Autonomy tiers", "act_under_cap does not cover this action")

        if goal.tier == Tier.OBSERVE and action_l not in {"read", "compute"}:
            return Decision("ESCALATE", "Autonomy tiers", "observe cannot draft or write")

        return Decision("ALLOW", "Always allowed", f"{action} permitted at tier {goal.tier.value}")
