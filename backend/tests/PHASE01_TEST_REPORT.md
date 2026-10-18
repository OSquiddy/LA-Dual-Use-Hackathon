# Combined Phase 0 and Phase 1 test report

Branch: backend. Local automated checks only; CALL_MODE=simulate, temporary databases, fictional fixtures and synthetic signing key. No real calls or public services were used, and the running demo was not reset.

## Result

**All checks run in this matrix passed.** This validates the listed local scenarios, not every possible situation or external service.

| Check | Result |
| --- | --- |
| Backend pytest | **147 PASS, 0 FAIL/errors/skips/XFAIL** |
| Frontend rendered from real test API responses | **48 PASS** |
| Frontend state/error/ownership rendering | **11 PASS** |
| Frontend mocked API checks | **7 PASS** |
| Supplemental backend failure matrix | **52 PASS** |
| VITE_API=fixture production build | **PASS** |
| VITE_API=live production build | **PASS** |
| pip dependency consistency | **PASS** |
| git diff --check | **PASS** |
| Root/frontend local environment files ignored and untracked | **PASS** |

Suites overlap; counts should not be summed as unique product requirements. One existing Starlette/AnyIO deprecation warning remains; pip also reported an unavailable cache directory without affecting its successful check.

## New combined acceptance matrix

Each of 12 flows starts with the three-report storm, accepts a signed synthetic fourth intake, checks duplicate delivery, advances follow-up using a fake clock and a recorded outbound stub, receives a signed outcome, then checks acknowledgment, acceptance and human closure. All original reports, consent and source refs are checked. The frontend renders actual state/detail responses at each of four stages (12 × 4 = 48 renders).

| Outcome | Fourth caller opted in | Fourth caller declined | Consent missing |
| --- | --- | --- | --- |
| Worse | PASS | PASS | PASS |
| Same | PASS | PASS | PASS |
| Better | PASS | PASS | PASS |
| No answer | PASS | PASS | PASS |

When the fourth caller declines or has no consent, the engine contacts an earlier opted-in seed witness, never that fourth caller. Existing tests separately prove zero calls when an incident has no consenting witness.

At all four stages, the real React components render preserved report transcripts and consent; critical evidence stays visible after acceptance; acknowledgment is distinguished from acceptance; closed cases leave the active queue; full phone numbers never appear in the rendered HTML. Hooks receive exported state/detail rather than running browser effects.

## Existing coverage rerun

- Spoken-number geocoding, map lookup, location debt, complete/partial coordinates.
- Spatial/time/hazard linking, boundary cases, nearest/anchor behavior and preservation of sources.
- Evidence-only risk, negation, improvement, no-answer uncertainty and capped retries.
- Signature freshness, tamper/unsigned rejection, malformed payloads and duplicate intake/outcomes.
- Callback case/attempt identity and delayed-result protection after reset.
- Human ownership/closure, department silence, critical alerts beyond top ten.
- Safe invalid-seed handling, surge source preservation and idempotent toggles.
- Consent revocation, provider timeout simulation, actual simulator delivery and same-schema app restart persistence.

## New files

- backend/tests/test_phase01_acceptance.py: 12 combined flow tests; optional export of synthetic response snapshots.
- frontend/scripts/check-phase01-integration.cjs: renders existing React components against those snapshots; fails with exit 1 on any mismatch.
- This report. No production or shared-schema changes in this pass.

## Reproduce

From backend, choose a fresh temporary snapshot directory:

```sh
HANDOFFPROOF_INTEGRATION_SNAPSHOTS=/private/tmp/handoffproof-phase01-snapshots CALL_MODE=simulate .venv/bin/python -m pytest -q
```

Then from frontend:

```sh
node scripts/check-phase01-integration.cjs /private/tmp/handoffproof-phase01-snapshots
node scripts/check-readiness.cjs
VITE_API=fixture npm run build
VITE_API=live npm run build
```

## Every backend test result

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
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[worse-opted-in] | PASS |
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[worse-declined] | PASS |
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[worse-missing] | PASS |
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[same-opted-in] | PASS |
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[same-declined] | PASS |
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[same-missing] | PASS |
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[better-opted-in] | PASS |
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[better-declined] | PASS |
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[better-missing] | PASS |
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[no_answer-opted-in] | PASS |
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[no_answer-declined] | PASS |
| tests.test_phase01_acceptance.test_combined_seed_intake_followup_and_human_handoff[no_answer-missing] | PASS |
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
| tests.test_phase1_sync.test_sync1_authenticated_intake_adds_fourth_report_without_losing_sources | PASS |
| tests.test_phase1_sync.test_sync1_new_intake_respects_permission_before_followup[True] | PASS |
| tests.test_phase1_sync.test_sync1_new_intake_respects_permission_before_followup[False] | PASS |
| tests.test_phase1_sync.test_sync1_new_intake_respects_permission_before_followup[None] | PASS |
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

## External and manual checks still outstanding

- Real Retell provider delivery/signatures, opted-in test call, account number/credit, tunnel and redacted actual provider fixture.
- Real-browser click, polling recovery, accessibility and projector checks; these renders do not execute network effects.
- Team-machine setup, shared-code review/sign-off, map confirmation and cross-machine Sync 1.
- Concurrent database reset/write behavior, load/soak tests, disk failures and general multilingual language accuracy are not certified.
- Timed surge replay and optional second-domain functionality are not certified.

**Phase 0/1 local automated gate: PASS. Team/external acceptance: pending those checks.**
