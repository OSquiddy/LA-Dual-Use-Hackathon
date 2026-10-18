# Assignment and accountability

Department, individual, assignment status, acknowledgment, acceptance and available timestamps now share one responsibility panel in department cards, supervisor cards, Critical Review and incident detail. Times are displayed explicitly in America/Los_Angeles. The configured roster is labeled as fictional demonstration personnel throughout.

## From a report to accepted responsibility

1. `ingest._new_incident()` uses `config.HAZARD_DEPARTMENT[incident.hazard_type]` to create a department assignment. Water/road reports route to Street Services, downed trees to Urban Forestry, and power hazards to Power & Water. The configured `other` fallback is retained. No person is assigned or accepted by report creation.
2. The existing ladder nudges an unaccepted department, then looks up its area-specific contact in `seeds/oncall.json`. Automatic assignment uses only that department's configured contact. Missing department/area entries remain visibly unassigned; no fallback person is invented. An existing explicit individual assignment is not overwritten by the automatic step.
3. An operator explicitly records acknowledgment under an entered name. Its timestamp and actor belong to that assignment. Receipt does not accept responsibility or stop the ladder.
4. An operator explicitly accepts responsibility under an entered name. `accepted_at` and `accepted_by` are persisted, the no-owner debt is cleared, and the ladder stops. If a different named human takes responsibility, a new assignment row records that takeover and retains the former roster assignment. This is an explicit human action, not an automatically invented roster entry. Acceptance does not fabricate an acknowledgment.
5. An authorized reviewer may explicitly reassign a case, supplying the existing reviewer key, a name and a reason. Department/person options come from the backend; a selected individual must match that department's configured roster for the incident's area. Department-only assignment is supported when a contact is unknown. A department override is a recorded human routing decision; the UI shows the hazard-based recommendation.
6. Reassignment retains the previous row, including its acknowledgment and acceptance. The new row starts without either action. The ladder resumes; critical cases remain critical and their new responsibility is immediately visible. Reassignment changes no reports, consent or physical-risk score.
7. Closure displays the existing recorded human name/time. Repeated close requests preserve the first closure record, and closed cases cannot be reassigned. The engine never closes a case automatically.

## What each state means

| Display | Recorded basis |
| --- | --- |
| Awaiting department assignment | No current department assignment |
| Department assigned · individual not assigned | Department present; no individual or receipt action |
| Individual assigned · awaiting acknowledgment | Individual present; no acknowledgment/acceptance timestamp |
| Acknowledged · awaiting acceptance | Actual acknowledgment timestamp; no acceptance timestamp |
| Accepted by a named individual | Actual acceptance timestamp and recorded accepting person |
| Closed by a named human | Existing incident closure metadata |

Acknowledgment and acceptance are also shown as independent fields, including their actors/times. A closed case may legitimately have no prior acknowledgment or acceptance; neither is inferred. Legacy names, timestamps or assigning actors that were never recorded are labeled as missing, not reconstructed.

## Data and API changes

No SQLModel/schema migration or database reset is required. The existing `Assignment` table stores successive responsibility rows; the existing append-only `Event` table records who changed responsibility and why, with `assignment:<id>` references. Initial assignment, roster assignment, reassignment, acknowledgment, acceptance and closure have audit references.

Approved additive contract changes:

- Every `IncidentView` includes `assignment`, `closed_at`, and `closed_by`, with defaults for older clients/fixtures.
- `AssignmentView` adds the existing row `id` and event-derived `assigned_by`/`change_reason`.
- Incident detail includes `assignment_history[]` in recorded order. The latest row is the current assignment in both state and detail.
- `GET /api/incidents/{id}/assignment-options` returns the hazard-based recommendation and configured department/area roster choices. React contains no hardcoded staff or department names.
- `POST /api/incidents/{id}/reassign` requires `Authorization: Bearer <reviewer-key>` and accepts `{department, owner, by, reason, expected_assignment_id?}`. Missing/invalid authorization returns 401 before incident lookup; a missing/blank server key returns 503. Unknown departments or mismatched roster contacts return 422; closed cases and stale assignment IDs return 409. Putting a key in the body does not grant authorization.
- Existing acknowledge/accept requests accept optional `expected_assignment_id`; the dashboard sends it. Actions against a stale assignment are rejected before mutation. Human transitions and ladder assignments are serialized within the existing single-worker local architecture.

Department metrics count distinct incident/department pairs rather than assignment-history rows. Recording a new owner cannot manufacture a silent-department alert by inflating the assigned count.

Historical rows/events already present are preserved. Older code mutated the current assignment in place; details lost before this change cannot be recovered. Those existing rows and events remain visible, while new responsibility changes retain prior rows. No bulk backfill or rewriting of existing incidents was performed.

## Using the interface

Choose **Review incident** or **Review incident evidence** to open detail. The department-card **Accept** control opens that drawer; it no longer records a generic department desk as the accepting person.

Under **Record a human action**, enter the person's name and choose **Record acknowledgment** or **Accept responsibility**. The dashboard waits for server confirmation and displays errors without optimistic acceptance. Under **Assign or reassign responsibility**, explicitly choose the department and individual (or department-only assignment), enter a reason and the reviewer authorization key, and save. Identical assignments are not presented as a new handoff.

Reassignment and raw incident evidence require the existing separate `REVIEWER_API_KEY`, privately configured in the repository-root `.env`. Restart the backend after changing it. Never use the Retell signing key, a URL query parameter, or a `VITE_*` setting for this credential. The UI sends it only in the authorization header, keeps it only in the open component's memory, and clears it after each reassignment attempt and assignment change. It is not persisted to assignments, events, browser storage or application logs.

This is shared reviewer authorization for the local prototype. The entered actor name is an audit label; the shared key does not establish an individual account identity or City of Los Angeles authority. Acknowledgment, acceptance and closure retain the existing trusted local-operator model; the new authorization requirement specifically protects the reassignment endpoint. Per-user identity/roles remain a separate deployment concern. Keep the main API private and expose only the webhook gateway.

After editing roster contacts, restart the backend to refresh its existing roster cache. Retell signatures, event mapping, consent, gateway isolation and outbound-call configuration are unchanged by this task. Keep `CALL_MODE=simulate` and tunnel only the webhook gateway.

## Verification

- **294 backend tests passed**, including authorized/denied reassignment, roster validation, stale forms, immutable prior audit events and gateway isolation. One existing Starlette/AnyIO deprecation warning remains.
- **Frontend production build passed** (`npm run build`).
- **103 frontend rendering/API checks passed**: 36 accountability checks, 12 readiness checks, 7 evidence checks and 48 backend-exported handoff snapshots. These are static rendering, mocked-fetch and action-handler checks, not an interactive browser certification.
- Earlier read-only ASGI requests confirmed consistent current assignment metadata, available history and transcript redaction in the existing demo database. The latest unauthenticated reassignment probe returned **401** with the local reviewer key configured. Hashes confirmed that report, assignment and event records were unchanged by that denied request. No real authorized reassignment was performed against existing data; successful writes were tested only in the isolated synthetic test database.
- `CALL_MODE=simulate` was confirmed. No real outbound calls, commits or pushes were performed.

Reproduce from `backend/`:

```sh
HANDOFFPROOF_INTEGRATION_SNAPSHOTS=/private/tmp/handoffproof-accountability-snapshots .venv/bin/python -m pytest -q
```

From `frontend/`:

```sh
npm run build
node scripts/check-accountability.cjs
node scripts/check-readiness.cjs
node scripts/check-evidence.cjs
node scripts/check-phase01-integration.cjs /private/tmp/handoffproof-accountability-snapshots
```

Backend tests use the isolated test database and synthetic names/data, not the existing live demo database.

## Files changed for this task

Earlier uncommitted webhook/evidence work was preserved. This task changed the following files:

| Files | Purpose |
| --- | --- |
| `backend/app/contracts.py`, `frontend/src/types.ts` | Approved current assignment/history/closure contracts and guarded human action requests. |
| `backend/app/engine/assignments.py` | Retain previous assignment rows; record transitions and source references. |
| `backend/app/engine/ingest.py`, `ladder.py` | Route initial assignments through the history-preserving helper; record actual human actions; protect closure records. |
| `backend/app/engine/oncall.py`, `backend/seeds/oncall.json` | Backend-derived roster options, safe missing-contact behavior, explicit fictional roster note. Staff entries were not changed. |
| `backend/app/engine/views.py`, `silence.py` | Project current/history metadata and avoid counting history rows as separate incidents. |
| `backend/app/api/routes.py` | Authorized and validated reassignment/options routes and stale assignment guards; reuse existing reviewer authorization. |
| `backend/tests/test_assignment_accountability.py`, `test_failure_scenarios.py`, `test_webhook_gateway.py` | Lifecycle/routing/history/concurrency and authorization tests; immutable previous audit records; gateway isolation; distinct-incident department threshold. |
| `frontend/src/components/AssignmentSummary.tsx`, `AssignmentActions.tsx`, `AssignmentHistory.tsx` | Reusable responsibility display, named actions and auditable history. |
| `frontend/src/components/IncidentCard.tsx`, `DepartmentQueue.tsx`, `CriticalAlerts.tsx`, `IncidentDetail.tsx` | Use the common responsibility display across all requested views; replace desk acceptance with an explicit named action. |
| `frontend/src/api.ts`, `styles.css` | Action/options API functions and readable, responsive responsibility styles. |
| `frontend/src/fixtures/state.json`, `incident.json` | Matching fictional assignment metadata and history. |
| `frontend/scripts/check-accountability.cjs`, `check-readiness.cjs` | Six-state/four-view regression checks, human action confirmation/failure checks and updated existing assertions. |
| `README.md`, `backend/ASSIGNMENT_ACCOUNTABILITY.md`, `backend/EVIDENCE_REVIEW.md` | Feature behavior, reviewer authorization setup, limits, complete change list and verified results. |
