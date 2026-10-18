"""Regression checks for every remaining failure in FAILURE_SCENARIO_REPORT.md."""
import json
import time
from datetime import timedelta

import pytest
from sqlmodel import Session, select

from app.db import engine
from app.engine import ladder, seeds
from app.models import Assignment, Incident, Report
from app.timeutil import utcnow
from app.voice import webhooks


def state(client):
    return client.get('/api/state').json()


def incident_id(client):
    return state(client)['incidents'][0]['id']


@pytest.mark.parametrize('action,key', [('accept', 'owner'), ('close', 'by'), ('acknowledge', 'by')])
@pytest.mark.parametrize('name', ['   ', '\t\n'])
def test_whitespace_identity_rejected_without_mutation(client, action, key, name):
    i = incident_id(client)
    before = client.get(f'/api/incidents/{i}').json()
    assert client.post(f'/api/incidents/{i}/{action}', json={key: name}).status_code == 422
    assert client.get(f'/api/incidents/{i}').json() == before


def test_human_identity_is_trimmed(client):
    i = incident_id(client)
    response = client.post(f'/api/incidents/{i}/accept', json={'owner': '  Demo operator  '})
    assert response.json()['owner'] == 'Demo operator'


@pytest.mark.parametrize('seed', ['gazetteer', 'oncall', 'missing', '../storm_night'])
def test_invalid_reset_preserves_sources_events_and_twists(client, seed):
    i = incident_id(client)
    client.post(f'/api/incidents/{i}/simulate-callback', json={'outcome': 'worse'})
    client.post('/api/twists/phones_down', json={'on': True})
    before = client.get(f'/api/incidents/{i}').json()
    assert client.post('/api/demo/reset', json={'seed': seed}).status_code == 404
    assert client.get(f'/api/incidents/{i}').json() == before
    assert state(client)['twists']['phones_down'] is True


@pytest.mark.parametrize('bad_row', [
    {'call_id': 'bad'}, {'hazard_type': 'flood'},
    {'call_id': 'bad', 'hazard_type': 'flood', 'offset_s': 'invalid'},
])
def test_bad_row_in_scenario_rejected_before_reset(client, monkeypatch, tmp_path, bad_row):
    scenario = {'reports': [{'call_id': 'valid', 'hazard_type': 'flood'}, bad_row]}
    (tmp_path / 'bad.json').write_text(json.dumps(scenario))
    before = state(client)['incidents']
    monkeypatch.setattr(seeds, 'SEEDS_DIR', tmp_path)
    assert client.post('/api/demo/reset', json={'seed': 'bad'}).status_code == 404
    assert state(client)['incidents'] == before


@pytest.mark.parametrize('payload', [
    [], {}, {'event': 'call_analyzed', 'call': {}},
    {'event': 'call_analyzed', 'call': {'call_id': 'bad-time', 'start_timestamp': 'invalid'}},
    {'event': 'call_analyzed', 'call': {'call_id': 'bad-meta', 'metadata': {'incident_id': 'invalid'}}},
    {'event': 'call_analyzed', 'call': {'call_id': 'bad-analysis', 'call_analysis': []}},
    {'event': 'call_analyzed', 'call': {'call_id': 'bad-fields', 'call_analysis': {'custom_analysis_data': ['bad']}}},
    {'event': 'call_analyzed', 'call': {'call_id': 'bad-id', 'metadata': {'incident_id': -1}}},
])
def test_authenticated_malformed_webhook_is_400(client, signed_webhook, payload):
    before = state(client)['incidents']
    assert signed_webhook(payload).status_code == 400
    assert state(client)['incidents'] == before


def test_authenticated_invalid_json_is_400(client, signed_webhook):
    assert signed_webhook(raw=b'{').status_code == 400


def test_unsigned_webhook_rejected(client):
    before = state(client)['incidents']
    assert client.post('/retell/webhook', json={'event': 'call_analyzed', 'call': {'call_id': 'forged'}}).status_code == 401
    assert state(client)['incidents'] == before


@pytest.mark.parametrize('age', [-600_000, 600_000])
def test_stale_or_future_signature_rejected(signed_webhook, age):
    assert signed_webhook({'event': 'call_started'}, timestamp=int(time.time() * 1000) + age).status_code == 401


def test_tampered_signature_rejected(client, signed_webhook):
    valid = signed_webhook({'event': 'call_started'})
    assert valid.status_code == 204
    request = valid.request
    assert client.post('/retell/webhook', content=b'{"event":"call_analyzed"}', headers=dict(request.headers)).status_code == 401


def test_unconfigured_signing_key_fails_closed(client, monkeypatch):
    monkeypatch.setattr(webhooks, 'RETELL_API_KEY', '')
    assert client.post('/retell/webhook', json={'event': 'call_started'}).status_code == 401


def test_authenticated_unicode_and_duplicate_intake(client, signed_webhook):
    payload = {'event': 'call_analyzed', 'call': {
        'call_id': 'unicode-demo', 'agent_id': 'synthetic-intake-agent', 'transcript': 'Agua en la calle — información',
        'call_analysis': {'custom_analysis_data': {'location_text': 'Unknown place', 'hazard_type': 'flood'}},
    }}
    raw = json.dumps(payload, ensure_ascii=False).encode()
    assert signed_webhook(raw=raw).status_code == 204
    assert signed_webhook(raw=raw).status_code == 204
    with Session(engine) as s:
        reports = s.exec(select(Report).where(Report.call_id == 'unicode-demo')).all()
        assert len(reports) == 1
        assert reports[0].transcript == payload['call']['transcript']
    unknown = next(i for i in state(client)['incidents'] if i['lat'] is None)
    assert any(d['kind'] == 'location' for d in unknown['debts'])


def test_duplicate_signed_callback_preserves_events_and_risk(client, signed_webhook):
    i = incident_id(client)
    payload = {'event': 'call_analyzed', 'call': {
        'call_id': 'callback-retry', 'metadata': {'incident_id': i, 'attempt_no': 1},
        'call_analysis': {'custom_analysis_data': {'outcome': 'worse'}},
    }}
    assert signed_webhook(payload).status_code == 204
    before = client.get(f'/api/incidents/{i}').json()
    assert signed_webhook(payload).status_code == 204
    assert client.get(f'/api/incidents/{i}').json() == before


def test_department_toggle_produces_one_alert_and_suppresses_nudge(client, clock, calls):
    i = incident_id(client)
    client.post('/api/twists/dept_silent', json={'on': True})
    clock.tick()
    alerts = state(client)['alerts']
    assert len(alerts) == 1 and alerts[0]['department'] == 'Street Services'
    events = client.get(f'/api/incidents/{i}').json()['events']
    assert not any(e['type'] == 'nudge' for e in events)
    assert any(e['type'] == 'nudge_suppressed' for e in events)
    # Operational alerts never hide evidence-backed critical review.
    client.post(f'/api/incidents/{i}/simulate-callback', json={'outcome': 'worse'})
    assert len(state(client)['critical_alerts']) == 1
    client.post('/api/twists/dept_silent', json={'on': False})
    assert state(client)['alerts'] == []


def test_real_department_threshold_and_acceptance_clear_alert(client):
    with Session(engine) as s:
        for n in range(4):
            # Five distinct incidents, not five history rows for one handoff.
            case = Incident(title=f'Synthetic threshold case {n}', hazard_type='pothole')
            s.add(case)
            s.flush()
            s.add(Assignment(incident_id=case.id, department='Street Services'))
        s.commit()
    assert len(state(client)['alerts']) == 1
    with Session(engine) as s:
        a = s.exec(select(Assignment)).first()
        a.accepted_at = utcnow()
        s.add(a)
        s.commit()
    assert state(client)['alerts'] == []


def test_surge_retains_50_reports_in_four_clusters_and_is_idempotent(client):
    response = client.post('/api/twists/surge', json={'on': True})
    assert response.status_code == 200
    s = response.json()
    assert sum(i['report_count'] for i in s['incidents']) == 53
    assert len(s['incidents']) == 5  # Original storm plus four synthetic surge clusters.
    client.post('/api/twists/surge', json={'on': True})
    client.post('/api/twists/surge', json={'on': False})
    client.post('/api/twists/surge', json={'on': True})
    assert sum(i['report_count'] for i in state(client)['incidents']) == 53
    client.post('/api/demo/reset', json={'seed': 'storm_night'})
    s = state(client)
    assert s['twists']['surge'] is False and sum(i['report_count'] for i in s['incidents']) == 3


@pytest.mark.parametrize('domain', ['nonsense', 'port', '', None])
def test_unsupported_domain_rejected_without_mutation(client, domain):
    before = state(client)['twists']
    assert client.post('/api/twists/domain', json={'domain': domain}).status_code == 404
    assert state(client)['twists'] == before


def test_supported_domain_is_accepted(client):
    assert client.post('/api/twists/domain', json={'domain': 'storm'}).status_code == 200


def test_phones_down_never_places_call_or_increases_physical_risk(client, calls, clock):
    before = state(client)['incidents'][0]['risk_score']
    client.post('/api/twists/phones_down', json={'on': True})
    clock.tick(3)
    assert calls == []
    i = state(client)['incidents'][0]
    assert i['risk_score'] == before and i['status'] != 'closed'
    assert any(d['kind'] == 'caller_unreachable' for d in i['debts'])
    d = client.get(f"/api/incidents/{i['id']}").json()
    assert d['callbacks'][0]['outcome'] == 'no_answer'
