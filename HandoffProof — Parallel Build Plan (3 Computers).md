# HandoffProof — Parallel Build Plan (3 Computers)

Companion to *HandoffProof — Build Plan & Judge Defense*. That file defines the **updated software-only incident intelligence and accountability MVP**; this file assigns the same work to **three people in parallel** without editing one another's directories.

**The trick that makes this parallel:** we spend the first hour together agreeing on the *seams* (data model, three Python functions, one REST shape, one seed file format). After that, each machine builds against a fake of the others' work and we swap fakes for the real thing at three sync points.

| Computer | Person | Owns (directories) | Runs on demo day |
| --- | --- | --- | --- |
| **PC-A — Voice** | A | `backend/app/voice/`, `agents/`, `docs/pitch/` | Slides + the "resident" phone |
| **PC-B — Engine** | B | `backend/app/engine/`, `backend/app/api/`, `backend/app/models.py`, `backend/seeds/`, `backend/tests/` | Backend server + tunnel (the demo server) |
| **PC-C — Dashboard** | C | `frontend/` | The big screen (dashboard full-screen) |

**Rule:** only edit files you own. Shared changes — `backend/app/contracts.py`, `backend/app/models.py`, `frontend/src/types.ts`, `.env.example` or documented API shapes — require an explicit team message and coordinated review **before editing**. No wireless sensing or hardware tasks are part of this build.

---

## Progress — Oct 17, 2026 (branch `frontend`, merged backend + dashboard v2)

✅ done and verified · 🟡 partly done · ❌ not started · ⚪ optional (cut list)

**Verified on Windows:** backend `pytest` **147 passed** · frontend `npm run build` passes · `npm run check:readiness` **11/11** · `npm run check:phase01` **48/48** (12 consent × outcome scenarios × 4 handoff stages, rendered by the real dashboard) · live run: storm-night ladder end to end in `CALL_MODE=simulate`, Acknowledge and Accept clicked in the browser and recorded by the backend.

**Phases at a glance**

| Phase | Status | What's left |
| --- | --- | --- |
| 0 Together | 🟡 | Third machine set up; paste updated prompts into Retell; confirm phone number |
| 1 Each piece alone | 🟡 | Engine and dashboard ✅; a **real** Retell intake call through a tunnel (A4) and a redacted real payload (A5) |
| Sync 1 | 🟡 | Passes with signed synthetic webhooks (seed → 1 incident / 3 reports → 4th report); not yet with a live call |
| 2 Escalation loop | 🟡 | Engine and dashboard ✅; **live outbound callback** to the opted-in teammate (A8, A9) |
| Sync 2 | 🟡 | Simulated loop, no-consent, no-answer and human-close cases ✅ (tests + live run); live-call half open |
| 3 Twists, fallbacks, pitch | 🟡 | Silence, surge, phones-down ✅; surge counter (C14), fallback recordings (A12, video), demo script and slides (A13, A14) |
| Sync 3 / Phase 4 | ❌ | First full dry run, fallback video, freeze, three rehearsals |

**Person A — Voice + pitch**

| Task | Status | Notes |
| --- | --- | --- |
| A1 Intake prompt (demo-labelled, consent, 911) | ✅ | `agents/intake.md`; must be re-pasted into Retell |
| A2 Retell extraction fields (5 + 3) | ✅ | Browser-tested in Retell |
| A3 Signature check on raw body, duplicate protection | ✅ | `voice/security.py` (HMAC + 5-min window); duplicate intake and callback webhooks ignored |
| A4 Real call through a tunnel | ❌ | Needs the tunnel and an opted-in teammate |
| A5 Redacted real webhook fixture | ❌ | Only a synthetic fixture exists (`tests/fixtures/synthetic_retell_intake.json`) |
| A6 Retell number / credit / constraints | 🟡 | Not yet confirmed |
| A7 Callback agent prompt | ✅ | `agents/callback.md` |
| A8 Live outbound `request_callback` | 🟡 | Code written, consent-gated by the engine; never run against Retell |
| A9 Parse callback / no-answer payloads | 🟡 | Mapped and tested with synthetic payloads; real payload unchecked |
| A10 Simulator + no-consent negative test | ✅ | |
| A11 Prompt guardrails | ✅ | No impersonation, no safety claims, 911 direction |
| A12 Consented demo recording | ❌ | |
| A13 Demo script (`docs/pitch/demo.md`) | ❌ | |
| A14 Slides incl. funding (potential, unverified) | ❌ | |
| A15 Spanish callback | ⚪ | |

**Person B — Engine**

| Task | Status | Notes |
| --- | --- | --- |
| B1 Contract migration (consent, acknowledgment, critical alerts, evidence) | ✅ | Additive with defaults; `types.ts` and fixtures mirror it |
| B2 Seeds keep every report as its own row | ✅ | Seeds validated before a destructive reset |
| B3 Geocoding incl. "Avenue fifty two"; unresolved → debt | ✅ | |
| B4 Linker (≤300 m, ≤60 min, hazard group, street fallback) | ✅ | Link reason logged per report |
| B5 Evidence-only risk | ✅ | Negation-aware danger phrases; no-answer/consent/time add nothing |
| B6 State/detail responses; 1 incident / 3 reports | ✅ | |
| B7 Ladder timers + audit events | ✅ | |
| B8 Default on-call owner (proposed, never invented) | ✅ | |
| B9 Callback outcomes; no-answer = unknown | ✅ | Max 2 attempts |
| B10 Top 10 + uncapped critical alerts | ✅ | |
| B11 Human-only close; safety tests | ✅ | |
| B12 Department silence, nudge suppression | ✅ | One alert per department; critical alerts unaffected |
| B13 Surge (`surge_50.json`) | 🟡 | All 50 reports ingest at once; timed replay not built |
| B14 Phones-down = no-answer, never worse | ✅ | |
| B15 Port-domain seed | ⚪ | Domain twist accepts only `storm` |
| B16 Deterministic reset | ✅ | |

**Person C — Dashboard**

| Task | Status | Notes |
| --- | --- | --- |
| C1 Layout + pinned critical lane | ✅ | Dashboard v2 (master-detail), light and dark themes |
| C2 Polling, fixture/live switch | ✅ | |
| C3 Cards: proposed / acknowledged / accepted | ✅ | |
| C4 Detail: every report, evidence, audit trail | ✅ | |
| C5 Colour: red only for critical or high risk | ✅ | |
| C6 Error, empty, loading states | 🟡 | Done; projector check open |
| C7 Acknowledge + Accept, no optimistic accept | ✅ | Name editable in the top bar |
| C8 Critical alerts always visible, arrival animation | ✅ | |
| C9 SIMULATED label on simulate buttons | ✅ | |
| C10 Calling / consent status, masked phones | ✅ | |
| C11 Live wiring | ✅ | Verified in a browser against FastAPI |
| C12 Twist panel | ✅ | Domain swap not offered (B15 optional) |
| C13 Department alert + separate critical lane | ✅ | |
| C14 "50 reports → ~4 incidents" counter | ❌ | |
| C15 Second-domain relabel | ⚪ | |
| C16 Projector check, prototype label | 🟡 | Label ✅; projector open |

**Definition of done:** ✅ 2 linking · ✅ 3 ownership · ✅ 5 safety · ✅ 6 human closure · ✅ 7 demo labelling · 🟡 1 input (signature ✅, real call ❌) · 🟡 4 consent (simulated ✅, live callback ❌) · 🟡 8 engineering (tests ✅; three-machine sign-off and fallback recording ❌).

---

## Phase 0 — Together, one table (≈30 min with the scaffold)

The scaffold repo has contracts, stubs, seeds and fixtures. **This updated scope is a plan, not a claim that all new fields exist.** Review interfaces together, record approval, then each owner builds against stable contracts. No one begins changes to shared schemas unilaterally.

| # | Task | Status / output |
| --- | --- | --- |
| 0.1 | Clone scaffold on A, B, C; A/B run backend tests, C runs `npm run build` and dashboard | 🟡 Mac and Windows verified (Windows on `frontend`: 147 passed, build passes); third machine not yet verified |
| 0.2 | Confirm approximate Highland Park N Figueroa locations visually; test spoken "Avenue fifty two" normalization | ✅ Transit-stop coordinates with sources; spoken-number normalization tested |
| 0.3 | Agree fictional storm-night reports, departments, and on-call contacts | ✅ `backend/seeds/storm_night.json`, `oncall.json` (only the demo resident gives callback consent) |
| 0.4 | Agree shared contract migration: `callback_ok`, acknowledgment event/field, critical-alert payload and evidence provenance | **Approved; implemented on `backend`:** `ReportIn.callback_ok`, `acknowledged_at/by`, `POST /acknowledge`, `critical_alerts[]`, event `actor`/`evidence`, masked phones. All additive with defaults; `types.ts` and fixtures updated |
| 0.5 | Fixture state/detail JSON matches currently committed contracts; plan updated examples | ✅ Fixtures carry the new fields; contract tests pass |
| 0.6 | Agree root `.env` and frontend `.env.local`, `CALL_MODE=simulate`, timing and no secrets in Git | 🟡 Templates exist; verify on all machines |
| 0.7 | A configures Retell Intake and Callback agents (5 + 3 extracted fields), stores IDs/API key privately | 🟡 Browser-level Retell tests passed; phone number, live webhook and outbound calls **not yet verified** |
| 0.8 | Confirm safety: prototype/nonofficial voice prompt, 911 direction, opt-in calls only, no unsanctioned data collection | 🟡 Prompts updated in repo and webhook signatures enforced; prompts must be re-pasted into Retell; `/api/*` is still unauthenticated if the whole backend is tunnelled |
| 0.9 | B/C smoke-test live local `VITE_API=live` against FastAPI; reset seeds; no public webhook yet | ✅ Dashboard driven against a live backend in a browser |
| 0.10 | Team approves software-only MVP, three-person ownership, and definition of done | ✅ Contracts approved by the team |

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

**Stack locked:** Python 3.11 + FastAPI + SQLModel/SQLite, one `uvicorn` process and an `asyncio` timer loop. Vite + React polls `/api/state` every 1 s. Public tunnel **only after Retell signature verification**; simulated calls until then. **No sensor/ESP32 work.**

### Scope gate — freeze before Phase 1

- **No wireless sensing, hardware, ESP32 or city-system integration**; all inputs are Retell speech and synthetic test reports.
- **Accountability:** track assignment, explicit human acknowledgment, explicit acceptance, and human-verified resolution/closure as separate concepts. Do not overwrite `accepted_at` with a default owner.
- **Consent:** Retell's tested `callback_ok` extraction is not yet stored in `ReportIn`; no live callbacks until it is persisted and guarded; missing/false consent means no call.
- **Safety:** danger must be grounded in a source report or confirmed worsening. No-answer = unknown follow-up; top-10 cap cannot hide critical alerts; non-emergency prototype never dispatches.
- **One story:** three synthetic reports → one incident retaining three report rows → unaccepted handoff → opted-in follow-up → evidence-based human-review alert.

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
    # PLANNED SHARED CONTRACT ADDITION: callback_ok: bool = False
    # Do NOT enable outbound calls until consent is persisted and enforced.
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

**Current scaffold:** `ingest_report` inserts individual rows; `request_callback` simulates when `CALL_MODE=simulate`. These are not proofs of consent-gated live calls. **Planned shared migration:** append `callback_ok: bool = False` to ReportIn and persist it; add an acknowledgment timestamp/event to the assignment domain; expose a persistent critical-alert list/flag and source evidence for dashboard use. Coordinate Pydantic, SQLModel, TypeScript and fixtures/tests in one review before implementation.

### Contract 2 — the REST API between B and C

| Method + path | Body | Purpose |
| --- | --- | --- |
| `GET /api/state` | — | Main screen; **planned:** include persistent critical safety alerts in addition to the top 10 |
| `GET /api/incidents/{id}` | — | Incident + **all distinct** `reports[]`, `debts[]`, `events[]`, `callbacks[]`, `assignment` |
| `POST /api/incidents/{id}/accept` | `{owner}` | Human explicitly **accepts responsibility**, distinct from mere assignment |
| **PLANNED** `POST /api/incidents/{id}/acknowledge` | `{by}` | Record **receipt only**; add in coordinated contract migration |
| `POST /api/incidents/{id}/close` | `{by, note}` | Authorized human-only closure with recorded resolution evidence (not automated) |
| `POST /api/incidents/{id}/simulate-callback` | `{outcome, danger}` | Fallback button (A's simulator behind it) |
| `POST /api/twists/{name}` | `{on}` or `{domain}` | `dept_silent`, `surge`, `phones_down`, `domain` |
| `POST /api/demo/reset` | `{seed}` | Demo-only wipe/reload; test with synthetic data, keep inaccessible from public internet |

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

**Contract example status:** the JSON above illustrates the **current scaffold** and is not a final schema for the updated scope. Planned extensions, subject to three-person agreement, are `assignment.acknowledged_at`, incident evidence/source refs, explicit consent in report detail, and `critical_alerts[]` at state level. Do not invent these fields in the frontend until B's Pydantic API and C's TypeScript types/fixtures change together. A caller's `no_answer` is a contact debt, not an increment to the physical-danger score.

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

These are **timer defaults only**: no retries occur unless initial contact was explicitly authorized, the destination is valid, and the agreed rate/cadence policy permits another call.

---

## Phase 1 — Parallel: each piece works alone (≈3 h)

Goal = doc milestone *"inbound intake call lands in the backend; cases render on the dashboard."*

| PC-A — Voice | PC-B — Engine | PC-C — Dashboard |
| --- | --- | --- |
| **A1.** Finalize demo-labelled intake prompt: location, hazard, danger, **explicit callback permission**; immediate danger → 911 | **B1.** Plan **shared-contract migration** for persisted `callback_ok`, acknowledgment and evidence; coordinate before changing `models.py` or `contracts.py` | **C1.** Keep existing department/supervisor/detail layout; design a **separate pinned critical-alert lane** |
| **A2.** Verify previously tested Retell extraction fields: 5 intake incl. `callback_ok`, 3 callback; preserve examples privately | **B2.** Keep seeded reports as distinct rows through `ingest_report`; synthetic phones only | **C2.** Keep `useHandoffState()` 1 s polling with fixture/live switch; document what fixture mode simulates |
| **A3.** In `voice/webhooks.py` verify **Retell signature on raw payload**, map `call_analyzed`, prevent duplicate ingestion, pass consent to B | **B3.** Geocode `gazetteer.json`, including spoken street numbers ("Avenue fifty two"); unresolved location opens a debt | **C3.** Incident card: witnesses, risk, ownership **assigned / acknowledged / accepted**, debt chips, source-backed reason |
| **A4.** After A3, use a tunnel + opted-in teammate to test a real call; otherwise use simulated webhook | **B4.** Linker: ≤300 m, ≤60 min, compatible hazard group; retain original reports and prevent unsafe merges | **C4.** Detail drawer shows **every linked report**, transcript/extracted values, evidence and handoff event timeline |
| **A5.** Save a **redacted** real webhook fixture for B's tests (no genuine phone/transcript PII or secrets) | **B5.** Deterministic physical-risk score plus separate contact/ownership uncertainty; test false-positive danger extraction | **C5.** Accessible color/status encoding; do not use red simply for old/unaccepted low-risk cases |
| **A6.** Verify Retell API/number/free-credit and callbacks constraints; ensure prototype is not impersonating city government | **B6.** Expose new agreed state/detail shapes only after shared review; seeded test targets **1 incident / 3 retained reports** | **C6.** Backend-down / empty / loading states, projector resolution; run `npm run build` and API integration smoke check |

**Risk score v1 — planned, not implemented:** `hazard base` (flood 30, stalled_vehicle 35, water_on_road 25, blocked_drain 15, pothole 5) + `25 if a supported danger phrase/person at risk` + `5 per additional independently sourced report` (capped +25) + `30 for explicit worsening`; `same` adds zero danger. Verified improvement may lower danger only on new evidence; never auto-close. `no_answer`, absent callback consent and an unaccepted handoff are **separate operational/contact uncertainty signals**, *not physical-risk points*. Critical display is pinned independently of the top-10 rank; always explain the evidence.

### 🔗 Sync 1 (15 min, everyone)

1. B pulls everyone's code and runs the backend + tunnel; A points the Retell webhook at **B's** tunnel.
2. C sets `VITE_API=live` against B's machine (same Wi-Fi, `http://<B-ip>:8000`).
3. **Pass when:** seed reset shows 1 incident with 3 retained report records on C's screen; a **verified, consent-aware** live or clearly labeled simulated intake adds a 4th report without destroying originals. Check missing-consent fields and audit source.

---

## Phase 2 — Parallel: the escalation loop (≈3–4 h)

Goal = doc milestones *"linking, debt list, Accept, default owner, supervisor queue"* and *"outbound callback loop end to end; escalation on worse and on no-answer."*

| PC-A — Voice | PC-B — Engine | PC-C — Dashboard |
| --- | --- | --- |
| **A7.** Callback agent asks worse/same/better and danger, with `{{location}}` / `{{hazard}}`; identify demo clearly | **B7.** Timer ladder nudges on deadlines but never treats age as hazard evidence; records reasoned audit events | **C7.** Add **Acknowledge** then explicit **Accept** UI actions; no optimistic "accepted" before server confirmation |
| **A8.** Outbound `request_callback` uses authorized number, agent ID, dynamic variables and metadata; **A and B jointly enforce `callback_ok=true` before API call** | **B8.** Load configured on-call owner; assign without setting accepted; keep `no_owner` if missing; persist human acknowledgment separately | **C8.** Animate rank changes but keep all **critical alerts permanently visible** even when not top 10 |
| **A9.** Parse callback and no-answer events against real provider payload; respect voicemail/privacy; no repeat calls without consent/rate policy | **B9.** Outcome updates evidence and contact debt; worse/danger can trigger critical review; no_answer only preserves uncertainty or already-high-risk review | **C9.** Keep simulate buttons; visibly label simulated results as **SIMULATED** |
| **A10.** Simulator schedules scripted callback in `CALL_MODE=simulate`; add no-consent negative test (no simulated outbound) | **B10.** Supervisor top 10 plus persistent critical alerts; build reasons from individual report/callback event IDs | **C10.** Show calling / unanswered / callback consent status without exposing full phone number |
| **A11.** Prompts never impersonate LA officials, claim safety, promise crews or dispatch; tell immediate danger callers to call 911 | **B11.** Closure human-only and evidence backed. Tests: unaccepted ≠ acknowledged; no consent → no call; silence ≠ worse; critical never hidden | **C11.** After contract sign-off connect all new live fields; run build and integration tests |

### 🔗 Sync 2 (30 min, everyone)

1. Run with `CALL_MODE=simulate`: reset → nudge → configured default contact (still **not accepted**) → **consented** simulated "worse" → persistent critical alert with a source-backed reason. Repeat 3×.
2. With webhook verification and consent gate proved, enable `CALL_MODE=live` for the opted-in teammate only; test "water rising" and check no official/city claims.
3. Test **no consent** (zero outbound API actions), **no answer** (contact debt, no automatic physical-worsening inference) and **human-only closure**. Repeat on two separate runs.

---

## Phase 3 — Parallel: twists, fallbacks, pitch (≈3 h)

Goal = doc milestone *"department-silence detector; twist toggles; first full dry run."*

| PC-A — Voice + pitch | PC-B — Engine | PC-C — Dashboard + evidence |
| --- | --- | --- |
| **A12.** Record clean **consented demo** audio and callback-screen capture; redact all real numbers | **B12.** Silent department (assigned ≥5, accepted 0 / hour): one operational alert, **without suppressing case-critical alerts** | **C12.** Twist panel: Dept silent · Call surge · Phones down · Synthetic domain swap · Reset |
| **A13.** Draft 3-minute demo in `docs/pitch/demo.md`, including "prototype, not city service" line and human Accept moment | **B13.** `surge_50.json` — 50 synthetic calls, ~4 incidents, original reports individually accessible | **C13.** Show grouped department alert and separately pinned case-critical alerts |
| **A14.** Slides: LA evidence, what changed at handoff, evidence/consent, dual use, **potential** funding (unverified until checked) | **B14.** Phones-down twist: `no_answer` as unknown-contact debt, never auto-closed or physically upgraded solely by silence | **C14.** "50 reports → ~4 incidents" plus count of preserved source reports |
| **A15.** Spanish callback only if all essential flows pass | **B15.** Optional `port_domain.json`: synthetic carrier/customs/terminal handoff, **no real integration** | **C15.** Same UI labels and statuses for synthetic second domain; no parallel codebase |
| | **B16.** Reset returns deterministically with synthetic demo data; run all pytest; verify no real data remains | **C16.** Projector check, captions, error/fallback states and prominent prototype label |

### 🔗 Sync 3 — first full dry run (Sat night)

- Full 3-minute **synthetic / opted-in** demo with timer, source-backed critical alert, and human Accept; then each twist.
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

- **PC-B:** backend + tunnel **only after webhook validation**, `TIMING_PROFILE=demo`, `CALL_MODE=live` only for approved opted-in test calls; otherwise simulate. Laptop powered and backup network ready.
- **PC-C:** dashboard on projector with permanent critical-alert lane, twist panel one key away and fallback video queued.
- **PC-A:** slides + consenting "resident" teammate's phone; demo agent explicitly identifies itself as a prototype; confirm callback permission/number privately.
- Fallback order if something breaks: live call → simulate-callback button → seeded data alone → fallback video.

---

## Updated definition of done (all three must demonstrate)

1. **Input:** real Retell test call is accepted only after webhook signature checking; browser-only Retell prompt tests do not count as an integrated webhook.
2. **Linking:** 3 different water-related storm reports appear as 1 incident with **3 accessible original report records** and explainable linking reason.
3. **Ownership:** assignment ≠ acknowledgment ≠ acceptance; the on-call name is from configuration and human actions are audit-logged.
4. **Consent:** an unconsented or unknown-consent case produces **zero** outbound callback requests; consented test case can generate a valid callback.
5. **Safety:** reported danger/worsening creates evidence-backed human review; `no_answer` does not mean worsening, does not close; all critical alerts stay visible beyond top 10.
6. **Human closure:** only an authorized named human records completion with a note/evidence; neither timer nor LLM closes.
7. **Demo:** synthetic LA municipal story and optional synthetic dual-use handoff; prototype disclaimer present; nothing connects to official city systems or sensors.
8. **Engineering:** backend tests, frontend build, combined API smoke test, three-machine sign-off and a reproducible fallback recording.

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
                         call → card        consent → critical alert     full dry run + video
```

## What blocks what (and the fake that unblocks it)

| If this isn't ready… | …the blocked person uses | Owner of the fake |
| --- | --- | --- |
| Retell intake agent | `seeds/storm_night.json` through `ingest_report` | B |
| Real engine | Phase 0 stub `ingest_report` that just inserts a row | B |
| Retell outbound / free-credit limits, or missing consent | `CALL_MODE=simulate` for synthetic tests; **never synthesize consent for live calls** | A + B |
| Backend API | `frontend/src/fixtures/*.json` | C |
| Geocoder | `gazetteer.json` lookup | B |
| LLM key | Deterministic grouping/risk rules and Retell extraction; optional LLM cleanup only | B |
| New shared fields not merged yet | Keep scaffold types in sync; agree revised `ReportIn`/`StateView`/TS types before feature branches depend on them | A + B + C |

## Git rules

- Keep `main` stable; work on **separate owned feature branches**, small commits and reviewed pull requests; coordinate before integrating.
- Only touch your own directories; **shared contracts need agreement in team chat** and coordinated updates.
- Run `pytest` (backend) or `npm run build` (frontend) and relevant integration tests before PR.
- `.env` and `frontend/.env.local` are never committed; `.env.example` documents keys only; redact PII in webhook fixtures.
- At each sync point all three push their branches, review shared changes, and B runs merged demo tests before updating `main`.
