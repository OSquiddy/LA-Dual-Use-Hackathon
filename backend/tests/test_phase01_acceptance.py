"""Combined Phase 0/1 scenarios, exporting optional synthetic API snapshots for React checks."""
import json
import os
from pathlib import Path

import pytest

from app.contracts import IncidentDetailView, StateView

FIXTURE = Path(__file__).parent / 'fixtures' / 'synthetic_retell_intake.json'


@pytest.mark.parametrize('permission', [True, False, None], ids=['opted-in', 'declined', 'missing'])
@pytest.mark.parametrize('outcome', ['worse', 'same', 'better', 'no_answer'])
def test_combined_seed_intake_followup_and_human_handoff(
    client, signed_webhook, calls, clock, monkeypatch, permission, outcome,
):
    from app.voice import callbacks

    def no_network(*args, **kwargs):
        raise AssertionError('Combined simulation attempted external HTTP')
    monkeypatch.setattr(callbacks.httpx, 'post', no_network)
    initial = client.get('/api/state').json()
    assert len(initial['incidents']) == 1 and initial['incidents'][0]['report_count'] == 3
    i = initial['incidents'][0]['id']
    path = f'/api/incidents/{i}'
    originals = client.get(path).json()['reports']
    payload = json.loads(FIXTURE.read_text())
    fields = payload['call']['call_analysis']['custom_analysis_data']
    if permission is None:
        fields.pop('callback_ok')
    else:
        fields['callback_ok'] = permission
    assert signed_webhook(payload).status_code == 204
    assert signed_webhook(payload).status_code == 204
    detail = client.get(path).json()
    assert detail['reports'][:3] == originals
    assert detail['report_count'] == 4 and len(detail['reports']) == 4
    before_risk = detail['risk_score']

    # An incident may follow up with an earlier opted-in witness, never a declining new caller.
    clock.tick(3)
    assert len(calls) == 1
    assert calls[0]['phone'] == ('+13235550144' if permission is True else '+13235550103')
    callback = {'event': 'call_analyzed', 'call': {
        'call_id': 'test-call-1', 'metadata': {'incident_id': i, 'attempt_no': 1},
        'call_analysis': {'custom_analysis_data': {
            'outcome': outcome, 'anyone_in_danger': outcome == 'worse',
            'summary': f'SYNTHETIC combined evidence: {outcome}',
        }},
    }}
    if outcome == 'no_answer':
        callback['call']['disconnection_reason'] = 'dial_no_answer'
    assert signed_webhook(callback).status_code == 204
    answered = client.get(path).json()
    assert signed_webhook(callback).status_code == 204
    assert client.get(path).json() == answered
    expected = min(100, before_risk + 30) if outcome == 'worse' else before_risk - 10 if outcome == 'better' else before_risk
    assert answered['risk_score'] == expected
    assert answered['callbacks'][0]['outcome'] == outcome
    assert answered['status'] != 'closed'
    assert bool(answered['critical']) is (outcome in ('worse', 'no_answer'))
    assert any(d['kind'] == 'caller_unreachable' for d in answered['debts']) is (outcome == 'no_answer')

    snapshots = []
    def capture(stage):
        state = client.get('/api/state').json()
        detail = client.get(path).json()
        StateView.model_validate(state)
        IncidentDetailView.model_validate(detail)
        snapshots.append({'stage': stage, 'state': state, 'detail': detail})
    capture('review')
    acknowledged = client.post(path + '/acknowledge', json={'by': 'Synthetic operator'}).json()
    assert acknowledged['acknowledged'] and not acknowledged['accepted']
    capture('acknowledged')
    accepted = client.post(path + '/accept', json={'owner': 'Synthetic operator'}).json()
    assert accepted['accepted'] and accepted['next_step_at'] is None
    clock.tick(3)
    assert len(calls) == 1
    assert (len(client.get('/api/state').json()['critical_alerts']) > 0) is (outcome in ('worse', 'no_answer'))
    capture('accepted')
    closed = client.post(path + '/close', json={
        'by': 'Synthetic operator', 'note': 'SYNTHETIC test: resident verified resolution',
    }).json()
    assert closed['status'] == 'closed'
    assert client.get('/api/state').json()['incidents'] == []
    assert client.get('/api/state').json()['critical_alerts'] == []
    capture('closed')
    target = os.getenv('HANDOFFPROOF_INTEGRATION_SNAPSHOTS')
    if target:
        dest = Path(target)
        dest.mkdir(parents=True, exist_ok=True)
        (dest / f'{outcome}-{permission}.json').write_text(json.dumps(snapshots))
