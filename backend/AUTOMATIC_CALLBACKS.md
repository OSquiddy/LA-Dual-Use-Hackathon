# Automatic resident callbacks

Current local mode, October 17, 2026: **automatic live callbacks enabled at the user's explicit request**. One earlier controlled real callback completed and its signed result was recorded. The Callback Agent's DNC and extraction settings are now published, and the saved webhook base matches the active gateway. Existing data and attempt limits are preserved; no database reset, commit or push was performed.

## Pause or resume automatic calling

In the private repository-root `.env`, automatic mode uses:

```dotenv
CALL_MODE=live
LIVE_CALLBACKS_ENABLED=1
LADDER_ENABLED=1
```

**To stop new automatic calls, change `LIVE_CALLBACKS_ENABLED=0` and save. No backend restart is needed.** The backend checks the saved file before scheduling and dispatching automatic calls. This does not hang up a call already dispatched. Intake webhooks and the dashboard continue working.

Set it back to `1` to resume a process that was started with automatic live calling authorized. Overdue eligible incidents may then call immediately. If the backend was restarted while automation was off, restart it after enabling the switch to authorize that new process. A missing, unreadable or invalid settings file disables automatic dispatch. Manual live calls still require their separate reviewer-authorized confirmation.

For full simulation mode, set `CALL_MODE=simulate` and `LIVE_CALLBACKS_ENABLED=0`, then restart the backend. The default `.env.example` remains in simulation mode.

New incidents retain the approximately 15/30/45-second demo sequence, consent/number/opt-out checks, acceptance cancellation and two-attempt limit. Existing expired timers are not backfilled or reset. Incident #3 has used both attempts and will not call again automatically.

## What existed and what changed

The existing ladder already nudged at 15 seconds, proposed a configured on-call owner at 30 seconds, and attempted a consenting resident callback at 45 seconds. It already had an outbound Retell request, simulated answers, signed intake/callback webhooks, report consent, evidence-based risk, assignment history, and a persistent critical review lane.

The callback implementation now commits a durable attempt before dispatch, binds provider results to that attempt, prevents concurrent/duplicate requests, bounds retries, validates E.164 numbers, persists per-report and per-contact opt-outs, recovers simulated results after a lost timer, and preserves uncertain dispatches without redialing. Human acceptance or closure cancels a callback that has not crossed the dispatch boundary. A call already dispatched cannot be undone by acceptance.

The earlier consent display error occurred after persistence: a consenting report without a callable number was shown as having no permission. Consent, phone eligibility, and opt-out are now distinct. Only a validated JSON boolean `true` in `callback_ok` grants permission; transcript text never grants it. Stored opt-outs override later consent on the same number. Fictional seed consent permits simulation only; a live callback requires an eligible Retell intake report.

The dashboard shows eligibility, recorded consent, scheduled times, attempts, calling/completed/failed/cancelled/unknown states, concise condition updates, risk, supervisor review, and the existing responsibility details. Full intake and callback transcripts and raw analysis summaries stay in the reviewer-authorized evidence view. Ordinary callback text is generated from structured outcomes, including protection against older APIs returning an entire conversation in `summary`.

## Verification results

| Check | Result |
| --- | --- |
| Full backend suite | **370 passed**, no failures or XFAILs |
| Live pause/resume regressions | 10 passed, included above |
| Callback-specific lifecycle and migration tests | Included in the full suite |
| Assignment interface checks | 36 passed |
| Readiness interface checks | 12 passed |
| Evidence boundary checks | 7 passed |
| Callback interface/API checks | 14 passed |
| Combined Phase 0/1 API snapshots rendered through React | 48 passed |
| Total frontend scripted checks | **117 passed** |
| TypeScript and Vite production build | Passed |
| Additive migration, repeated on an isolated copy of the existing database | Passed; original report, callback, assignment and event fields preserved |
| Whitespace/diff check | Passed |

There is one dependency deprecation warning concerning Starlette's AnyIO portal alias. Backend tests use an isolated synthetic SQLite database. The frontend checks/build above were verified for the preceding callback implementation; this pause/resume update changes backend control only. Frontend checks execute actual modules with mocked fetch and server-rendered React; they do not certify browser interaction.

Covered scenarios include explicit/declined/missing/invalid consent, invalid or missing numbers, the 15/30/45-second ladder, acknowledgment without acceptance, cancellation before dispatch, concurrent requests, duplicate ticks, authenticated actions, forged callback metadata, duplicate results, worse/same/better, immediate danger, no answer/voicemail/busy/failure, bounded retry, wrong number/DNC, lost timers, missing analysis, ambiguous provider responses, restart recovery, privacy boundaries, and gateway rejection of all dashboard/control paths.

## Retell account verification

A read-only check using the configured credentials verified that the published Callback Agent exists, its `outcome` and `anyone_in_danger` extraction fields are configured, `call_analyzed` is enabled, and its response-engine configuration contains `{{hazard}}` and `{{location}}`.

The previously missing settings are now resolved:

- The configured outbound number has valid E.164 format and exists in the Retell account.
- The published Callback Agent's webhook matches the active HTTPS tunnel to port 8002; the private `PUBLIC_BASE_URL` is synchronized.
- The required `summary`, `callback_opt_out` and `wrong_number` extraction fields are configured using [agents/post_call_fields.json](../agents/post_call_fields.json).
- DNC detection is enabled. A copy of the published agent was updated and published, preserving the existing prompt, voice, webhook and other extraction fields.

The gateway acknowledged a signed non-call probe and rejected public dashboard access. One preceding controlled real call used the configured Callback Agent and its final analyzed result reached the backend. No manual call was requested while enabling automatic mode. Local prompt files alone still do not update Retell; publish future dashboard changes and recheck the tunnel whenever its address changes.

```bash
# From backend/. This only makes configuration GET requests and prints booleans.
PYTHONPATH=. .venv/bin/python scripts/check_retell_callback_config.py --mode automatic
```

The checker returns a nonzero exit status while required settings are missing. It supports `--mode simulate`, `--mode manual-live`, and `--mode automatic`; without an argument it checks the configured mode. Never paste keys, phone numbers, agent prompts containing personal data, or full provider payloads into logs or chat.

## Run locally in simulation

Use separate terminals from the repository root. Stop an existing server on a port before replacing it. These commands preserve existing incidents; do not call `/api/demo/reset` to prepare this test.

```bash
cd backend
CALL_MODE=simulate LIVE_CALLBACKS_ENABLED=0 TIMING_PROFILE=demo LADDER_ENABLED=1 \
  .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --no-access-log
```

```bash
cd backend
CALL_MODE=simulate LIVE_CALLBACKS_ENABLED=0 \
  .venv/bin/python -m uvicorn webhook_gateway:app --host 127.0.0.1 --port 8002 --no-access-log
```

```bash
ngrok http 8002
```

Tunnel only port 8002. Both layers verify signatures; the gateway has one route, `POST /retell/webhook`. Evidence, state, reset, human actions, callback requests and opt-outs remain unavailable through it.

```bash
cd frontend
VITE_API=live VITE_BACKEND_URL=http://127.0.0.1:8001 \
  npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://localhost:5173`. On an eligible unaccepted incident, expand **Authorized callback controls**, enter your name and reviewer key, and choose **Request one simulated callback**. That action skips the wait, uses an eligible stored contact, checks limits, and starts no phone call. The default simulated answer arrives after approximately eight seconds. The separate synthetic outcome demonstration is clearly marked and disabled in live calling mode.

## One controlled live callback — user action only

1. Complete and publish the Retell setup above. Keep the gateway private behind the webhook-only tunnel. Ensure the root `.env` still says `CALL_MODE=simulate` and `LIVE_CALLBACKS_ENABLED=0`.
2. Stop the simulation backend. Start a replacement with **automatic scheduling disabled**:

```bash
cd backend
CALL_MODE=live LIVE_CALLBACKS_ENABLED=0 TIMING_PROFILE=demo LADDER_ENABLED=0 \
  .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --no-access-log
```

3. Call the Intake Agent from your own consenting number and explicitly agree to the AI callback. Check that the signed intake appears on an unaccepted incident with consent granted, a valid stored contact, and an unused attempt. If it links to an existing accepted, closed or attempt-limited incident, it is ineligible; do not reset existing data or use fictional seed permission to bypass this.
4. In that incident's **Authorized callback controls**, enter your reviewer key and name. Check **I confirm one real phone call…**, then press **Place one confirmed live callback** once. This authenticated action dispatches only that incident's attempt; it cannot supply an arbitrary destination or drain other queued contacts. Automatic live calling and automatic retry remain disabled.
5. Answer and report worse/same/better and whether anyone is in danger. Check the correlated result, concise condition summary, preserved responsibility history, and critical review where warranted. A better answer never closes the incident. No answer means conditions unknown, with no evidence-based risk increase.
6. Stop this live backend immediately afterward and restart the simulation command above. Its environment overrides are process-local; the saved `.env` remains in simulation mode. The explicit `LIVE_CALLBACKS_ENABLED=1` gate is reserved for a separately authorized automatic live workflow and is not needed for this one-call test.

Do not repeatedly press the button after a timeout. A provider may have received a request even if its response was lost. Such attempts remain unknown and block redispatch pending a correlated webhook or manual provider reconciliation. A webhook resend for that actual attempt can reconcile it using its stored request identifier.

## State, contracts and security

`Callback` persists scheduling, dispatch state, report reference, attempt number, mode, authorization, per-request idempotency key, timestamps, finite failure codes and restricted evidence. The migration adds columns/indexes and a private contact-preference table without deleting old rows. Existing legacy attempts are never redispatched. Ambiguous duplicate legacy attempts stop migration for review rather than silently removing evidence.

`MAX_CALLBACK_ATTEMPTS` defaults to 2. Confirmed no-answer retries use the existing timing profile's retry interval; ambiguous sends and missing analysis/results block automatic retry. `CALLBACK_RESULT_TIMEOUT_S` defaults to 180. The original ladder deadlines remain in `config.TIMING`; there is no competing escalation timer.

The reviewer-protected `POST /api/incidents/{id}/request-callback` accepts `by` and strict boolean `confirm_live`. `POST /api/reports/{id}/callback-opt-out` records a named action and a validated reason. Acknowledge, accept, close, reassign, synthetic outcomes and evidence also require reviewer authorization. The prototype uses a shared reviewer key; a typed name is an audit label, not a separately authenticated personal account.

The outbound request uses the documented Retell API, a published callback-agent override, metadata `incident_id`/`attempt_no`/`callback_request_id`, dynamic variables `hazard`/`location`, a provider idempotency key and internal DNC enforcement. The signed `call_analyzed` event must match the configured agent and the persisted attempt. Missing analysis never becomes an invented condition answer. Failed-contact reasons override any spurious extracted worsening/danger.

This is a single-worker SQLite demo. Do not run multiple uvicorn workers, a production load test or overlapping backend processes on this database and claim those deployment modes verified. Crash/timeout behavior deliberately favors avoiding duplicate calls. Automatic provider reconciliation, a multi-user identity system, carrier delivery, current tunnel reachability and browser end-to-end operation remain outside these local checks.

Official API references: [outbound calling](https://docs.retellai.com/api-references/create-phone-call), [webhook lifecycle and retries](https://docs.retellai.com/features/webhook-overview), [agent configuration](https://docs.retellai.com/api-references/get-agent).

## Files changed in the final verification pass

- `.env.example`: explicit automation gate, retry/result limits and private reviewer/contact configuration comments.
- `agents/callback.md`, `agents/post_call_fields.json`: opt-out/wrong-number behavior, required extraction fields and publishing instructions.
- `backend/app/models.py`, `backend/app/migrations.py`: distinguish automatic attempts for safe one-call controls and preserve existing rows during additive upgrades.
- `backend/app/engine/callback_jobs.py`, `contact.py`, `ladder.py`, `evidence.py`, `views.py`: dispatch isolation, consent/seed/DNC gates, recovery, missing-analysis handling, failed-contact semantics and safe projections.
- `backend/app/engine/live_control.py`, `backend/tests/test_live_control.py`: private file-based pause/resume switch, startup authorization, fail-closed behavior and due-timer preservation while paused.
- `backend/app/voice/callbacks.py`, `webhooks.py`: published outbound agent version and safe interpretation of failed contact.
- `backend/app/api/routes.py`: dispatch only the explicitly requested attempt and block synthetic outcomes in live mode.
- `backend/scripts/check_retell_callback_config.py`: read-only remote configuration checker with no secret output.
- `backend/tests/test_automatic_callbacks.py`, `test_callback_migration.py`: new lifecycle, privacy, authorization, concurrency, restart and migration regressions.
- `backend/tests/conftest.py`, `test_failure_scenarios.py`, `test_phase01_acceptance.py`, `test_readiness.py`, `test_retell_evidence.py`, `test_webhook_gateway.py`: model a genuine persisted dispatch, assert ambiguous timeout semantics, and cover new gateway exclusions.
- `frontend/src/components/CallbackPanel.tsx`, `IncidentDetail.tsx`, `EvidenceReview.tsx`, `frontend/src/styles.css`: callback controls/status, protected callback transcripts and readable live confirmation.
- `frontend/scripts/check-callbacks.cjs`, `check-accountability.cjs`: callback rendering/actions and authenticated named-human actions.
- `README.md` and this document: readiness, reproduction commands, account blockers and one-call procedure.

Earlier portions of the callback implementation on the branch also updated configuration, startup/recovery, database initialization, Python/TypeScript contracts and authenticated assignment API helpers. Existing API field names and assignment records are preserved.

To reproduce the complete checks:

```bash
# backend/
HANDOFFPROOF_INTEGRATION_SNAPSHOTS=/private/tmp/handoffproof-callback-snapshots \
  .venv/bin/python -m pytest -q

# frontend/
node scripts/check-accountability.cjs
node scripts/check-readiness.cjs
node scripts/check-evidence.cjs
node scripts/check-callbacks.cjs
node scripts/check-phase01-integration.cjs /private/tmp/handoffproof-callback-snapshots
npm run build
```
