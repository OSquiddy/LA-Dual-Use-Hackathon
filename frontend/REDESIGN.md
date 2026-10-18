# Operations workspace and responsibility redesign

The dashboard now uses a navy navigation rail, a light operations workspace, four backend-derived metrics, compact incident cards, an independent persistent Critical Review panel, a ranked supervisor attention list, and department workloads. Functional views cover Operations Dashboard, Incidents, Departments, Assignment History, and Critical Review. Demo controls are separate. Prototype and fictional-roster disclosures remain visible.

Incident search covers title/location, ID, responsible department, unit, person and role. Filters cover department, priority and ownership; sort uses physical risk, oldest creation, or latest backend audit update. Missing historical timestamps display “Not recorded.” Acceptance uses the current assignment's actual acceptance timestamp. It neither implies acknowledgment nor marks a hazard safe. Critical flags remain visible beyond the top ten and after acceptance.

Incident detail provides Overview, Responsibility, Assignment History, Follow-up and Evidence anchors. It preserves existing authorized human actions, reassignment and callback controls. Opening a drawer writes nothing. Reviewer keys remain in memory and go only in the Authorization header. Full transcripts appear only after reviewer authorization, can be locked again, and are cleared when the drawer closes. Call consent remains per report. Modal Escape, focus containment/restoration, keyboard navigation, loading, empty, outage and action-error states are supported.

## Official logo and Higgsfield

The supplied image was imported at the requested `public/assets/handoffproof-logo.png` path. The complete artwork and taglines appear on a light surface; click to enlarge. The source WEBP is preserved. A pixel-preserving cropped SVG supplies the compact mark/favicon. See [brandkit/Brand-Lock.md](brandkit/Brand-Lock.md).

Higgsfield CLI and skills were available, but the account-readiness check failed. No assets were generated or uploaded. The fallback uses the supplied official logo, CSS and small source-controlled SVG interface icons.

## Configured directory and routing

Official parent naming was checked against the [City department directory](https://lacity.gov/government/departments-bureaus), [LA Sanitation watershed program](https://sanitation.lacity.gov/programs/watershed-protection), and [LADWP Power System](https://www.ladwp.com/who-we-are/power-system). Units, coverage rules, routing decisions and all people below are demonstration configuration, not official dispatch policy or city employee records.

| Routing key | Parent department / bureau | Fictional operational unit | Fictional configured staff |
| --- | --- | --- | --- |
| Stormwater Operations | Public Works — LA Sanitation & Environment | Stormwater & Drainage Response | Elena Morales — Stormwater Operations Coordinator; Daniel Park — Drainage Response Specialist |
| Street Services | Public Works — Bureau of Street Services | Roadway Maintenance & Obstructions | Jordan Ramirez — Roadway Maintenance Coordinator; Maya Chen — Street Operations Supervisor |
| Traffic Operations | Los Angeles Department of Transportation | Traffic & Roadway Coordination | Marcus Lee — Traffic Operations Coordinator; Sofia Bennett — Roadway Incident Specialist |
| Urban Forestry | Public Works — Bureau of Street Services | Urban Forestry Response | Olivia Torres — Urban Forestry Coordinator; Ethan Brooks — Field Operations Specialist |
| Power & Water | Los Angeles Department of Water and Power | Electrical & Utility Coordination | Alex Rivera — Electrical Response Coordinator; Priya Shah — Utility Operations Specialist |

`backend/app/config.py` routes flooding/drains/road water to Stormwater, potholes/debris/other to Street Services, stalled vehicles to Traffic, trees to Urban Forestry, and lines/outages to Power & Water. Existing danger detection/escalation remains unchanged. Linked incidents retain their primary accountable assignment; changing aggregate hazards does not silently transfer human responsibility. Supporting departments are not modeled.

`backend/seeds/oncall.json` owns unit labels, profiles, on-call flags and department/area lists. The ladder keeps initial department routing and its existing nudge/default-owner timing. At the default-owner step it filters the department's configured coverage and available staff, then selects `(incident_id - 1) % eligible_staff_count`. Repeated reads never rotate people. This distributes demonstration cases deterministically; it is not shift scheduling or workload balancing. An explicit `*` coverage entry provides a configured citywide demonstration fallback for unknown areas without guessing a geographic location. Without coverage or available contacts, the case remains unassigned. Critical cases that bypass the normal ladder can still require an authorized individual assignment; no receipt or acceptance is invented.

New assignment rows snapshot department display name, unit, staff ID/name/role and coverage. Existing assignment rows are untouched. Historical missing metadata remains labeled as missing; records are not rewritten from the new directory. Explicit future reassignment creates a new snapshot and retains prior assignments and events. Human acceptance under a different entered name records that takeover without inventing a staff role.

## Additive storage and API changes

- Nullable `Assignment.responsibility_profile` JSON column, added idempotently to the recognized existing schema. No reset, destructive migration or historical backfill.
- Optional/defaulted assignment metadata in Python/TypeScript contracts; created/update timestamps, priority and callback lifecycle state on incidents.
- Departments expose configured staff, parent display name, unit, active workload and pending acceptance, including empty departments.
- `GET /api/assignment-history?limit=30&before_id=<id>` returns bounded pages across active and closed incidents, newest assignment first. Limits are validated from 1–100. Current-assignment detail still includes the complete per-incident history. The route returns no transcripts, phone numbers or credentials. It stays private behind the main API; the webhook gateway is unchanged.
- State exposes nonsecret call mode and automatic-dispatch status. Existing authorized live calling was left as configured; tests force simulation and stub provider calls.

## Run and verify

From the repository root, start the backend without loading any demonstration seed:

```sh
cd backend
CALL_MODE=simulate LIVE_CALLBACKS_ENABLED=0 .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --no-access-log
```

This command intentionally starts a simulation process. If an authorized live server already owns port 8001, do not launch a second server; use its existing process and pause/resume procedure in `backend/AUTOMATIC_CALLBACKS.md`.

In another terminal:

```sh
cd frontend
npm install
# Preserve an existing private frontend configuration.
test -f .env.local || cp .env.example .env.local
npm run dev -- --port 5173 --strictPort
```

Open http://127.0.0.1:5173. The Vite proxy defaults to private backend port 8001. Explicit `VITE_API=fixture` remains available for the legacy contract fixtures; new setup defaults to live API integration. Both frontend run commands bind to loopback.

Backend checks, from `backend/`:

```sh
HANDOFFPROOF_INTEGRATION_SNAPSHOTS=/private/tmp/handoffproof-redesign-integration .venv/bin/python -m pytest -q
```

Frontend checks, from `frontend/`:

```sh
npm run build
npm run test:regression
node scripts/check-phase01-integration.cjs /private/tmp/handoffproof-redesign-integration
npx playwright install chromium
npm run test:e2e
```

Playwright starts Vite on loopback port 5180 and intercepts **every** `/api/` request. Its synthetic fixture comes from isolated pytest and contains no resident records or credentials. It cannot reach the real API, reset the real database or place calls. Screenshots are saved to ignored `artifacts/redesign/operations-1440.png` and `operations-1920.png`. Additional tablet checks cover 1024 and 768 pixels. Browser output is ignored by Git.

## Verification and limits

See the final verification record below for exact run results. Current scope is a local municipal operations prototype: reviewer authorization is a shared key with entered audit names, not individual employee authentication. Existing missing role/unit metadata cannot be recovered automatically. No real-provider calls, signature deliveries, or city-system integrations are certified by mocked UI tests. No load, multi-worker database, Safari or full accessibility audit is claimed. The existing Starlette/AnyIO dependency deprecation warning remains. No commit or push was performed.

## Final verification record

Local run on October 17, 2026:

| Check | Result |
| --- | --- |
| Full backend pytest | **377 passed**, no failures or skips; one existing Starlette/AnyIO deprecation warning |
| New backend directory/selection/snapshot/legacy/migration/history checks | **7 passed**, included in the 377 |
| Frontend TypeScript + Vite production build | **PASS** |
| Accountability rendering/action checks | **36 passed** |
| Evidence rendering/API checks | **7 passed** |
| Dashboard readiness checks | **12 passed** |
| Callback rendering/action checks | **14 passed** |
| Combined Phase 0/1 backend-exported frontend snapshots | **48 passed** |
| Chromium interactions and responsive layouts | **16 passed**, including 1440/1920 desktop and 1024/768 tablet |
| Running private backend contract | HTTP **200**, five configured departments and additive assignment fields present |
| Running dashboard and its `/api/state` proxy on port 5173 | Both HTTP **200** |
| Original database records | All baseline report/assignment/event/callback hashes still match over their original columns; new records appeared during development and were retained |

Chromium coverage includes filters/metrics, timestamp sorting, department/staff inspection, global history/pagination, drawer close, reviewer evidence unlock/relock, authorized acknowledgment/acceptance/reassignment, rejected authorization, uncapped critical alerts, live-mode reset disabled, outage state, and full-logo proportions/focus restoration. Provider calls are stubbed and browser APIs are entirely intercepted. Neither test suite resets the resident database or initiates a real provider call. The running application retained its previously authorized live-calling configuration.

The npm dependency installation reported two pre-existing dependency audit advisories (one moderate, one high) in the Vite toolchain. A forced major dependency upgrade was not applied during this product change; use this loopback-bound development setup and address dependency upgrades separately before deployment.

## Files changed in this redesign

Earlier uncommitted Retell/callback/security work remains intact. This list describes the current redesign, not every pre-existing working-tree change.

| Files | Change |
| --- | --- |
| `src/App.tsx`, `src/styles.css`, `src/workspace.ts` | Live navigation/workspace, four metrics, state-accurate search/filter/sort and responsive design |
| `src/components/Icon.tsx`, `BrandDialog.tsx` | Editable SVG UI icons and accessible complete-logo view |
| `src/components/DepartmentDirectory.tsx` | Backend-derived department, unit, staff and current responsibility inspection |
| `src/components/HistoryWorkspace.tsx`, `SupervisorReviewList.tsx` | Paginated audit history and compact backend-ranked supervisor list |
| `src/components/AssignmentSummary.tsx`, `AssignmentHistory.tsx`, `IncidentCard.tsx`, `CriticalAlerts.tsx` | Department/unit/person/role/times, distinct receipt/acceptance, concise evidence, pending critical action |
| `src/components/IncidentDetail.tsx`, `TwistPanel.tsx` | Sectioned drawer, modal keyboard behavior and separate demo controls with live reset disabled |
| `src/api.ts`, `src/types.ts` | Additive history API and typed assignment/directory/time/priority/callback metadata |
| `index.html`, `public/assets/handoffproof-logo-original.webp`, `handoffproof-logo.png`, `handoffproof-mark.svg` | Preserved official artwork, PNG integration and cropped favicon/navigation mark |
| `.env.example`, `vite.config.ts`, `package.json`, `package-lock.json` | Live frontend/backend port 8001 defaults, loopback dev/preview, Playwright and test scripts |
| `playwright.config.ts`, `tests/redesign.spec.ts`, `tests/fixtures/operations.json`, `.gitignore` | Isolated browser regression suite, synthetic API fixture and ignored output artifacts |
| `scripts/check-phase01-integration.cjs` | Preserve real initial values of newly added App state during synthetic SSR checks |
| `brandkit/official-logo.json`, `brandkit/Brand-Lock.md`, `brandkit/.gitignore`, `REDESIGN.md` | Brand provenance/locked input and implementation report; generated local `state.json` is ignored |
| `../backend/seeds/oncall.json`, `../backend/app/config.py`, `engine/oncall.py` | Five service routing groups, ten fictional staff, units/availability/area coverage and stable selection |
| `../backend/app/models.py`, `migrations.py`, `db.py`, `engine/assignments.py` | Nullable assignment-profile snapshot and non-destructive migration; new handoffs preserve their recorded metadata |
| `../backend/app/engine/ladder.py`, `silence.py`, `views.py` | Incident-aware roster selection, directory/workload metrics, safe enriched projections and call-mode status |
| `../backend/app/contracts.py`, `api/routes.py` | Additive response contracts and bounded global assignment-history endpoint |
| `../backend/tests/test_redesign_accountability.py` | New directory, availability, profile immutability, legacy compatibility, migration, history and synthetic export tests |
| `../backend/tests/test_assignment_accountability.py`, `test_engine.py`, `test_failure_scenarios.py`, `test_smoke.py` | Update existing routing expectations; verify explicit citywide fallback and missing-coverage behavior without weakening authorization checks |
| `../README.md`, `../backend/ASSIGNMENT_ACCOUNTABILITY.md` | Current implementation/startup links and identification of superseded earlier roster/migration notes |
