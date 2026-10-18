"""Phase 1 / Sync 1 acceptance: authenticated synthetic intake joins the three-report story.

No provider payload, account, phone call, public tunnel or live-service claim is involved.
"""
import copy
import json
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.contracts import IncidentDetailView, StateView
from app.db import engine
from app.models import Report

FIXTURE = Path(__file__).parent / 'fixtures' / 'synthetic_retell_intake.json'


def test_sync1_authenticated_intake_adds_fourth_report_without_losing_sources(client, signed_webhook):
    before = StateView.model_validate(client.get('/api/state').json())
    assert len(before.incidents) == 1 and before.incidents[0].report_count == 3
    incident_id = before.incidents[0].id
    path = f'/api/incidents/{incident_id}'
    original = client.get(path).json()['reports']
    payload = json.loads(FIXTURE.read_text())

    assert signed_webhook(payload).status_code == 204
    state = StateView.model_validate(client.get('/api/state').json())
    assert len(state.incidents) == 1 and state.incidents[0].report_count == 4
    detail = IncidentDetailView.model_validate(client.get(path).json())
    assert [r.model_dump(mode='json') for r in detail.reports[:3]] == original
    added = detail.reports[-1]
    assert added.call_id == payload['call']['call_id'] and added.callback_ok is True
    assert added.phone == '•••0144'
    linked = [event for event in detail.events if f'report:{added.id}' in event.evidence]
    assert linked and all(event.type == 'linked' for event in linked)
    with Session(engine) as s:
        report = s.exec(select(Report).where(Report.call_id == added.call_id)).one()
        assert report.source == 'retell' and report.callback_ok is True
        assert report.lat is not None and report.lng is not None

    # Delivery retries must not duplicate the fourth witness or rewrite consent/evidence.
    before_retry = client.get(path).json()
    assert signed_webhook(payload).status_code == 204
    assert client.get(path).json() == before_retry


@pytest.mark.parametrize('permission', [True, False, None])
def test_sync1_new_intake_respects_permission_before_followup(client, signed_webhook, calls, clock, permission):
    # Close the initial synthetic case so the intake becomes a separate case with its own consent.
    initial = client.get('/api/state').json()['incidents'][0]['id']
    assert client.post(f'/api/incidents/{initial}/close', json={'by': 'Synthetic test operator'}).status_code == 200
    payload = copy.deepcopy(json.loads(FIXTURE.read_text()))
    fields = payload['call']['call_analysis']['custom_analysis_data']
    if permission is None:
        fields.pop('callback_ok')
    else:
        fields['callback_ok'] = permission
    assert signed_webhook(payload).status_code == 204
    (incident,) = client.get('/api/state').json()['incidents']
    clock.tick(3)
    placed = [call for call in calls if call['incident_id'] == incident['id']]
    assert len(placed) == (1 if permission is True else 0)
    detail = client.get(f"/api/incidents/{incident['id']}").json()
    assert detail['reports'][0]['callback_ok'] is (permission is True)
    assert detail['status'] != 'closed'
