# Failure scenario report

Run: October 17, 2026. Local scaffold; CALL_MODE=simulate. Backend checks used an isolated temporary SQLite database and TestClient. No live demo reset, real calls, or production changes.

## Results

- Existing pytest suite: 23 passed, 1 expected B4 XFAIL, 1 dependency deprecation warning.
- Additional backend scenarios: 30 PASS, 22 FAIL (52 total).
- Frontend API module scenarios with mocked fetch: 7 PASS, 0 FAIL.
- Frontend TypeScript and Vite production build: PASS.

FAIL means the desired defensive/product behavior is absent. Planned scaffold gaps are identified separately; they are not unexpected regressions in the existing suite.

## Every additional backend scenario

| Scenario | Result | Observation | Owner / scope |
| --- | --- | --- | --- |
| Simulation health | PASS | Expected behavior observed | B: Current behavior check |
| Missing incident /api/incidents/999999 | PASS | Expected behavior observed | B: Current behavior check |
| Missing incident /api/incidents/999999/accept | PASS | Expected behavior observed | B: Current behavior check |
| Missing incident /api/incidents/999999/close | PASS | Expected behavior observed | B: Current behavior check |
| Missing incident /api/incidents/999999/simulate-callback | PASS | Expected behavior observed | B: Current behavior check |
| Invalid body /api/incidents/1/accept {} | PASS | Expected behavior observed | B: Current behavior check |
| Invalid body /api/incidents/1/accept {"owner": ""} | PASS | Expected behavior observed | B: Current behavior check |
| Invalid body /api/incidents/1/close {"by": ""} | PASS | Expected behavior observed | B: Current behavior check |
| Invalid body /api/incidents/1/simulate-callback {"outcome": "invalid"} | PASS | Expected behavior observed | B: Current behavior check |
| Invalid body /api/incidents/1/simulate-callback {"outcome": "worse", "danger": "invalid"} | PASS | Expected behavior observed | B: Current behavior check |
| Invalid body /api/demo/reset {"seed": null} | PASS | Expected behavior observed | B: Current behavior check |
| Whitespace-only human identity accept | FAIL | Whitespace identity accepted; expected 422 | B: Shared request validation |
| Whitespace-only human identity close | FAIL | Whitespace identity accepted; expected 422 | B: Shared request validation |
| Malformed REST JSON | PASS | Expected behavior observed | B: Current behavior check |
| Invalid reset preserves data: missing | PASS | Expected behavior observed | B: Current behavior check |
| Invalid reset preserves data: ../storm_night | PASS | Expected behavior observed | B: Current behavior check |
| Invalid reset preserves data: gazetteer | FAIL | Expected controlled 4xx, got 500 | B: Current behavior check |
| Invalid reset preserves data: oncall | FAIL | Expected controlled 4xx, got 500 | B: Current behavior check |
| Unknown twist rejected | PASS | Expected behavior observed | B: Current behavior check |
| Callback recorded and never closes: worse | PASS | Expected behavior observed | B: Current behavior check |
| Callback recorded and never closes: same | PASS | Expected behavior observed | B: Current behavior check |
| Callback recorded and never closes: better | PASS | Expected behavior observed | B: Current behavior check |
| Callback recorded and never closes: no_answer | PASS | Expected behavior observed | B: Current behavior check |
| Worse increases risk | FAIL | Risk remains 15 | B: B5/B9 pending |
| Reported danger reaches supervisor step | FAIL | Ladder remains below 5 | B: B9 pending |
| No answer opens unreachable debt | FAIL | Debt absent | B: B9 pending |
| No answer schedules retry | FAIL | Retry schedule unchanged | B: B9 pending |
| Silence never closes or raises risk alone | PASS | Expected behavior observed | B: Current behavior check |
| Overdue assignment gets nudge | FAIL | Overdue case stays at step 1 | B: B7 pending |
| Storm reports linked | FAIL | Three separate incidents | B: B4 intentionally pending |
| Unknown location opens debt without guessing | PASS | Expected behavior observed | B: Current behavior check |
| Unknown hazard falls back safely | PASS | Expected behavior observed | A: Current behavior check |
| Irrelevant webhook ignored | PASS | Expected behavior observed | A: Current behavior check |
| Malformed webhook: missing call ID | FAIL | Expected controlled 4xx; got 500 | A: A3/A9 validation |
| Malformed webhook: list body | FAIL | Expected controlled 4xx; got 500 | A: A3/A9 validation |
| Malformed webhook: bad timestamp | FAIL | Expected controlled 4xx; got 500 | A: A3/A9 validation |
| Malformed webhook: bad metadata | FAIL | Expected controlled 4xx; got 500 | A: A3/A9 validation |
| Malformed webhook JSON | FAIL | Malformed JSON causes 500 | A: A3 validation |
| Unsigned intake rejected | FAIL | Unsigned intake accepted | A: A3 signature check pending |
| Duplicate intake is idempotent | FAIL | Webhook retry duplicated report | A/B: Webhook retry deduplication |
| Disconnect mapped to no_answer: dial_no_answer | PASS | Expected behavior observed | A: Current behavior check |
| Disconnect mapped to no_answer: voicemail_reached | PASS | Expected behavior observed | A: Current behavior check |
| Disconnect mapped to no_answer: dial_busy | PASS | Expected behavior observed | A: Current behavior check |
| Disconnect mapped to no_answer: dial_failed | PASS | Expected behavior observed | A: Current behavior check |
| Duplicate callback is idempotent | FAIL | Duplicate audit event on webhook retry | A/B: Callback retry deduplication |
| Accept clears debt and stops timer | PASS | Expected behavior observed | B: Current behavior check |
| Late callback never reopens closed case | PASS | Expected behavior observed | B: Current behavior check |
| Department silence produces alert | FAIL | No department alert | B: B12 pending |
| Surge loads reports | FAIL | No surge reports loaded | B: B13 pending |
| Unknown domain rejected | FAIL | Unknown domain accepted | B: B15 pending |
| Reset clears callbacks and twists | PASS | Expected behavior observed | B: Current behavior check |
| Low-risk step-1 case excluded from supervisor | FAIL | Low-risk step-1 case in supervisor queue | B: B10 pending |

## Every frontend API module scenario

These execute the transpiled existing api.ts with mocked fetch. They do not verify browser rendering, hook recovery, or button error presentation.

| Scenario | Result |
| --- | --- |
| Backend offline rejects state fetch | PASS |
| HTTP 500 rejects state fetch | PASS |
| Missing incident 404 rejects detail fetch | PASS |
| Malformed response JSON rejects state fetch | PASS |
| Fixture reads need no backend | PASS |
| Fixture writes never reach backend | PASS |
| Live worse request carries outcome and danger | PASS |

## Existing pytest suite output

```text
============================= test session starts ==============================
platform darwin -- Python 3.11.17, pytest-8.3.3, pluggy-1.7.0 -- /Users/mboyun/LA-Dual-Use-Hackathon/backend/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/mboyun/LA-Dual-Use-Hackathon/backend
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.15.1
collecting ... collected 24 items

tests/test_contracts.py::test_state_fixture_matches_contract PASSED      [  4%]
tests/test_contracts.py::test_incident_fixture_matches_contract PASSED   [  8%]
tests/test_contracts.py::test_live_responses_match_dashboard_contracts PASSED [ 12%]
tests/test_contracts.py::test_fixture_summary_and_geography_are_consistent PASSED [ 16%]
tests/test_phase0_geography.py::test_storm_reports_have_demo_locations PASSED [ 20%]
tests/test_phase0_geography.py::test_distant_street_is_outside_link_radius PASSED [ 25%]
tests/test_phase0_geography.py::test_cross_street_order_does_not_matter PASSED [ 29%]
tests/test_phase0_geography.py::test_unknown_location_is_not_guessed PASSED [ 33%]
tests/test_phase0_geography.py::test_numbered_avenue_variants[Figueroa and Avenue fifty two] PASSED [ 37%]
tests/test_phase0_geography.py::test_numbered_avenue_variants[Figueroa and Ave 52] PASSED [ 41%]
tests/test_phase0_geography.py::test_numbered_avenue_variants[Avenue Fifty-Two by Figueroa] PASSED [ 45%]
tests/test_phase0_geography.py::test_numbered_avenue_variants[Ave fifty two and Figueroa] PASSED [ 50%]
tests/test_phase0_geography.py::test_unlisted_avenue_is_not_guessed[Figueroa and Ave 520] PASSED [ 54%]
tests/test_phase0_geography.py::test_unlisted_avenue_is_not_guessed[Figueroa and Avenue fifty nine] PASSED [ 58%]
tests/test_phase0_geography.py::test_unlisted_avenue_is_not_guessed[Other street and Avenue fifty two] PASSED [ 62%]
tests/test_smoke.py::test_health PASSED                                  [ 66%]
tests/test_smoke.py::test_reset_loads_storm_night PASSED                 [ 70%]
tests/test_smoke.py::test_gazetteer_geocodes_seed_locations PASSED       [ 75%]
tests/test_smoke.py::test_storm_night_links_into_one_incident XFAIL      [ 79%]
tests/test_smoke.py::test_accept_clears_no_owner PASSED                  [ 83%]
tests/test_smoke.py::test_close_requires_a_named_person PASSED           [ 87%]
tests/test_smoke.py::test_simulated_callback_is_recorded PASSED          [ 91%]
tests/test_smoke.py::test_unknown_twist_is_404 PASSED                    [ 95%]
tests/test_smoke.py::test_intake_webhook_creates_report PASSED           [100%]

=============================== warnings summary ===============================
.venv/lib/python3.11/site-packages/starlette/testclient.py:40
  /Users/mboyun/LA-Dual-Use-Hackathon/backend/.venv/lib/python3.11/site-packages/starlette/testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=================== 23 passed, 1 xfailed, 1 warning in 0.19s ===================
```

## Highest-priority findings

1. Reset accepts gazetteer/oncall as seed names, drops the database, then fails because they have no reports array. Validate scenario data before any reset. Owner B.
2. Unsigned webhooks are accepted (A3 pending). Malformed webhook bodies, metadata, and timestamps produce 500. Owner A.
3. Duplicate intake delivery inserts another report; duplicate callback delivery adds another audit event. Coordinate A/B.
4. Whitespace-only accept/close identity passes validation. Any shared-contract fix requires approval.
5. B4/B5/B7/B9/B10/B12/B13/B15 behavior remains incomplete, as reflected above. No later-phase implementation was added.

## Not verified

- Retell accounts, credentials, real phone calls, public tunnel, actual signatures and provider payloads.
- Browser rendering during an outage, automatic recovery, projector layout, and multiple-computer connectivity.
- SQLite lock contention, simultaneous reset/write traffic, disk full/read-only storage, process crash/restart recovery, long-running timers, load/soak performance.
- phones_down end-to-end call failure: the ladder does not initiate callbacks yet.
- Every possible malformed input: this is a bounded scenario matrix, not exhaustive verification.

## Reproduce additional checks on this machine

Backend harness: /private/tmp/handoffproof_adverse_check.py (run from backend with PYTHONPATH=. and .venv/bin/python).
Frontend harness: /private/tmp/handoffproof-frontend-check.cjs (run with node from frontend).
Harnesses and raw results are temporary local artifacts; production and shared files were not modified.
