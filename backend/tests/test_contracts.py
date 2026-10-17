"""The dashboard's fixture JSON must keep matching the backend's response models."""
import json

from app.config import REPO_ROOT
from app.contracts import IncidentDetailView, StateView
from app.engine.geocode import geocode

FIXTURES = REPO_ROOT / "frontend" / "src" / "fixtures"


def test_state_fixture_matches_contract():
    StateView.model_validate(json.loads((FIXTURES / "state.json").read_text(encoding="utf-8")))


def test_incident_fixture_matches_contract():
    IncidentDetailView.model_validate(json.loads((FIXTURES / "incident.json").read_text(encoding="utf-8")))


def test_live_responses_match_dashboard_contracts(client):
    state = StateView.model_validate(client.get("/api/state").json())
    for incident in state.incidents:
        response = client.get(f"/api/incidents/{incident.id}")
        assert response.status_code == 200
        detail = IncidentDetailView.model_validate(response.json())
        assert detail.report_count == len(detail.reports)
        assert detail.assignment.department == incident.department


def test_fixture_summary_and_geography_are_consistent():
    state = StateView.model_validate(json.loads((FIXTURES / "state.json").read_text(encoding="utf-8")))
    detail = IncidentDetailView.model_validate(json.loads((FIXTURES / "incident.json").read_text(encoding="utf-8")))
    summary = next(i for i in state.incidents if i.id == detail.id)
    assert summary.model_dump() == detail.model_dump(include=set(type(summary).model_fields))
    assert detail.report_count == len(detail.reports)
    for incident in state.incidents:
        hit = geocode(incident.title)
        assert hit is not None
        assert (incident.lat, incident.lng) == (hit.lat, hit.lng)
