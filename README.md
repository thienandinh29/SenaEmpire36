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

Run these in three separate terminals from the repository root. The worker is
required: the API only saves uploads and queues topics; it does not generate lessons.
Pass `--local-uploads` to both the API and worker to enable consented demo PDFs
using private workspace storage (the flag is not persisted across restarts).

```powershell
apps/api/.venv/Scripts/python scripts/run_live.py --service api --local-uploads
apps/api/.venv/Scripts/python scripts/run_live.py --service worker --local-uploads
apps/api/.venv/Scripts/python scripts/run_live.py --service web
```

Open http://localhost:3000 or http://127.0.0.1:3000 and accept the demo data notice
before uploading. PDF/DOCX files must be at most 20 MB. Scanned PDFs need OCR
before upload; the reader currently extracts existing text only.
