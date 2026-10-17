# HandoffProof — Parallel Build Plan (3 Computers)

Companion to *HandoffProof — Build Plan & Judge Defense*. That file says **what** we build; this one says **who builds what, on which machine, in what order**, so all three computers work at the same time without blocking each other.

**The trick that makes this parallel:** we spend the first hour together agreeing on the *seams* (data model, three Python functions, one REST shape, one seed file format). After that, each machine builds against a fake of the others' work and we swap fakes for the real thing at three sync points.

| Computer | Person | Owns (directories) | Runs on demo day |
| --- | --- | --- | --- |
| **PC-A — Voice** | A | `backend/app/voice/`, `agents/`, `docs/pitch/` | Slides + the "resident" phone |
| **PC-B — Engine** | B | `backend/app/engine/`, `backend/app/api/`, `backend/app/models.py`, `backend/seeds/`, `backend/tests/` | Backend server + tunnel (the demo server) |
| **PC-C — Dashboard** | C | `frontend/` | The big screen (dashboard full-screen) |

**Rule:** you only edit files in directories you own. Anything shared (`models.py`, `contracts.py`, `.env.example`) changes only after a message in the team chat.

---

## Phase 0 — Together, one table (≈30 min with the scaffold)

The scaffold repo already has the contracts, stubs, placeholder seeds and fixtures. Phase 0 is now **review and adjust together on one screen**, then push. Nobody starts their own track until it's pushed.

| # | Task | Status / output |
| --- | --- | --- |
| 0.1 | Push the scaffold to a GitHub repo, clone on A, B, C; each runs backend `pytest` and `npm run dev` once | ⬜ Repo cloned on A, B, C |
| 0.2 | Confirm the demo street. The scaffold uses N Figueroa St (Highland Park) with **approximate** lat/lng; fix on a map | ⬜ `backend/seeds/gazetteer.json` |
| 0.3 | Review the storm-night story: 3 reports (drain, water across road, stalled car), departments, on-call roster | ✅ draft in `backend/seeds/storm_night.json`, `oncall.json` |
| 0.4 | Read the contracts below as code and agree any changes now | ✅ `backend/app/contracts.py`, `backend/app/models.py`, `frontend/src/types.ts` |
| 0.5 | Hand-written examples of the dashboard API response | ✅ `frontend/src/fixtures/state.json`, `incident.json` (a test keeps them in sync with the backend) |
| 0.6 | Agree `.env` keys and timing profile | ✅ `.env.example`, `frontend/.env.example` |
| 0.7 | A signs up for Retell, claims free credit, buys a number (parallel with 0.2–0.6) | ⬜ Retell API key + number in team password manager |

### Repo layout

```
handoffproof/
  backend/
    app/
      main.py            # FastAPI app, mounts routers, starts ladder loop   (B)
      contracts.py       # Pydantic models: ReportIn, CallbackOutcome          (shared)
      models.py          # SQLModel tables (the data model)                   (shared, B edits)
      db.py              # SQLite session                                      (B)
      config.py          # env, timing profiles, danger words, hazard groups  (B)
      engine/            # linker, risk, debts, ladder, silence, twists, seeds (B)
      api/routes.py      # REST for the dashboard                              (B)
      voice/             # Retell webhooks, outbound client, simulator         (A)
    seeds/               # storm_night.json, surge_50.json, port_domain.json   (B)
    tests/               # pytest on seeded scenarios                          (B)
  agents/                # Retell prompts + post-call analysis field defs      (A)
  frontend/              # Vite + React dashboard                              (C)
  docs/pitch/            # demo script, slides, funding slide                  (A)
```

Every placeholder in the code is tagged with its task id below, e.g. `TODO(B4)`.

**Stack locked:** Python 3.11 + FastAPI + SQLModel/SQLite, single `uvicorn` process, an `asyncio` loop for timers. Frontend: Vite + React, **polling `/api/state` every 1 s** (no websockets). Tunnel: `cloudflared` or `ngrok` to the backend.

### Contract 1 — the three functions that join A and B

```python
# backend/app/contracts.py
class ReportIn(BaseModel):
    source: Literal["retell", "seed"]
    call_id: str
    phone: str | None
    location_text: str | None
    lat: float | None = None          # engine geocodes from gazetteer if None
    lng: float | None = None
    hazard_type: str                  # flood | blocked_drain | water_on_road | stalled_vehicle | pothole | downed_tree | ...
    danger_words: list[str] = []
    anyone_in_danger: bool = False
    transcript: str = ""
    created_at: datetime

class CallbackOutcome(BaseModel):
    incident_id: int
    call_id: str
    attempt_no: int
    outcome: Literal["worse", "same", "better", "no_answer"]
    danger: bool = False
    summary: str = ""                 # e.g. "water at the curb and rising"
    transcript: str = ""
```

| Function | Lives in | Owner | Called by |
| --- | --- | --- | --- |
| `ingest_report(r: ReportIn) -> int` (report id; links into an incident) | `engine/ingest.py` | B | A's intake webhook, B's seed loader |
| `request_callback(incident_id, phone, attempt_no, vars: dict) -> str` (call id) | `voice/callbacks.py` | A | B's ladder |
| `record_callback_outcome(o: CallbackOutcome) -> None` | `engine/ladder.py` | B | A's callback webhook, A's simulator |

Until the real ones exist, each owner commits a **stub in Phase 0** (`ingest_report` just inserts a row; `request_callback` logs and returns `"fake-call-1"`).

### Contract 2 — the REST API between B and C

| Method + path | Body | Purpose |
| --- | --- | --- |
| `GET /api/state` | — | Everything the main screen needs (shape below) |
| `GET /api/incidents/{id}` | — | Incident + `reports[]`, `debts[]`, `events[]`, `callbacks[]`, `assignment` |
| `POST /api/incidents/{id}/accept` | `{owner}` | Department taps Accept |
| `POST /api/incidents/{id}/close` | `{by, note}` | Human-only close (never automated) |
| `POST /api/incidents/{id}/simulate-callback` | `{outcome, danger}` | Fallback button (A's simulator behind it) |
| `POST /api/twists/{name}` | `{on}` or `{domain}` | `dept_silent`, `surge`, `phones_down`, `domain` |
| `POST /api/demo/reset` | `{seed}` | Wipe DB, load a seed file |

```json
{
  "now": "2026-10-18T02:14:05Z",
  "timing_profile": "demo",
  "twists": { "dept_silent": false, "surge": false, "phones_down": false, "domain": "storm" },
  "incidents": [{
    "id": 1, "title": "Flooding — N Figueroa St @ Ave 52", "hazard_type": "flood",
    "status": "open", "ladder_step": 4, "risk_score": 82, "report_count": 3,
    "department": "Street Services", "owner": "J. Ramirez (on-call)", "accepted": false,
    "next_step_at": "2026-10-18T02:14:40Z",
    "debts": [{ "kind": "location", "label": "Exact location unclear" },
              { "kind": "caller_unreachable", "label": "1 caller unreachable" },
              { "kind": "no_owner", "label": "No one has accepted" }],
    "why": "Unowned 6 min · resident says worse · 1 caller unreachable",
    "lat": 34.11, "lng": -118.20
  }],
  "supervisor_queue": [1],
  "departments": [{ "name": "Street Services", "assigned_1h": 12, "accepted_1h": 0, "silent": true }],
  "alerts": [{ "type": "department_silent", "department": "Street Services",
               "text": "Street Services accepted 0 of 12 in the last hour" }]
}
```

### Contract 3 — env and timing

```
RETELL_API_KEY=            RETELL_FROM_NUMBER=
RETELL_INTAKE_AGENT_ID=    RETELL_CALLBACK_AGENT_ID=
PUBLIC_BASE_URL=           # tunnel URL of whoever is running the backend
CALL_MODE=simulate         # simulate | live
TIMING_PROFILE=demo        # demo | real
DB_PATH=./handoffproof.db
LLM_API_KEY=               # optional; engine must work without it
```

| Ladder step | `real` | `demo` (stage) |
| --- | --- | --- |
| Nudge after not accepted | 10 min | 15 s |
| Default owner | 20 min | 30 s |
| Callback | 30 min | 45 s |
| Callback retry after no answer | 5 min | 20 s |

---

## Phase 1 — Parallel: each piece works alone (≈3 h)

Goal = doc milestone *"inbound intake call lands in the backend; cases render on the dashboard."*

| PC-A — Voice | PC-B — Engine | PC-C — Dashboard |
| --- | --- | --- |
| **A1.** Write intake agent prompt in `agents/intake.md`: ask location (street + cross-street), what's happening, anyone in danger; tell anyone in immediate danger to hang up and call 911 | **B1.** `models.py` tables from the data model (reports, incidents, debts, assignments, callbacks, events) + `ladder_step`, `next_step_at` on incidents | **C1.** Vite + React app; layout: **Department queue** (left), **Supervisor top 10** (right), **Incident detail** drawer |
| **A2.** Configure post-call analysis fields in Retell: `location_text`, `hazard_type` (enum), `danger_words`, `anyone_in_danger`, `callback_ok` | **B2.** Seed loader: replays a seed file through `ingest_report` with per-report time offsets | **C2.** `useHandoffState()` polling hook against `fixtures/state.json` (switch by `VITE_API=fixture\|live`) |
| **A3.** `voice/webhooks.py`: `POST /retell/webhook`, verify the signature, on `call_analyzed` map the payload → `ReportIn` → `ingest_report` | **B3.** Geocode from `gazetteer.json` (string match on cross-streets); no match → open a `location` debt | **C3.** Incident card: title, hazard icon, report count ("3 witnesses"), risk badge, ladder step dots 1–5, debt chips, countdown to `next_step_at` |
| **A4.** Run backend locally + tunnel; point the Retell webhook at it; make a real test call | **B4.** Linker: ≤300 m, ≤60 min, compatible hazard group (water / road / power); unknown location → link on same street name | **C4.** Incident detail: reports + transcripts, **"Why it's here"** event timeline, callbacks list |
| **A5.** **Save the raw webhook JSON** as `backend/tests/fixtures/retell_call_analyzed.json` and push it — B tests against it | **B5.** Risk score v1 (below) + debts open/clear | **C5.** Visual language: red = supervisor queue, amber = default owner, grey = accepted; big-screen readable at 3 m |
| **A6.** Ask the Retell rep the open questions (outbound on free credit, voicemail detection, callbacks for city tickets) | **B6.** `GET /api/state`, `GET /api/incidents/{id}` returning real DB data; pytest: `storm_night.json` → 1 incident, 3 reports | **C6.** Error and empty states: backend down banner, "no incidents", loading; check the layout on the projector resolution |

**Risk score v1** (B tunes it on seeds; it never falls with time or silence):
`hazard base (flood 30, stalled_vehicle 35, water_on_road 25, blocked_drain 15, pothole 5)` + `25 if any danger word` + `5 per extra linked report (max +25)` + `30 per "worse"` + `10 per "same"` − `10 per "better"` + `15 per no_answer` + `10 while caller_unreachable is open`.

### 🔗 Sync 1 (15 min, everyone)

1. B pulls everyone's code and runs the backend + tunnel; A points the Retell webhook at **B's** tunnel.
2. C sets `VITE_API=live` against B's machine (same Wi-Fi, `http://<B-ip>:8000`).
3. **Pass when:** `POST /api/demo/reset {seed: storm_night}` shows 1 incident with 3 witnesses on C's screen, then a **live call** from a teammate's phone adds a 4th witness within ~10 s of hanging up.

---

## Phase 2 — Parallel: the escalation loop (≈3–4 h)

Goal = doc milestones *"linking, debt list, Accept, default owner, supervisor queue"* and *"outbound callback loop end to end; escalation on worse and on no-answer."*

| PC-A — Voice | PC-B — Engine | PC-C — Dashboard |
| --- | --- | --- |
| **A7.** Callback agent in Retell (`agents/callback.md`): one question set — *worse / same / better / anyone in danger?* — using dynamic variables `{{location}}`, `{{hazard}}` | **B7.** Ladder loop: `asyncio` task every 2 s walks open incidents through steps 1→5 using the timing profile; writes an `events` row with a one-line reason at each step | **C7.** Accept button → `POST /accept`; card turns grey instantly (optimistic), ladder stops |
| **A8.** `request_callback()` via Retell create-phone-call: `from_number`, `to_number`, `override_agent_id`, dynamic variables, and **`incident_id` + `attempt_no` in metadata** so the webhook can map back | **B8.** Step 3 default owner from `seeds/oncall.json` (department + area → named person). Never invent owners | **C8.** Supervisor queue animation: card slides to the top and pulses red when it enters; reason line in bold |
| **A9.** Callback webhook: post-call fields → `CallbackOutcome`; no answer / voicemail / dial failure (from the call's disconnection reason) → `outcome="no_answer"`. Verify field names against Retell's current docs | **B9.** `record_callback_outcome`: update risk, open/clear `caller_unreachable`, schedule retry on no_answer; step 5 when worse, danger, or no_answer on a high-risk case | **C9.** "Simulate callback" buttons in incident detail (worse / same / better / no answer) → `POST /simulate-callback` |
| **A10.** `voice/simulator.py`: in `CALL_MODE=simulate`, `request_callback` waits ~8 s then calls `record_callback_outcome` with a scripted answer. Also backs the simulate endpoint | **B10.** Supervisor queue: top 10 by risk among unaccepted or worsening; build the `why` string from the events | **C10.** Live callback indicator on the card ("📞 Calling resident… attempt 2") from `callbacks[]` |
| **A11.** Guardrails in both prompts: never says someone is safe, never promises dispatch, always offers 911 for immediate danger | **B11.** `POST /close` requires `by`; nothing in the engine can set `status=closed`. Pytest: silence never closes; no_answer raises risk | **C11.** Wire every remaining fixture field to live; delete the fixture only after Sync 2 passes |

### 🔗 Sync 2 (30 min, everyone)

1. Run with `CALL_MODE=simulate`: reset → wait → nudge → default owner → simulated "worse" → **card jumps to supervisor top, red, with reason**. Run it 3×.
2. Switch to `CALL_MODE=live`, put the "resident" phone (A's) on the incident: real callback rings, teammate says *"the water is at the curb and rising,"* card turns red.
3. Run a no-answer case (decline the call): retry fires, risk rises, case never closes.

---

## Phase 3 — Parallel: twists, fallbacks, pitch (≈3 h)

Goal = doc milestone *"department-silence detector; twist toggles; first full dry run."*

| PC-A — Voice + pitch | PC-B — Engine | PC-C — Dashboard + evidence |
| --- | --- | --- |
| **A12.** Record a clean audio + screen capture of a live callback (fallback #2) | **B12.** Department-silence detector: assigned ≥ 5 and accepted 0 in the last hour → **one** department alert, and per-ticket nudges for that department are suppressed | **C12.** Twist panel (hidden behind a key, e.g. `T`): Dept silent · Call surge · Phones down · Domain swap · Reset |
| **A13.** Demo script in `docs/pitch/demo.md`, timed to the 3-minute table, with who clicks what | **B13.** `surge_50.json` — 50 calls over 60 s that collapse into ~4 incidents | **C13.** Department alert banner at the top: "Street Services accepted 0 of 12 in the last hour" |
| **A14.** Slides: hook, LA evidence, insight, demo, dual use, funding (eligible pathway, not funded), pilot ask | **B14.** `phones_down`: `request_callback` fails → no_answer → risk up, never closed | **C14.** Counter strip: "20 calls → 1 incident" when surge runs |
| **A15.** (Cut list #1, only if green) Spanish callback agent | **B15.** `port_domain.json` (container: carrier → customs → terminal) running the same ladder unchanged | **C15.** Domain swap relabels the UI from the seed (department names, hazard icons) — no code fork |
| | **B16.** `POST /api/demo/reset` reliable in < 2 s; run every pytest | **C16.** Demo polish: full-screen mode, cursor hidden, font sizes checked from the back of the room |

### 🔗 Sync 3 — first full dry run (Sat night)

- Full 3-minute demo with timer, live call, then each twist.
- **C records the fallback video** of the full demo (fallback #1).
- Write down every glitch; each owner fixes their own.

---

## Phase 4 — Sunday morning (together)

| Time | Everyone |
| --- | --- |
| Morning | Polish only glitches from Sync 3; no new features. Each person rehearses their Q&A category: A — novelty + funding, B — escalation + technical, C — safety + dual use |
| **Freeze − 2 h before judging** | Tag `demo-freeze`. After this only text/slide changes |
| Before judging | 3 full rehearsals: A pitches, C drives, B watches the server and answers technical questions |

**Demo-day machine setup**

- **PC-B:** backend + tunnel, `TIMING_PROFILE=demo`, `CALL_MODE=live`, laptop plugged in, sleep disabled. Mobile hotspot as backup network.
- **PC-C:** dashboard on the projector, twist panel one key away, fallback video open in a background tab.
- **PC-A:** slides + the "resident" phone, ringer on loud, number confirmed against the seed.
- Fallback order if something breaks: live call → simulate-callback button → seeded data alone → fallback video.

---

## Parallel at a glance

```
            Phase 0        Phase 1               Phase 2                  Phase 3                Phase 4
            (together)     (~3h)                 (~3-4h)                  (~3h)                  (Sun)
PC-A Voice  ┐              intake agent,         callback agent,          fallback recording,    pitch lead
            │ repo,        webhook, real call →  outbound client,         demo script, slides,
            │ contracts,   fixture JSON          simulator, guardrails    (Spanish)
PC-B Engine ├ seeds,       models, seeds,        ladder loop, default     dept silence, surge,   tech Q&A,
            │ fixtures     geocode, linker,      owner, outcomes,         phones down, port      runs server
            │              risk, /api/state      supervisor top 10        domain, reset
PC-C Dash   ┘              layout, cards,        accept, red jump,        twist panel, alert     drives demo
                           detail, states        simulate buttons, live   banner, video
                               ▲                      ▲                        ▲
                             Sync 1                 Sync 2                   Sync 3
                         call → card            callback → red          full dry run + video
```

## What blocks what (and the fake that unblocks it)

| If this isn't ready… | …the blocked person uses | Owner of the fake |
| --- | --- | --- |
| Retell intake agent | `seeds/storm_night.json` through `ingest_report` | B |
| Real engine | Phase 0 stub `ingest_report` that just inserts a row | B |
| Retell outbound / free-credit limits | `CALL_MODE=simulate` | A |
| Backend API | `frontend/src/fixtures/*.json` | C |
| Geocoder | `gazetteer.json` lookup | B |
| LLM key | Rules only (danger-word list, hazard enum from Retell) — the LLM is an optional cleanup step | B |

## Git rules

- One `main` branch; pull before you start, push every working step (small commits).
- Only touch your own directories; shared files need a chat message first.
- Run `pytest` (backend) or `npm run build` (frontend) before pushing.
- `.env` never committed; `.env.example` is the contract.
- Each sync point starts with all three pushing, then B pulling and running.
