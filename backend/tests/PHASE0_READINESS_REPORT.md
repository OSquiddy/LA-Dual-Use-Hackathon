# Detailed readiness report — fixes verified

Branch: backend. Tested locally with CALL_MODE=simulate and temporary SQLite databases. No real calls, branch changes, commits, or pushes.

## Decision

**All automated checks in this report pass.** The seven deeper backend failures and the missing persistent critical-alert display have been fixed. This clears the local automated gate; team sign-off and external Retell verification remain separate.

## Results

| Check | Result |
| --- | --- |
| Backend pytest | **131 PASS, 0 FAIL, 0 skipped/XFAIL** |
| Frontend server-rendered UI checks | **8 PASS** |
| Frontend API checks with mocked fetch | **7 PASS** |
| Updated supplemental backend matrix | **52 PASS** |
| Frontend TypeScript and Vite build | **PASS** |
| git diff --check | **PASS** |

One existing dependency deprecation warning remains. Checks overlap and should not be added together as distinct requirements.

## What changed

| Defect | Fix |
| --- | --- |
| Partial coordinates crash distance calculation | Ingestion treats a partial pair as unresolved and opens a location debt; the linker calculates distance only when both complete pairs exist. |
| Old simulator result contaminates reset case | Delayed delivery requires the original pending call row; reset deletes it, so a timer cannot recreate evidence for a reused incident ID. |
| Callback bound to the wrong case or attempt | Existing call IDs must match both incident and attempt. A different call ID cannot reuse an already recorded attempt. Duplicate delivery remains idempotent. |
| Negated danger phrases add physical risk | Danger phrase matching checks ordered words within a clause and nearby explicit negation. Affirmative danger, contrast clauses, and cannot-get-out language retain evidence points. Explicit anyone_in_danger remains a conservative danger flag. |
| Accepted critical evidence disappears outside top ten | A separate uncapped CriticalAlerts section renders reason, quote, acceptance, evidence references, and a review button independently of the supervisor queue. |

## Regression coverage

- Geographic and time linking boundaries, geographic-anchor drift prevention, closed-case isolation.
- Partial latitude/longitude pairs produce unresolved locations and debts.
- Provider timeouts, capped retry, missing/false consent, revocation before retry.
- A real simulator timer delivers successfully without external HTTP; a captured pending timer delivered after reset does nothing.
- Wrong-case and wrong-attempt outcomes leave evidence unchanged; duplicate attempt cannot overwrite worse with better.
- Negated and affirmative danger, including contrast clauses and not-only wording.
- Invalid scenario validation preserves data; original webhook signature and payload checks remain green.
- All twelve critical alerts render beyond the queue cap, including accepted cases; no empty critical section is rendered.

## Every backend test

| Test | Result |
| --- | --- |
| tests.test_contracts.test_state_fixture_matches_contract | PASS |
| tests.test_contracts.test_incident_fixture_matches_contract | PASS |
| tests.test_contracts.test_live_responses_match_dashboard_contracts | PASS |
| tests.test_contracts.test_fixture_summary_and_geography_are_consistent | PASS |
| tests.test_engine.test_storm_night_is_one_flood_with_three_retained_reports | PASS |
| tests.test_engine.test_far_report_starts_its_own_incident | PASS |
| tests.test_engine.test_incompatible_hazard_is_not_linked | PASS |
| tests.test_engine.test_report_outside_time_window_is_not_linked | PASS |
| tests.test_engine.test_vague_location_links_by_street_and_keeps_a_location_debt | PASS |
| tests.test_engine.test_duplicate_webhook_is_ingested_once | PASS |
| tests.test_engine.test_storm_night_risk_is_built_from_evidence | PASS |
| tests.test_engine.test_danger_word_not_in_the_callers_words_is_ignored | PASS |
| tests.test_engine.test_same_caller_twice_is_not_independent | PASS |
| tests.test_engine.test_only_answered_trends_move_risk | PASS |
| tests.test_engine.test_nudge_then_default_owner_is_not_acceptance | PASS |
| tests.test_engine.test_missing_on_call_contact_is_flagged_not_invented | PASS |
| tests.test_engine.test_acknowledge_is_receipt_only | PASS |
| tests.test_engine.test_silence_never_closes_a_case | PASS |
| tests.test_engine.test_consented_caller_is_called_back_once | PASS |
| tests.test_engine.test_no_consent_means_no_call | PASS |
| tests.test_engine.test_high_risk_without_consent_goes_to_supervisor_as_unknown | PASS |
| tests.test_engine.test_no_answer_is_unknown_and_retries_are_capped | PASS |
| tests.test_engine.test_duplicate_callback_webhook_is_ignored | PASS |
| tests.test_engine.test_resident_says_worse_pins_a_critical_alert_with_their_words | PASS |
| tests.test_engine.test_worse_replaces_an_unknown_alert_but_not_the_other_way | PASS |
| tests.test_engine.test_accept_stops_the_ladder_but_the_alert_stays_until_closed | PASS |
| tests.test_engine.test_person_in_danger_at_intake_is_critical_immediately | PASS |
| tests.test_engine.test_critical_alerts_are_never_capped_by_the_top_10 | PASS |
| tests.test_engine.test_low_risk_unaccepted_case_stays_with_its_department | PASS |
| tests.test_engine.test_dashboard_never_sees_full_phone_numbers | PASS |
| tests.test_failure_scenarios.test_whitespace_identity_rejected_without_mutation[   -accept-owner] | PASS |
| tests.test_failure_scenarios.test_whitespace_identity_rejected_without_mutation[   -close-by] | PASS |
| tests.test_failure_scenarios.test_whitespace_identity_rejected_without_mutation[   -acknowledge-by] | PASS |
| tests.test_failure_scenarios.test_whitespace_identity_rejected_without_mutation[\t\n-accept-owner] | PASS |
| tests.test_failure_scenarios.test_whitespace_identity_rejected_without_mutation[\t\n-close-by] | PASS |
| tests.test_failure_scenarios.test_whitespace_identity_rejected_without_mutation[\t\n-acknowledge-by] | PASS |
| tests.test_failure_scenarios.test_human_identity_is_trimmed | PASS |
| tests.test_failure_scenarios.test_invalid_reset_preserves_sources_events_and_twists[gazetteer] | PASS |
| tests.test_failure_scenarios.test_invalid_reset_preserves_sources_events_and_twists[oncall] | PASS |
| tests.test_failure_scenarios.test_invalid_reset_preserves_sources_events_and_twists[missing] | PASS |
| tests.test_failure_scenarios.test_invalid_reset_preserves_sources_events_and_twists[../storm_night] | PASS |
| tests.test_failure_scenarios.test_bad_row_in_scenario_rejected_before_reset[bad_row0] | PASS |
| tests.test_failure_scenarios.test_bad_row_in_scenario_rejected_before_reset[bad_row1] | PASS |
| tests.test_failure_scenarios.test_bad_row_in_scenario_rejected_before_reset[bad_row2] | PASS |
| tests.test_failure_scenarios.test_authenticated_malformed_webhook_is_422[payload0] | PASS |
| tests.test_failure_scenarios.test_authenticated_malformed_webhook_is_422[payload1] | PASS |
| tests.test_failure_scenarios.test_authenticated_malformed_webhook_is_422[payload2] | PASS |
| tests.test_failure_scenarios.test_authenticated_malformed_webhook_is_422[payload3] | PASS |
| tests.test_failure_scenarios.test_authenticated_malformed_webhook_is_422[payload4] | PASS |
| tests.test_failure_scenarios.test_authenticated_malformed_webhook_is_422[payload5] | PASS |
| tests.test_failure_scenarios.test_authenticated_malformed_webhook_is_422[payload6] | PASS |
| tests.test_failure_scenarios.test_authenticated_malformed_webhook_is_422[payload7] | PASS |
| tests.test_failure_scenarios.test_authenticated_invalid_json_is_422 | PASS |
| tests.test_failure_scenarios.test_unsigned_webhook_rejected | PASS |
| tests.test_failure_scenarios.test_stale_or_future_signature_rejected[-600000] | PASS |
| tests.test_failure_scenarios.test_stale_or_future_signature_rejected[600000] | PASS |
| tests.test_failure_scenarios.test_tampered_signature_rejected | PASS |
| tests.test_failure_scenarios.test_unconfigured_signing_key_fails_closed | PASS |
| tests.test_failure_scenarios.test_authenticated_unicode_and_duplicate_intake | PASS |
| tests.test_failure_scenarios.test_duplicate_signed_callback_preserves_events_and_risk | PASS |
| tests.test_failure_scenarios.test_department_toggle_produces_one_alert_and_suppresses_nudge | PASS |
| tests.test_failure_scenarios.test_real_department_threshold_and_acceptance_clear_alert | PASS |
| tests.test_failure_scenarios.test_surge_retains_50_reports_in_four_clusters_and_is_idempotent | PASS |
| tests.test_failure_scenarios.test_unsupported_domain_rejected_without_mutation[nonsense] | PASS |
| tests.test_failure_scenarios.test_unsupported_domain_rejected_without_mutation[port] | PASS |
| tests.test_failure_scenarios.test_unsupported_domain_rejected_without_mutation[] | PASS |
| tests.test_failure_scenarios.test_unsupported_domain_rejected_without_mutation[None] | PASS |
| tests.test_failure_scenarios.test_supported_domain_is_accepted | PASS |
| tests.test_failure_scenarios.test_phones_down_never_places_call_or_increases_physical_risk | PASS |
| tests.test_phase0_geography.test_storm_reports_have_demo_locations | PASS |
| tests.test_phase0_geography.test_distant_street_is_outside_link_radius | PASS |
| tests.test_phase0_geography.test_cross_street_order_does_not_matter | PASS |
| tests.test_phase0_geography.test_unknown_location_is_not_guessed | PASS |
| tests.test_phase0_geography.test_numbered_avenue_variants[Figueroa and Avenue fifty two] | PASS |
| tests.test_phase0_geography.test_numbered_avenue_variants[Figueroa and Ave 52] | PASS |
| tests.test_phase0_geography.test_numbered_avenue_variants[Avenue Fifty-Two by Figueroa] | PASS |
| tests.test_phase0_geography.test_numbered_avenue_variants[Ave fifty two and Figueroa] | PASS |
| tests.test_phase0_geography.test_unlisted_avenue_is_not_guessed[Figueroa and Ave 520] | PASS |
| tests.test_phase0_geography.test_unlisted_avenue_is_not_guessed[Figueroa and Avenue fifty nine] | PASS |
| tests.test_phase0_geography.test_unlisted_avenue_is_not_guessed[Other street and Avenue fifty two] | PASS |
| tests.test_readiness.test_link_distance_boundary[0-True] | PASS |
| tests.test_readiness.test_link_distance_boundary[299.9-True] | PASS |
| tests.test_readiness.test_link_distance_boundary[300.1-False] | PASS |
| tests.test_readiness.test_link_distance_boundary[1000-False] | PASS |
| tests.test_readiness.test_link_time_boundary[3599-True] | PASS |
| tests.test_readiness.test_link_time_boundary[3600-True] | PASS |
| tests.test_readiness.test_link_time_boundary[3601-False] | PASS |
| tests.test_readiness.test_link_time_boundary[-3601-False] | PASS |
| tests.test_readiness.test_link_anchor_prevents_distance_chain_drift | PASS |
| tests.test_readiness.test_closed_incident_cannot_absorb_new_report | PASS |
| tests.test_readiness.test_missing_or_negative_webhook_consent_never_calls[None] | PASS |
| tests.test_readiness.test_missing_or_negative_webhook_consent_never_calls[False] | PASS |
| tests.test_readiness.test_missing_or_negative_webhook_consent_never_calls[false] | PASS |
| tests.test_readiness.test_missing_or_negative_webhook_consent_never_calls[no] | PASS |
| tests.test_readiness.test_missing_or_negative_webhook_consent_never_calls[unknown] | PASS |
| tests.test_readiness.test_missing_or_negative_webhook_consent_never_calls[0] | PASS |
| tests.test_readiness.test_provider_timeout_records_unknown_without_risk_increase | PASS |
| tests.test_readiness.test_second_missed_call_clears_retry_timer_at_cap | PASS |
| tests.test_readiness.test_invalid_scenario_structure_preserves_data[None] | PASS |
| tests.test_readiness.test_invalid_scenario_structure_preserves_data[bad1] | PASS |
| tests.test_readiness.test_invalid_scenario_structure_preserves_data[bad2] | PASS |
| tests.test_readiness.test_invalid_scenario_structure_preserves_data[bad3] | PASS |
| tests.test_readiness.test_invalid_scenario_structure_preserves_data[bad4] | PASS |
| tests.test_readiness.test_invalid_scenario_structure_preserves_data[bad5] | PASS |
| tests.test_readiness.test_partial_coordinates_do_not_crash_ingestion | PASS |
| tests.test_readiness.test_pending_simulator_callback_cannot_mutate_reset_incident | PASS |
| tests.test_readiness.test_callback_call_id_cannot_be_reassigned_to_another_incident | PASS |
| tests.test_readiness.test_same_call_attempt_is_not_applied_twice_under_different_ids | PASS |
| tests.test_readiness.test_negated_danger_does_not_count_as_confirmed_evidence[Nobody is trapped.] | PASS |
| tests.test_readiness.test_negated_danger_does_not_count_as_confirmed_evidence[The driver is not trapped.] | PASS |
| tests.test_readiness.test_negated_danger_does_not_count_as_confirmed_evidence[No child is injured.] | PASS |
| tests.test_readiness.test_real_simulator_delivers_outcome_without_network | PASS |
| tests.test_readiness.test_revoked_consent_prevents_retry | PASS |
| tests.test_readiness.test_same_schema_app_restart_preserves_evidence | PASS |
| tests.test_readiness.test_partial_coordinate_pair_opens_location_debt[35.0-None] | PASS |
| tests.test_readiness.test_partial_coordinate_pair_opens_location_debt[None--117.0] | PASS |
| tests.test_readiness.test_existing_callback_wrong_attempt_is_ignored | PASS |
| tests.test_readiness.test_danger_negation_preserves_affirmative_evidence[The car is not stuck.-phrases0-5] | PASS |
| tests.test_readiness.test_danger_negation_preserves_affirmative_evidence[No one is trapped, but the water is rising.-phrases1-30] | PASS |
| tests.test_readiness.test_danger_negation_preserves_affirmative_evidence[The driver is trapped.-phrases2-30] | PASS |
| tests.test_readiness.test_danger_negation_preserves_affirmative_evidence[The driver can't get out.-phrases3-30] | PASS |
| tests.test_readiness.test_danger_negation_preserves_affirmative_evidence[The driver is not only trapped but injured.-phrases4-30] | PASS |
| tests.test_smoke.test_health | PASS |
| tests.test_smoke.test_reset_loads_storm_night | PASS |
| tests.test_smoke.test_gazetteer_geocodes_seed_locations | PASS |
| tests.test_smoke.test_storm_night_links_into_one_incident | PASS |
| tests.test_smoke.test_accept_clears_no_owner | PASS |
| tests.test_smoke.test_close_requires_a_named_person | PASS |
| tests.test_smoke.test_simulated_callback_is_recorded | PASS |
| tests.test_smoke.test_unknown_twist_is_404 | PASS |
| tests.test_smoke.test_intake_webhook_creates_report | PASS |

## Reproduce

From backend:

```sh
CALL_MODE=simulate .venv/bin/python -m pytest -q
```

From frontend:

```sh
npm run build
node scripts/check-readiness.cjs
```

Supplemental local harnesses: /private/tmp/handoffproof_adverse_check_fixed.py (from backend with PYTHONPATH=. and LADDER_ENABLED=0), /private/tmp/handoffproof-frontend-check.cjs (from frontend). Permanent backend regression coverage is kept in test_readiness.py and test_failure_scenarios.py.

## Limits and remaining coordination

- The frontend checks use React server rendering with injected state, not real-browser clicks or projector verification.
- Negation handling is a bounded English rule, not general speech understanding or a measured safety guarantee.
- The callback guards are verified for sequential delivery and reset; concurrent reset/write races and load/soak testing are not certified.
- Real Retell calls, provider signatures, phone number/credit, public tunnel and multi-computer connectivity remain externally unverified. Keep CALL_MODE=simulate until those checks are authorized and completed.
- Teammate clones/environment checks, map confirmation, fictional story/roster and scope sign-off remain team tasks.
- Surge currently loads immediately; timed replay and a port-domain demo remain later work.
- No shared contract/model/type files or environment files were changed for these fixes.

## Latest full rerun and running dashboard

The latest full rerun again passed 131 backend tests, 52 supplemental backend scenarios, 8 frontend rendering checks, 7 mocked frontend API checks, and the TypeScript/Vite build. One existing dependency deprecation warning remains.

Running dashboard: http://localhost:5174/ ; backend: http://localhost:8001/ . The live Vite API mode, frontend HTTP response, backend simulation health, and proxy were verified. The local demo was reset and populated through its HTTP API:

| Incident | Situation | Risk | Reports | Acceptance / critical |
| --- | --- | ---: | ---: | --- |
| 1 | Worsening flood | 100 | 3 | Unaccepted; critical |
| 2 | No answer | 50 | 13 | Contact debt; no physical-risk increase |
| 3 | Danger reported, crew accepts | 75 | 13 | Accepted; critical alert retained |
| 4 | Better | 40 | 12 | Unaccepted; not critical |
| 5 | Same | 50 | 12 | Unaccepted; not critical |

Verified five incidents retain all 53 source reports, with two persistent critical alerts and one department-silence alert. Calls remain simulated. The automatic ladder can continue changing due state while the dashboard runs. This is HTTP/API and static-render verification, not a real-browser interaction test.

## Phase 1 continuation

Phase 1 local work has begun. The suite now has **135 passing backend tests** and **11 passing frontend rendering checks**, with a passing production build. See [PHASE1_HANDOFF.md](PHASE1_HANDOFF.md) for the authenticated synthetic fourth-report acceptance test and remaining account/browser/team checks.

## Latest combined Phase 0/1 run

The expanded suite now passes **147 backend tests**, **48 API-to-React rendering cases**, **11 frontend state checks**, both fixture/live builds, and the previous supplemental matrices. See [PHASE01_TEST_REPORT.md](PHASE01_TEST_REPORT.md) for the scenario coverage and remaining manual/external gates.
