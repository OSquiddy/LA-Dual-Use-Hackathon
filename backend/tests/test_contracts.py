"""The dashboard's fixture JSON must keep matching the backend's response models."""
import json

from app.config import REPO_ROOT
from app.contracts import IncidentDetailView, StateView

FIXTURES = REPO_ROOT / "frontend" / "src" / "fixtures"


def test_state_fixture_matches_contract():
    StateView.model_validate(json.loads((FIXTURES / "state.json").read_text(encoding="utf-8")))


def test_incident_fixture_matches_contract():
    IncidentDetailView.model_validate(json.loads((FIXTURES / "incident.json").read_text(encoding="utf-8")))
