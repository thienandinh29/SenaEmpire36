# SenaEmpire36

NodeTrail: an AI tutor for any subject (mascot: Sena the monkey), built for a 24-hour team competition.

- Rules and working agreement: `CLAUDE.md`
- 24-hour team plan (lanes, contracts, timeline): `TEAM.md`
- Per-person start guides: `team/P1.md` to `team/P5.md`
- What the product does: `SPEC.md`; where things are: `MAP.md`

Setup: copy `.env.example` to `.env` and fill it in by hand (never commit it). Copy `CLAUDE.local.md.example` to `CLAUDE.local.md` and set your lane number.

All teams use one PostgreSQL database through `DATABASE_URL` in the root `.env`.
The web reads/writes this data through the API. Use the common launcher for API,
worker and web; see [shared database setup](docker/DATABASE.md).

```powershell
apps/api/.venv/Scripts/python scripts/run_live.py --service check
```
