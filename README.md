# HandoffProof

**An incident isn't handled until someone accepts responsibility — and the evidence is still visible.**

HandoffProof is a **software-only AI-powered incident intelligence and accountability** hackathon prototype. It accepts fictional non-emergency resident reports through Retell AI, links related calls without discarding source evidence, tracks department handoffs and human acceptance, and uses consent-gated callbacks to collect updates. A human supervisor sees a ranked top 10 **plus persistent critical alerts** grounded in reported evidence.

**Scope / safety:** This is **not** an official City of Los Angeles service and is not connected to 911, municipal ticket systems, or any emergency dispatcher. It never claims safety, auto-closes cases, or calls anyone without explicit permission. **Wireless sensing / ESP32 / physical hardware is excluded** from this MVP; port/grid/defense-related handoffs are prospective software applications, not deployed integrations.

**Current scaffold vs revised plan:** The project already has running stubs, seed loader, simulated callbacks, API/UI fixture contracts and human Accept/Close. Linking (B4), new acknowledgment state, consent persistence/enforcement and a persistent critical-alert lane still require coordinated implementation. Do **not** treat the new plan as code already implemented.

- **What we're building and why:** [HandoffProof — Build Plan & Judge Defense.md](HandoffProof%20—%20Build%20Plan%20&%20Judge%20Defense.md)
- **Who builds what, in parallel:** [HandoffProof — Parallel Build Plan (3 Computers).md](HandoffProof%20—%20Parallel%20Build%20Plan%20(3%20Computers).md)

## Who owns what

Only edit files you own. Shared files (`backend/app/contracts.py`, `backend/app/models.py`, `.env.example`, `frontend/src/types.ts`) and any API changes need a team agreement **before edits**. Branches/PR review are preferred to direct edits on `main`.

| Computer | Owns |
| --- | --- |
| **PC-A — Voice** | `backend/app/voice/`, `agents/`, `docs/pitch/` |
| **PC-B — Engine** | `backend/app/engine/`, `backend/app/api/`, `backend/app/models.py`, `backend/seeds/`, `backend/tests/` |
| **PC-C — Dashboard** | `frontend/` |

Every placeholder is tagged with its original task ID (`TODO(B4)`, `TODO(A8)`, etc.). The revised plans keep **PC-A / PC-B / PC-C ownership and IDs** while adding consent, acknowledgment and safety acceptance tests. Use the plans as requirements and verify the current code separately.

## Run it

**Backend** (Python 3.11+), from `backend/`:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
test -f ../.env || cp ../.env.example ../.env  # local only; never overwrite configured secrets
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pytest                               # contract + smoke tests
```

Load the storm-night scenario: `curl -X POST localhost:8000/api/demo/reset -H "content-type: application/json" -d '{"seed":"storm_night"}'`. API docs are at http://localhost:8000/docs.

**Dashboard** (Node 18+), from `frontend/`:

```bash
npm install
test -f .env.local || cp .env.example .env.local    # set VITE_API=live for local integration
npm run dev                          # http://localhost:5173 · press T for the twist panel
npm run build                        # strict type-check + production build
npm run check:readiness              # renders the real dashboard against synthetic states
```

Full integration check (12 consent × outcome scenarios × 4 handoff stages): from `backend/`, run `HANDOFFPROOF_INTEGRATION_SNAPSHOTS=<dir> pytest tests/test_phase01_acceptance.py`, then from `frontend/` run `npm run check:phase01 -- <dir>`.

Set `VITE_API=live` to poll the backend. `VITE_BACKEND_URL` can point at PC-B's machine on the same Wi-Fi (e.g. `http://192.168.1.20:8000`).

**Retell:** Intake and Callback prompts and extraction fields are browser-tested. The webhook now verifies Retell's signature on the raw body and `callback_ok` is persisted and enforced, so no caller is called back without a clear yes. **Before exposing anything publicly:** tunnelling port 8000 also exposes `/api/*` (including `/api/demo/reset`), which has no authentication yet. Add a token or expose only `/retell/webhook` first. Keep `CALL_MODE=simulate` until then, and only call explicitly consenting test participants.

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

`CALL_MODE=simulate` replaces the outbound Retell API with `voice/simulator.py`; it does not establish real consent or verify live webhook signatures. B and C can develop against synthetic data while A implements validated voice integration.

## What works today

Per-task status lives in the [Parallel Build Plan](HandoffProof%20—%20Parallel%20Build%20Plan%20(3%20Computers).md) progress section.

- **Engine:** related reports link into one incident (≤300 m from its first report, ≤60 min, same hazard group, or same street when there's no exact spot). Every report stays its own row and the linked event says why. Duplicate webhooks are ingested once.
- **Risk is evidence-only:** hazard base, danger phrases the caller actually said, independent callers, and the latest worse/better answer. No-answer, missing consent and unaccepted time add nothing; they are debts.
- **Ladder:** nudge → default on-call owner from `seeds/oncall.json` (proposed, not accepted; a missing roster entry is flagged, never invented) → callback **only** to a caller with `callback_ok=true`, max 2 attempts. Acknowledge (receipt only) and Accept are separate human actions.
- **Critical alerts** (`critical_alerts[]`, uncapped): someone in danger, or a resident says worse (evidence); or high risk + unaccepted + unreachable/no consent (labelled "unknown", never "worse"). Only a human close clears one.
- **Twists:** department silence (one alert per department, per-ticket reminders suppressed), call surge (`surge_50.json`), phones down (failed calls = unknown, never worse).
- **Voice:** signed Retell webhooks (HMAC on the raw body, 5-minute window); duplicate intake and callback deliveries are ignored; consent is mapped from Retell's `callback_ok`.
- Human Accept, Acknowledge and Close endpoints work; phone numbers are masked in every API response.
- **Dashboard v2:** master-detail incident command view with light and dark themes; pinned critical lane, supervisor top 10, accountability chain, resident follow-up with SIMULATED controls, audit trail, original reports, human-only close, demo twist menu.
- Verified on `frontend` (Windows, Python 3.13): backend **147 passed**, `npm run build` passes, `check:readiness` 11/11, `check:phase01` 48/48, and the dashboard was driven in a browser against a live `CALL_MODE=simulate` backend.

**Not done yet:** a real Retell intake call and live outbound callback (A4, A5, A8, A9), auth on `/api/*` before tunnelling, surge counter on screen (C14), timed surge replay, projector check, fallback recordings, demo script and slides. Optional: port-domain seed (B15), Spanish callback.

### Phase 0 → Phase 1 integration gates

1. Confirm three developers can install/start their assigned app portions; backend tests and frontend build pass.
2. Confirm synthetic `storm_night` seed and approximate Highland Park geometry; geocode spoken locations without inventing missing data.
3. Agree a synchronized migration for `ReportIn.callback_ok`, acknowledgment fields/events, critical-alert representation, `frontend/src/types.ts` and fixture/tests.
4. Keep Retell credentials private and `CALL_MODE=simulate` until authenticated webhooks, consent gating and approved test numbers work.
5. Do not start hardware features or claim affiliation with LA. Phase 1 success is **3 preserved reports → 1 incident → consented follow-up → evidence-backed human review**.
