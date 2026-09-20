# Physical-efficiency agent portfolio

Drop this folder into Grok Build (`cd physical-agents && grok`).
Paste files in `bots/` into Grok Bot settings. Execute tickets in `stages/` one at a time.

## Stack

| Layer | Tool |
|---|---|
| Code, tests, domain models | Grok Build (plan mode → implement → eval) |
| Tickets, routines, approvals, channel | Grok Bot roster in `bots/` |
| Autonomy | `POLICY.md` + `chassis/policy.py` |

## First hour

1. Create a Grok Bot channel. Add the five bots using `bots/*.md` (skip `00-roster.md` as a bot; it is the map).
2. Tell **Floor PM**: `Open stage 00-chassis. Ticket is stages/00-chassis.md.`
3. In this directory: `grok` → plan mode → paste the Build prompt in that ticket.
4. Run `python -m pytest tests/ -q` after chassis work. Then freeze chassis and open stage 01.

## Stage order

0. Chassis  
1. Lane Cost & Exception  
2. Landed-Cost Buyer  
3. Watch Officer  
4. Water Pulse  
5. Yard & Dock Pulse  
6. Wrap  

Do not parallelize products. Parallelize fixtures inside one product with Build `/workflows` if needed.

## Sanity check (works before any domain)

```bash
python -m pytest tests/ -q
python -m chassis.demo_echo --goal "ping" 
```

## What is already here vs what Build still writes

Already here: policy, bot copy, tickets, fixtures, chassis interfaces + tests, demo scripts.

Build still writes: domain packages under `domains/*/`, eval harnesses that import those packages, any live adapters named in a later ticket.
