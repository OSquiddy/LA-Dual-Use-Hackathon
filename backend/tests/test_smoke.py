def test_health(client):
    assert client.get("/health").json()["ok"] is True


def test_reset_loads_storm_night(client):
    state = client.get("/api/state").json()
    assert sum(i["report_count"] for i in state["incidents"]) == 3
    assert all(i["department"] == "Stormwater Operations" for i in state["incidents"])


def test_gazetteer_geocodes_seed_locations(client):
    state = client.get("/api/state").json()
    assert all(i["lat"] is not None for i in state["incidents"])
    assert not any(d["kind"] == "location" for i in state["incidents"] for d in i["debts"])


def test_storm_night_links_into_one_incident(client):
    incidents = client.get("/api/state").json()["incidents"]
    assert len(incidents) == 1 and incidents[0]["report_count"] == 3


def test_accept_clears_no_owner(client):
    incident_id = client.get("/api/state").json()["incidents"][0]["id"]
    accepted = client.post(f"/api/incidents/{incident_id}/accept", json={"owner": "M. Lee"}).json()
    assert accepted["accepted"] is True and accepted["status"] == "accepted"
    assert not any(d["kind"] == "no_owner" for d in accepted["debts"])


def test_close_requires_a_named_person(client):
    incident_id = client.get("/api/state").json()["incidents"][0]["id"]
    assert client.post(f"/api/incidents/{incident_id}/close", json={"by": ""}).status_code == 422
    closed = client.post(f"/api/incidents/{incident_id}/close", json={"by": "M. Lee", "note": "drain cleared"})
    assert closed.json()["status"] == "closed"


def test_simulated_callback_is_recorded(client):
    incident_id = client.get("/api/state").json()["incidents"][0]["id"]
    detail = client.post(f"/api/incidents/{incident_id}/simulate-callback", json={"outcome": "worse"}).json()
    assert detail["callbacks"][-1]["outcome"] == "worse"
    assert any("resident says worse" in e["reason"] for e in detail["events"])


def test_unknown_twist_is_404(client):
    assert client.post("/api/twists/meteor", json={"on": True}).status_code == 404
    assert client.post("/api/twists/dept_silent", json={"on": True}).json()["twists"]["dept_silent"] is True


def test_intake_webhook_creates_report(client, signed_webhook):
    payload = {
        "event": "call_analyzed",
        "call": {
            "call_id": "retell-test-1",
            "from_number": "+13235550199",
            "transcript": "Water is coming into my garage on Figueroa and Avenue 57",
            "call_analysis": {
                "custom_analysis_data": {
                    "location_text": "Figueroa and Avenue 57",
                    "hazard_type": "flood",
                    "danger_words": "rising",
                    "anyone_in_danger": False,
                }
            },
        },
    }
    assert signed_webhook(payload).status_code == 204
    state = client.get("/api/state").json()
    assert sum(i["report_count"] for i in state["incidents"]) == 4
