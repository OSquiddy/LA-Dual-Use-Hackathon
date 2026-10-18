# Phase 1 handoff

Local Phase 1 work is underway on branch `backend`. This is a status record, not a claim of completed live Retell integration. All local calls stay simulated. Existing uncommitted work was preserved; no branch switch, commit, push, shared-schema change, or public tunnel was performed.

## Verified local milestone

`tests/test_phase1_sync.py` uses a synthetic, fictional 555-number fixture and a test-only signing key:

1. Reset storm night: one incident, three distinct report records.
2. Deliver an authenticated synthetic `call_analyzed` intake using spoken “Avenue fifty two.”
3. Confirm one incident, four retained reports, audit source references, persisted consent, and a masked phone in the response.
4. Repeat delivery: no duplicate evidence or report.
5. In separate cases, prove true consent permits follow-up and missing/false consent prevents it.

The synthetic fixture is `tests/fixtures/synthetic_retell_intake.json`. It is not Person A's required redacted provider fixture.

## Person B — B1 through B6

| Task | Local status |
| --- | --- |
| B1 Shared consent, acknowledgment, evidence models | Already implemented on this branch; unchanged in this pass |
| B2 Preserve source reports through seed intake | Implemented and verified |
| B3 Geocoding, spoken numbers, unresolved-location debt | Implemented and verified |
| B4 Spatial/time/hazard linking; preserve original sources | Implemented and verified, including boundary tests |
| B5 Evidence risk separate from operational uncertainty | Implemented and verified; bounded English negation rules |
| B6 State/detail responses; one incident/three seed reports | Implemented; signed fourth-intake acceptance check added |

## Person C — C1 through C6

- Department/supervisor/detail layout and uncapped critical-alert lane are implemented.
- Fixture/live API switch and polling are implemented. Fixture mode reads static examples and skips writes; it does not demonstrate a working engine.
- Cards now include hazard indicators and explicit assigned/acknowledged/accepted labels without treating a proposed owner as acceptance.
- Detail shows all reports, location/hazard/transcript, extracted danger phrases, callback permission, and event actor/evidence references. An incident-fetch failure now shows a retry message instead of an indefinite silent loading state.
- Status uses text as well as color. Actual accessibility interaction and projector readability still need Person C's browser check.
- Loading, main-screen outage, empty state, and critical-alert server-render checks pass; build passes. Browser recovery/click behavior and target projector resolution are not certified by server rendering.
- Explicit acknowledgment controls and choosing the accepting person remain C7 work in Phase 2; existing generic-desk Accept behavior is not presented as finished C7.

## Person A — A1 through A6

- Keep the existing demo-labelled prompt and five intake extraction fields, including callback permission.
- Webhook raw-body signature verification, validation, consent mapping, and duplicate-ingestion protection are implemented and tested with synthetic signatures.
- A2/A4/A5/A6 still require account-side verification: agent fields, authorized number/credit, actual provider payload/signature, an opted-in test call, and a redacted real fixture.
- Coordinate the first real test through the existing team workflow. Do not paste API keys, phone numbers or original transcripts into this report/chat.
- Use the account's webhook-capable API key; local test signing does not prove the actual provider key or payload is correct.

## Validation for this pass

- Backend: **135 passed**, zero failures/skips/XFAILs; one existing dependency deprecation warning.
- Frontend: `npm run build` **PASS**; `node scripts/check-readiness.cjs` **11 PASS**.
- No new dependencies or API shapes introduced.

From backend:

```sh
CALL_MODE=simulate .venv/bin/python -m pytest -q
CALL_MODE=simulate .venv/bin/python -m pytest -q tests/test_phase1_sync.py
```

From frontend:

```sh
npm run build
node scripts/check-readiness.cjs
```

Local dashboard previously verified at http://localhost:5174/ with backend http://localhost:8001/. These port choices are local; teammates must configure their own frontend backend URL.

## Sync 1 still requiring the team

Person C uses live API mode against Person B's server; Person A validates a consent-aware authenticated intake. Local simulation has passed the source-preservation test. A real cross-computer/provider run and projector/browser inspection remain outstanding. Each developer should verify the reviewed code on their own machine before claiming that team Sync 1 passed.

## Latest combined Phase 0/1 run

The expanded suite now passes **147 backend tests**, **48 API-to-React rendering cases**, **11 frontend state checks**, both fixture/live builds, and the previous supplemental matrices. See [PHASE01_TEST_REPORT.md](PHASE01_TEST_REPORT.md) for the scenario coverage and remaining manual/external gates.
