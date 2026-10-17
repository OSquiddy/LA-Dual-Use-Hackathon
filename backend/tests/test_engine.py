"""B's engine rules: linking, evidence-only risk, consent-gated callbacks, ownership and critical alerts."""
from datetime import datetime, timedelta, timezone

from app.contracts import CallbackOutcome, ReportIn
from app.engine import ladder
from app.engine.ingest import ingest_report

DEMO_RESIDENT = "+13235550103"


def state(client) -> dict:
    return client.get("/api/state").json()


def incident(client, incident_id: int) -> dict:
    return client.get(f"/api/incidents/{incident_id}").json()


def storm(client) -> dict:
    (only,) = [i for i in state(client)["incidents"] if i["title"].startswith("Flooding — N Figueroa St & Ave 52")]
    return only


def report(call_id: str, **fields) -> int:
    fields.setdefault("hazard_type", "water_on_road")
    fields.setdefault("created_at", datetime.now(timezone.utc))
    return ingest_report(ReportIn(source="seed", call_id=call_id, **fields))


def answer(incident_id: int, call_id: str, attempt_no: int, outcome: str, danger: bool = False, summary: str = ""):
    ladder.record_callback_outcome(CallbackOutcome(
        incident_id=incident_id, call_id=call_id, attempt_no=attempt_no,
        outcome=outcome, danger=danger, summary=summary,
    ))


# --- B4 linking ------------------------------------------------------------------------------

def test_storm_night_is_one_flood_with_three_retained_reports(client):
    flood = storm(client)
    assert flood["hazard_type"] == "flood" and flood["report_count"] == 3
    detail = incident(client, flood["id"])
    assert [r["call_id"] for r in detail["reports"]] == ["seed-storm-1", "seed-storm-2", "seed-storm-3"]
    linked = [e for e in detail["events"] if e["type"] == "linked"]
    assert len(linked) == 2 and all(" m from the first report" in e["reason"] for e in linked)


def test_far_report_starts_its_own_incident(client):
    report("far-1", location_text="Figueroa and Avenue 57", hazard_type="flood", phone="+13235550111")
    assert len(state(client)["incidents"]) == 2


def test_incompatible_hazard_is_not_linked(client):
    report("tree-1", location_text="Figueroa and Avenue 52", hazard_type="downed_tree")
    assert len(state(client)["incidents"]) == 2


def test_report_outside_time_window_is_not_linked(client):
    report("late-1", location_text="Figueroa and Avenue 52", created_at=datetime.now(timezone.utc) + timedelta(minutes=90))
    assert len(state(client)["incidents"]) == 2


def test_vague_location_links_by_street_and_keeps_a_location_debt(client):
    report("vague-1", location_text="somewhere on Figueroa", phone="+13235550112")
    flood = storm(client)
    assert flood["report_count"] == 4
    assert any(d["kind"] == "location" for d in flood["debts"])
    assert any("same street (Figueroa)" in e["reason"] for e in incident(client, flood["id"])["events"])


def test_duplicate_webhook_is_ingested_once(client):
    first = report("dup-1", location_text="Figueroa and Avenue 53", phone="+13235550113")
    assert report("dup-1", location_text="Figueroa and Avenue 53", phone="+13235550113") == first
    assert storm(client)["report_count"] == 4


# --- B5 risk: evidence only ------------------------------------------------------------------

def test_storm_night_risk_is_built_from_evidence(client):
    # stalled vehicle base 35 + supported "car stuck" 25 + 2 more independent callers 10
    assert storm(client)["risk_score"] == 70


def test_danger_word_not_in_the_callers_words_is_ignored(client):
    report("pothole-1", location_text="Figueroa and Avenue 57", hazard_type="pothole",
           danger_words=["trapped"], transcript="There's a big pothole by the bus stop.")
    pothole = next(i for i in state(client)["incidents"] if i["hazard_type"] == "pothole")
    assert pothole["risk_score"] == 5


def test_same_caller_twice_is_not_independent(client):
    report("again-1", location_text="Figueroa and Avenue 53", phone="+13235550101")
    assert storm(client)["risk_score"] == 70


def test_only_answered_trends_move_risk(client, calls, clock):
    flood_id = storm(client)["id"]
    clock.tick(3)
    answer(flood_id, "test-call-1", 1, "no_answer")
    assert storm(client)["risk_score"] == 70  # silence is not evidence
    answer(flood_id, "x-2", 2, "same")
    assert storm(client)["risk_score"] == 70
    answer(flood_id, "x-3", 3, "worse")
    assert storm(client)["risk_score"] == 100
    answer(flood_id, "x-4", 4, "better")
    flood = storm(client)
    assert flood["risk_score"] == 60 and flood["status"] != "closed"


# --- B7/B8 ladder and ownership --------------------------------------------------------------

def test_nudge_then_default_owner_is_not_acceptance(client, calls, clock):
    flood_id = storm(client)["id"]
    clock.tick()
    assert storm(client)["ladder_step"] == 2
    clock.tick()
    flood = storm(client)
    assert flood["ladder_step"] == 3 and flood["owner"] == "J. Ramirez (on-call)"
    assert flood["accepted"] is False
    assert any(d["kind"] == "no_owner" and "not accepted yet" in d["label"] for d in flood["debts"])
    assert incident(client, flood_id)["assignment"]["default_owner_at"] is not None


def test_missing_on_call_contact_is_flagged_not_invented(client, calls, clock):
    report("nowhere-1", location_text=None, hazard_type="pothole")
    clock.tick(2)
    pothole = next(i for i in state(client)["incidents"] if i["hazard_type"] == "pothole")
    assert pothole["owner"] is None
    assert any("No on-call contact" in d["label"] for d in pothole["debts"])


def test_acknowledge_is_receipt_only(client, calls, clock):
    flood_id = storm(client)["id"]
    acked = client.post(f"/api/incidents/{flood_id}/acknowledge", json={"by": "M. Lee"}).json()
    assert acked["acknowledged"] is True and acked["accepted"] is False and acked["status"] == "open"
    clock.tick()
    assert storm(client)["ladder_step"] == 2  # the ladder keeps going until someone accepts
    assert incident(client, flood_id)["assignment"]["acknowledged_by"] == "M. Lee"


def test_silence_never_closes_a_case(client, calls, clock):
    clock.tick(12)
    flood = storm(client)
    assert flood["status"] != "closed" and flood["accepted"] is False


# --- B9 consent-gated callbacks --------------------------------------------------------------

def test_consented_caller_is_called_back_once(client, calls, clock):
    flood_id = storm(client)["id"]
    clock.tick(3)
    assert calls == [{
        "incident_id": flood_id, "phone": DEMO_RESIDENT, "attempt_no": 1,
        "vars": {"location": "Avenue 54 by Figueroa", "hazard": "flooding"},
    }]
    detail = incident(client, flood_id)
    assert detail["callbacks"][0]["outcome"] is None  # ringing
    assert not any(d["kind"] == "consent_unknown" for d in detail["debts"])


def test_no_consent_means_no_call(client, calls, clock):
    report("noconsent-1", location_text="Figueroa and Avenue 57", hazard_type="pothole", phone="+13235550114")
    clock.tick(3)
    pothole = next(i for i in state(client)["incidents"] if i["hazard_type"] == "pothole")
    assert all(c["incident_id"] != pothole["id"] for c in calls)
    assert any(d["kind"] == "consent_unknown" for d in pothole["debts"])
    assert pothole["critical"] is False  # low risk stays with the department
    assert any(e["type"] == "no_callback" for e in incident(client, pothole["id"])["events"])


def test_high_risk_without_consent_goes_to_supervisor_as_unknown(client, calls, clock):
    report("hr-1", location_text="Figueroa and Avenue 57", hazard_type="flood", phone="+13235550115",
           danger_words=["rising"], transcript="The water is rising fast.")
    report("hr-2", location_text="Figueroa and Avenue 57", hazard_type="water_on_road", phone="+13235550116")
    clock.tick(3)
    ave57 = next(i for i in state(client)["incidents"] if "Ave 57" in i["title"])
    assert ave57["risk_score"] == 60 and ave57["critical"] is True
    assert "unknown" in ave57["why"] and "worse" not in ave57["why"]
    assert all(c["incident_id"] != ave57["id"] for c in calls)


def test_no_answer_is_unknown_and_retries_are_capped(client, calls, clock):
    flood_id = storm(client)["id"]
    clock.tick(3)
    answer(flood_id, "test-call-1", 1, "no_answer")
    flood = storm(client)
    assert flood["risk_score"] == 70
    assert any(d["label"] == "Caller unreachable (1 missed)" for d in flood["debts"])
    assert flood["critical"] is True and "not confirmed worse" in flood["why"]

    clock.tick()
    assert [c["attempt_no"] for c in calls] == [1, 2]
    answer(flood_id, "test-call-2", 2, "no_answer")
    clock.tick(3)
    assert len(calls) == 2  # MAX_CALLBACK_ATTEMPTS
    assert any(d["label"] == "Caller unreachable (2 missed)" for d in storm(client)["debts"])


def test_duplicate_callback_webhook_is_ignored(client, calls, clock):
    flood_id = storm(client)["id"]
    clock.tick(3)
    answer(flood_id, "test-call-1", 1, "worse")
    answer(flood_id, "test-call-1", 1, "better")
    assert storm(client)["risk_score"] == 100


# --- B10/B11 supervisor, critical lane, human-only actions -----------------------------------

def test_resident_says_worse_pins_a_critical_alert_with_their_words(client, calls, clock):
    flood_id = storm(client)["id"]
    clock.tick(3)
    answer(flood_id, "test-call-1", 1, "worse", danger=True, summary="Water is at the curb and rising")
    s = state(client)
    (alert,) = s["critical_alerts"]
    assert alert["incident_id"] == flood_id and alert["quote"] == "Water is at the curb and rising"
    assert alert["reason"].startswith("Resident says it's worse") and alert["evidence"][0].startswith("callback:")
    flood = storm(client)
    assert flood["status"] == "escalated" and flood["ladder_step"] == 5 and flood["accepted"] is False
    assert s["supervisor_queue"][0] == flood_id


def test_worse_replaces_an_unknown_alert_but_not_the_other_way(client, calls, clock):
    flood_id = storm(client)["id"]
    clock.tick(3)
    answer(flood_id, "test-call-1", 1, "no_answer")
    assert "unknown" in storm(client)["why"]
    clock.tick()
    answer(flood_id, "test-call-2", 2, "worse")
    assert storm(client)["why"].startswith("Resident says it's worse")
    answer(flood_id, "late-call", 3, "no_answer")
    assert storm(client)["why"].startswith("Resident says it's worse")


def test_accept_stops_the_ladder_but_the_alert_stays_until_closed(client, calls, clock):
    flood_id = storm(client)["id"]
    clock.tick(3)
    answer(flood_id, "test-call-1", 1, "worse")
    client.post(f"/api/incidents/{flood_id}/accept", json={"owner": "M. Lee"})
    clock.tick(5)
    assert len(calls) == 1
    (alert,) = state(client)["critical_alerts"]
    assert alert["accepted"] is True and alert["owner"] == "M. Lee"
    assert flood_id not in state(client)["supervisor_queue"]

    client.post(f"/api/incidents/{flood_id}/close", json={"by": "M. Lee", "note": "Drain cleared, water receding"})
    assert state(client)["critical_alerts"] == []


def test_person_in_danger_at_intake_is_critical_immediately(client):
    report("danger-1", location_text="Figueroa and Avenue 57", hazard_type="flood",
           anyone_in_danger=True, transcript="My neighbor is stuck in her car and the water is rising.")
    ave57 = next(i for i in state(client)["incidents"] if "Ave 57" in i["title"])
    assert ave57["critical"] is True and ave57["why"] == "Caller reports someone in danger"


def test_critical_alerts_are_never_capped_by_the_top_10(client):
    for n in range(12):
        report(f"crit-{n}", location_text=None, hazard_type="flood", anyone_in_danger=True)
    s = state(client)
    assert len(s["supervisor_queue"]) == 10
    assert len(s["critical_alerts"]) == 12


def test_low_risk_unaccepted_case_stays_with_its_department(client):
    report("pothole-2", location_text="Figueroa and Avenue 57", hazard_type="pothole")
    pothole = next(i for i in state(client)["incidents"] if i["hazard_type"] == "pothole")
    assert pothole["id"] not in state(client)["supervisor_queue"]


def test_dashboard_never_sees_full_phone_numbers(client):
    detail = incident(client, storm(client)["id"])
    assert [r["phone"] for r in detail["reports"]] == ["•••0101", "•••0102", "•••0103"]
    assert [r["callback_ok"] for r in detail["reports"]] == [False, False, True]
