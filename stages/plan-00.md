# Plan 00 — Chassis gaps vs acceptance

Status: **implemented** (minimal `demo_echo` stdout + clean-checkout audit verify)

## Evidence gathered

- `AGENTS.md`, `POLICY.md`, `stages/00-chassis.md` read.
- `chassis/` modules inspected: `goal`, `policy`, `tools`, `channels`, `audit`, `agent`, `demo_echo`.
- `tests/test_chassis.py`: **10/10 OK** via `python -m unittest tests.test_chassis -q`.
- `python -m chassis.demo_echo --goal "ping"` exits 0; stdout: `verdict=ALLOW result=echo:ping`.
- `data/audit.jsonl` is written by `Agent.act` → `append_audit` (gitignored; created on first write).
- `python -m pytest` is unavailable in this environment (`No module named pytest`); unittest covers the same file.

## Acceptance box vs reality

| Acceptance item | Status | Notes |
|---|---|---|
| Goal, Policy, Tool, Channel, RunLog exist | **Done** (already checked) | Present under `chassis/`; do not rewrite. |
| `demo_echo` run succeeds on a clean checkout | **Mostly done; one eval gap** | CLI exists and runs. Audit line is written. Eval text also expects an **audit-style record on stdout**; current print is only `verdict=… result=…`. |
| Cap missing + `act_under_cap` → escalate, no tool side effect | **Behavior already met** | `test_act_under_cap_without_cap_escalates` passes. `Agent.act` skips tools when `decision.ok` is false. No failing test → no rewrite. |
| Blocked destination rejected | **Behavior already met** | `test_agency_destination_blocked` / `test_unknown_destination_blocked` pass. |
| Engineer does not start stage 01 | **Process** | Keep `domains/` untouched this session. |

Ticket guidance: *If tests already pass, add only what the ticket still marks open (demo_echo CLI if missing, audit file create).*

- **demo_echo CLI**: not missing.
- **audit file create**: already implemented in `chassis/audit.py` (`mkdir` + append). No new create path needed unless approval wants a tracked placeholder (not recommended; file is gitignored by design).

## Proposed edits after approval (minimal)

1. **`chassis/demo_echo.py` only** — print an audit-style record after `act` (fields aligned with `RunLog`: goal_id, domain, action, verdict, note, artifact, etc.), while keeping the existing audit append path.
2. **Verify clean-checkout audit create** — remove/rename local `data/audit.jsonl`, re-run demo, confirm file reappears with one JSON line. No module rewrite if that already works.
3. **Do not** rewrite `policy.py` / `agent.py` / other working modules unless a test fails.
4. **Do not** open `domains/` or stage 01.
5. Re-run `python -m unittest tests.test_chassis -q` (and `pytest` if installed) plus `python -m chassis.demo_echo --goal "ping"`.

## Out of scope

- Installing pytest (env note only).
- POLICY.md / `chassis/policy.py` changes (no policy gap found).
- New agent tests for escalate side effects (optional later; not required by “add only open items”).

## Approval ask

Approve the single `demo_echo.py` stdout change + clean-checkout audit verification, or say to mark acceptance closed with zero code changes.
