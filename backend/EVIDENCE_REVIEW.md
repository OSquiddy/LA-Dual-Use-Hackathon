# Retell evidence and reviewer access

The Critical Review panel shows a source-grounded assessment, risk, assignment, acknowledgment and acceptance. It links to the incident drawer. Full conversations require a separate reviewer unlock inside that drawer.

## Root causes

Intake originally copied `ReportIn.transcript` → `Report.transcript` → `Incident.critical_quote`; `supervisor.critical_alerts()` returned that quote and `frontend/src/components/CriticalAlerts.tsx` rendered it in a blockquote. Callback summaries were also copied into alert quotes and audit-event reasons.

The affected real report already had `Report.callback_ok=true`, with no phone number. `ladder.callback_target()` correctly could not call it, but `refresh_consent_debt()` incorrectly treated every unavailable target as missing permission. A Retell web call need not supply `from_number`. The five configured extraction fields include consent, not a callback number.

## Evidence boundary

- `GET /api/state`: finite critical reasons, empty legacy `quote`, source IDs, no transcripts.
- `GET /api/incidents/{id}` and simulation responses: existing response shape, `reports[].transcript=""`, safe callback descriptions and event reasons. Report consent remains visible.
- `GET /api/incidents/{id}/evidence`: same response shape, full report transcripts and original callback summaries, after reviewer authorization. Responses use `Cache-Control: no-store`.
- Missing/wrong reviewer credentials: **401** when configured; missing server key: **503**, denying access. Authorization runs before incident lookup.
- The webhook-only gateway does not expose this endpoint. Keep both local servers bound to `127.0.0.1` and tunnel only port 8002.

Configure a **separate strong random** `REVIEWER_API_KEY` in the repository-root `.env`, privately, and restart the backend. Do not reuse the Retell signing key, put this key in a `VITE_*` variable, send it in URLs, or commit it. The example configuration documents the setting but intentionally leaves it empty. No local credential is generated or changed by this implementation.

Start the backend from `backend/`:

```sh
CALL_MODE=simulate .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001 --no-access-log
```

Open an incident with **Review incident evidence**, enter the reviewer key in the password field, then choose **Unlock incident evidence**. The key is sent only in an Authorization header and cleared from the input after the request. Evidence stays in component memory until locked or the drawer closes; it is not written to browser storage. Unlock again to fetch newly arrived evidence. Fixture mode contains fictional bundled data and requires no key.

This is a shared reviewer secret for the local prototype, not individual accounts or role administration. It also authorizes the reassignment endpoint and its password field in the incident drawer; see [assignment accountability](ASSIGNMENT_ACCOUNTABILITY.md). Keep the main API private; acknowledgment, acceptance and closure still use the existing local trust model. A public/multi-user deployment needs a coordinated identity and authorization system.

## Summary and consent rules

Summaries select from finite descriptions using structured hazard/outcome data and supported caller statements. Agent questions do not establish danger. Descriptions retain “possible,” “reported” and “unverified”; ambiguous danger remains explicitly unconfirmed. Callback outcome summaries use validated outcome/danger fields, never unbounded free text. The UI also rejects conversation-shaped legacy alert reasons rather than displaying excerpts.

Only the validated Retell extraction `custom_analysis_data.callback_ok` with JSON boolean **true** grants callback permission. False, missing, null, strings and numbers grant none. Transcript wording never supplies consent. That value passes through `ReportIn` unchanged into each report's existing database field. It is not inherited by other reports.

Consent plus no usable number produces `callback_number_missing`, not `consent_unknown`. The ladder does not place that callback. A reachable, consenting older report may be selected over a later non-consenting report. Missing contact information adds no risk points and proves neither safety nor deterioration.

## Existing data

No database reset or schema migration is required. Original report transcripts, callback source summaries, consent and historical audit rows remain stored. Legacy alert quotes/event reasons and incorrect contact debts are safely projected for the dashboard without rewriting those records. New alerts store source references rather than duplicate transcripts. Older data is not reinterpreted to grant permission.

The existing callback model stores its source summary, not a full callback transcript. This change preserves the full intake transcript already stored per report; adding callback transcript storage would require a separately coordinated schema migration. No missing historical evidence can be reconstructed by this change.

## Verification

From `backend/`:

```sh
CALL_MODE=simulate .venv/bin/python -m pytest -q
```

From `frontend/`:

```sh
npm run build
node scripts/check-readiness.cjs
node scripts/check-evidence.cjs
```

Tests use synthetic keys/data and an isolated test database. They verify full transcript preservation, bounded summaries, caller versus agent evidence, uncertainty, strict consent, missing numbers, legacy projection, authenticated evidence retrieval and gateway isolation. Rendering and mocked-fetch checks do not constitute an interactive browser or a new genuine Retell delivery test. No real outbound call is needed or initiated.

Evidence-only implementation verification: **252 backend tests passed**, with one existing Starlette/AnyIO deprecation warning. `npm run build` passed. All **67 frontend checks** passed: 12 readiness rendering checks, 7 evidence rendering/mocked-fetch checks, and 48 rendered handoff-stage snapshots exported by the backend acceptance tests. `git diff --check` passed. See [assignment accountability](ASSIGNMENT_ACCOUNTABILITY.md) for current results after the assignment authorization additions.

At that evidence-only verification, read-only HTTP checks after restarting the backend confirmed `CALL_MODE=simulate`, empty critical quotes, bounded critical reasons, redacted ordinary transcripts, and zero incorrect no-permission labels for the consented report lacking a number. Both reports then present retained their stored transcripts. The local reviewer key was unset at that time, so evidence access correctly returned **503**; successful/denied reviewer authorization was verified with synthetic keys in tests. Local configuration has since changed; the latest assignment report records the current authorization check without exposing credentials.

## Files changed for this task

Earlier uncommitted webhook/gateway and uniqueness work was preserved. This task changed:

| Files | Purpose |
| --- | --- |
| `backend/app/engine/evidence.py`, `source_text.py`, `risk.py` | Generate finite source-grounded summaries; separate caller evidence from agent questions; sanitize legacy projections. |
| `backend/app/engine/critical.py`, `ingest.py`, `ladder.py` | Stop copying conversations into alerts/events; distinguish consent from a missing callback number; preserve source evidence. |
| `backend/app/engine/supervisor.py`, `views.py` | Redact ordinary responses, project safe summaries and corrected contact debts without rewriting existing rows. |
| `backend/app/api/routes.py`, `backend/app/config.py`, `.env.example` | Approved reviewer endpoint/configuration, authorization, no-store evidence responses. No schema or shared response-field changes. |
| `frontend/src/App.tsx`, `api.ts`, `components/CriticalAlerts.tsx`, `components/IncidentDetail.tsx`, `components/EvidenceReview.tsx`, `styles.css` | Concise review panel with risk and accountability; explicit protected evidence unlock; remove inline raw conversations. |
| `backend/tests/test_retell_evidence.py`, `test_engine.py`, `test_readiness.py`, `test_webhook_gateway.py` | Regression coverage and revised summary expectations; wait for the complete asynchronous simulator result; verify public evidence route isolation. |
| `frontend/scripts/check-readiness.cjs`, `check-evidence.cjs`, `check-phase01-integration.cjs` | Verify summary/evidence boundaries, locked/unlocked rendering, reviewer API failures, and combined handoff rendering. |
| `README.md`, `backend/EVIDENCE_REVIEW.md` | Reviewer setup, root causes, contract behavior, limits and verified results. |
