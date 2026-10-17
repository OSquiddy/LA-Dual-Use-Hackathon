# HandoffProof

An emergency isn't handled until someone accepts responsibility.

- **What we're building and why:** [HandoffProof — Build Plan & Judge Defense.md](HandoffProof%20—%20Build%20Plan%20&%20Judge%20Defense.md)
- **Who builds what, in parallel:** [HandoffProof — Parallel Build Plan (3 Computers).md](HandoffProof%20—%20Parallel%20Build%20Plan%20(3%20Computers).md)

## Who owns what

Only edit files you own. Shared files (`backend/app/contracts.py`, `backend/app/models.py`, `.env.example`, `frontend/src/types.ts`) change only after a message in the team chat.

| Computer | Owns |
| --- | --- |
| **PC-A — Voice** | `backend/app/voice/`, `agents/`, `docs/pitch/` |
| **PC-B — Engine** | `backend/app/engine/`, `backend/app/api/`, `backend/app/models.py`, `backend/seeds/`, `backend/tests/` |
| **PC-C — Dashboard** | `frontend/` |

Every placeholder is tagged with its task id from the parallel plan. Search for `TODO(B4)`, `TODO(A8)`, etc. to find your next job.

## Run it

**Backend** (Python 3.11+), from `backend/`:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env           # defaults work: CALL_MODE=simulate, TIMING_PROFILE=demo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pytest                               # contract + smoke tests
```

Load the storm-night scenario: `curl -X POST localhost:8000/api/demo/reset -H "content-type: application/json" -d '{"seed":"storm_night"}'`. API docs are at http://localhost:8000/docs.

**Dashboard** (Node 18+), from `frontend/`:

```bash
npm install
cp .env.example .env.local           # VITE_API=fixture works with no backend
npm run dev                          # http://localhost:5173 · press T for the twist panel
```

Set `VITE_API=live` to poll the backend. `VITE_BACKEND_URL` can point at PC-B's machine on the same Wi-Fi (e.g. `http://192.168.1.20:8000`).

**Retell webhooks** need a public URL: `cloudflared tunnel --url http://localhost:8000` (or `ngrok http 8000`). Put the URL in `PUBLIC_BASE_URL` and set the agent webhook to `<url>/retell/webhook`.

## How the pieces join

```
Retell intake call ──► POST /retell/webhook ──► ingest_report(ReportIn) ──► linker · debts · risk
                          (voice/, A)              (engine/, B)                    │
                                                                                   ▼
Retell callback ◄── request_callback(...) ◄──── ladder.tick() every 2 s ◄── incidents in SQLite
      │                 (voice/, A)              (engine/, B)                      │
      └──► POST /retell/webhook ──► record_callback_outcome(CallbackOutcome)       ▼
                                                              GET /api/state ──► dashboard (frontend/, C)
```

`CALL_MODE=simulate` replaces Retell with `voice/simulator.py`, so B and C never wait on phones.

## What works today (scaffold)

- Seeds load through the same `ingest_report` path a live call uses. Locations are geocoded from `seeds/gazetteer.json`, and every incident gets a department and a `no_owner` debt.
- Accept and close (human-only) work; simulated callbacks are recorded and show up in "why it's here".
- The dashboard renders fixtures or live data: department queues, supervisor top 10, incident drawer, twist panel.
- `tests/test_contracts.py` fails if the frontend fixtures stop matching the backend's response models.

Not built yet (placeholders): linking (B4: `test_storm_night_links_into_one_incident` is the target), risk formula (B5), the ladder steps (B7–B10), the department-silence detector (B12), twists (B13–B15), and Retell signature check and live payload mapping (A3, A9).
