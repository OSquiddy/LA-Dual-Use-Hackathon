> Latest result: the deeper failures are now fixed. All 131 backend tests and 8 frontend rendering checks pass. See [PHASE0_READINESS_REPORT.md](PHASE0_READINESS_REPORT.md). The results below describe the earlier test matrix.

# Failure scenario report — fixes verified

Branch: `backend`. All local tests use `CALL_MODE=simulate` and temporary test databases; no real calls.

## Results

| Check | Result |
| --- | --- |
| Backend pytest (50 existing + 39 new regression cases) | **89 PASS, 0 FAIL, 0 XFAIL** |
| Updated backend scenario matrix | **52 PASS, 0 FAIL** |
| Frontend API checks with mocked fetch | **7 PASS, 0 FAIL** |
| Frontend TypeScript and Vite production build | **PASS** |
| git diff --check | **PASS** |

One existing Starlette/AnyIO deprecation warning remains. No test was skipped or marked XFAIL to obtain these results. These suites overlap; their counts are not distinct product requirements.

## Fixes

- Blank/whitespace human identities are rejected at the API boundary for acknowledge, accept and close; valid names are trimmed. Shared contracts remain unchanged.
- Every seed row is parsed and validated before demo data is erased. Gazetteer/oncall files, malformed rows, duplicate IDs and invalid seed names are rejected. Validated rows are reused for ingestion rather than rereading the file after reset.
- Retell signature checks authenticate original request bytes plus the provider timestamp; missing/invalid keys, expired/future signatures and tampered bodies fail closed with 401. Authenticated malformed payloads receive a generic 422 without echoing sensitive content.
- Department silence produces one operational alert per affected department and suppresses redundant nudges. Critical incident alerts remain visible.
- Surge ingests 50 fictional source reports in four synthetic clusters, preserves the original storm, and avoids duplicate ingestion on repeated toggles.
- Unsupported domains receive 404 without changing state. Only the implemented storm domain is accepted.
- Phones-down records no_answer without making an outbound request, raising physical danger solely for silence, or closing a case.

## Scenario harness corrections

Valid webhook tests now send synthetic signed payloads; the unsigned negative test remains unsigned. The three outdated assertions were corrected: baseline risk comes from the current linked storm (70), unknown-location incidents are found by their data rather than hardcoded ID 4, and the low-risk test creates an actual pothole instead of treating the storm as low risk. The worse test also requires a rise above the current baseline.

## All 52 backend scenarios

| Scenario | Result |
| --- | --- |
| Simulation health | PASS |
| Missing incident /api/incidents/999999 | PASS |
| Missing incident /api/incidents/999999/accept | PASS |
| Missing incident /api/incidents/999999/close | PASS |
| Missing incident /api/incidents/999999/simulate-callback | PASS |
| Invalid body /api/incidents/1/accept {} | PASS |
| Invalid body /api/incidents/1/accept {"owner": ""} | PASS |
| Invalid body /api/incidents/1/close {"by": ""} | PASS |
| Invalid body /api/incidents/1/simulate-callback {"outcome": "invalid"} | PASS |
| Invalid body /api/incidents/1/simulate-callback {"outcome": "worse", "danger": "invalid"} | PASS |
| Invalid body /api/demo/reset {"seed": null} | PASS |
| Whitespace-only human identity accept | PASS |
| Whitespace-only human identity close | PASS |
| Malformed REST JSON | PASS |
| Invalid reset preserves data: missing | PASS |
| Invalid reset preserves data: ../storm_night | PASS |
| Invalid reset preserves data: gazetteer | PASS |
| Invalid reset preserves data: oncall | PASS |
| Unknown twist rejected | PASS |
| Callback recorded and never closes: worse | PASS |
| Callback recorded and never closes: same | PASS |
| Callback recorded and never closes: better | PASS |
| Callback recorded and never closes: no_answer | PASS |
| Worse increases risk | PASS |
| Reported danger reaches supervisor step | PASS |
| No answer opens unreachable debt | PASS |
| No answer schedules retry | PASS |
| Silence never closes or raises risk alone | PASS |
| Overdue assignment gets nudge | PASS |
| Storm reports linked | PASS |
| Unknown location opens debt without guessing | PASS |
| Unknown hazard falls back safely | PASS |
| Irrelevant webhook ignored | PASS |
| Malformed webhook: missing call ID | PASS |
| Malformed webhook: list body | PASS |
| Malformed webhook: bad timestamp | PASS |
| Malformed webhook: bad metadata | PASS |
| Malformed webhook JSON | PASS |
| Unsigned intake rejected | PASS |
| Duplicate intake is idempotent | PASS |
| Disconnect mapped to no_answer: dial_no_answer | PASS |
| Disconnect mapped to no_answer: voicemail_reached | PASS |
| Disconnect mapped to no_answer: dial_busy | PASS |
| Disconnect mapped to no_answer: dial_failed | PASS |
| Duplicate callback is idempotent | PASS |
| Accept clears debt and stops timer | PASS |
| Late callback never reopens closed case | PASS |
| Department silence produces alert | PASS |
| Surge loads reports | PASS |
| Unknown domain rejected | PASS |
| Reset clears callbacks and twists | PASS |
| Low-risk step-1 case excluded from supervisor | PASS |

## All frontend API checks

These execute existing api.ts with mocked fetch, not browser interactions.

| Scenario | Result |
| --- | --- |
| Backend offline rejects state fetch | PASS |
| HTTP 500 rejects state fetch | PASS |
| Missing incident 404 rejects detail fetch | PASS |
| Malformed response JSON rejects state fetch | PASS |
| Fixture reads need no backend | PASS |
| Fixture writes never reach backend | PASS |
| Live worse request carries outcome and danger | PASS |

## Reproduce

From backend:

```sh
CALL_MODE=simulate .venv/bin/python -m pytest -q
```

Permanent regression coverage: `backend/tests/test_failure_scenarios.py`; valid webhook fixtures sign their payloads using a synthetic key. The existing intake smoke test now uses that authenticated fixture.

From frontend:

```sh
npm run build
```

Supplementary harnesses on this computer: `/private/tmp/handoffproof_adverse_check_fixed.py` (from backend, with `PYTHONPATH=.` and `LADDER_ENABLED=0`) and `/private/tmp/handoffproof-frontend-check.cjs` (from frontend). They are temporary; the new regression tests are kept in the repository.

## Remaining verification limits

- Real Retell calls, account configuration, actual provider delivery and the public tunnel are not verified. The configured Retell key must support webhook verification.
- Signature protocol reference: [Retell official Python SDK](https://github.com/RetellAI/retell-python-sdk/blob/main/src/retell/lib/webhook_auth.py). Local tests use synthetic signatures.
- Surge is ingested immediately by the toggle; it is not a timed 60-second replay.
- A port-domain demo is not implemented; unsupported domains are rejected.
- Invalid-input reset is protected by prevalidation; disk failures, interrupted valid resets, and simultaneous writes are not covered by these checks.
- Browser rendering/outage recovery, multi-computer networking, load/soak testing and crash recovery remain unverified.

No shared schema, .env, frontend implementation, dependency pins, branch, or Git history was changed.
