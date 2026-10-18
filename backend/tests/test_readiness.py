"""Deeper integration probes. Failures stay visible, never marked XFAIL."""
import json
import math
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, select

from app.contracts import CallbackOutcome, ReportIn
from app.db import engine
from app.engine import ladder, seeds
from app.engine.ingest import ingest_report
from app.models import Callback, Report
from app.voice import simulator


def state(client):
    return client.get('/api/state').json()


def add(call_id, **kwargs):
    fields = dict(source='seed', call_id=call_id, hazard_type='pothole',
                  lat=35.0, lng=-117.0, created_at=datetime.now(timezone.utc))
    fields.update(kwargs)
    rid = ingest_report(ReportIn(**fields))
    with Session(engine) as s:
        return s.get(Report, rid).incident_id


@pytest.mark.parametrize('metres,links', [(0, True), (299.9, True), (300.1, False), (1000, False)])
def test_link_distance_boundary(client, metres, links):
    first = add('distance-first')
    second = add('distance-second', lat=35.0 + math.degrees(metres / 6_371_000))
    assert (first == second) is links


@pytest.mark.parametrize('seconds,links', [(3599, True), (3600, True), (3601, False), (-3601, False)])
def test_link_time_boundary(client, seconds, links):
    now = datetime.now(timezone.utc)
    first = add('time-first', created_at=now)
    second = add('time-second', created_at=now + timedelta(seconds=seconds))
    assert (first == second) is links


def test_link_anchor_prevents_distance_chain_drift(client):
    first = add('anchor')
    second = add('middle', lat=35.0 + math.degrees(250 / 6_371_000))
    third = add('drift', lat=35.0 + math.degrees(500 / 6_371_000))
    assert first == second and third != first


def test_closed_incident_cannot_absorb_new_report(client):
    first = add('closed-first')
    client.post(f'/api/incidents/{first}/close', json={'by': 'Demo operator'})
    assert add('closed-second') != first


@pytest.mark.parametrize('consent', [None, False, 'false', 'no', 'unknown', 0])
def test_missing_or_negative_webhook_consent_never_calls(client, signed_webhook, calls, clock, consent):
    payload = {'event': 'call_analyzed', 'call': {
        'call_id': 'consent-probe', 'from_number': '+13235550188',
        'call_analysis': {'custom_analysis_data': {
            'hazard_type': 'pothole', 'location_text': 'Figueroa and Avenue 57', 'callback_ok': consent,
        }},
    }}
    assert signed_webhook(payload).status_code == 204
    clock.tick(3)
    target = next(i for i in state(client)['incidents'] if i['hazard_type'] == 'pothole')
    assert all(c['incident_id'] != target['id'] for c in calls)
    assert any(d['kind'] == 'consent_unknown' for d in target['debts'])


def test_provider_timeout_records_unknown_without_risk_increase(client, monkeypatch, clock):
    from app.voice import callbacks
    def fail(*args, **kwargs):
        raise TimeoutError('Synthetic provider timeout')
    monkeypatch.setattr(callbacks, 'request_callback', fail)
    clock.tick(3)
    i = state(client)['incidents'][0]
    assert i['risk_score'] == 70 and i['status'] != 'closed'
    detail = client.get(f"/api/incidents/{i['id']}").json()
    assert detail['callbacks'][0]['outcome'] == 'no_answer'


def test_second_missed_call_clears_retry_timer_at_cap(client, calls, clock):
    i = state(client)['incidents'][0]['id']
    clock.tick(3)
    ladder.record_callback_outcome(CallbackOutcome(incident_id=i, call_id='test-call-1', attempt_no=1, outcome='no_answer'))
    clock.tick()
    ladder.record_callback_outcome(CallbackOutcome(incident_id=i, call_id='test-call-2', attempt_no=2, outcome='no_answer'))
    clock.tick(3)
    assert len(calls) == 2
    assert client.get(f'/api/incidents/{i}').json()['next_step_at'] is None


@pytest.mark.parametrize('bad', [None, [], {}, {'reports': []}, {'reports': [None]},
    {'reports': [{'call_id': 'duplicate', 'hazard_type': 'flood'}] * 2}])
def test_invalid_scenario_structure_preserves_data(client, monkeypatch, tmp_path, bad):
    (tmp_path / 'invalid.json').write_text(json.dumps(bad))
    monkeypatch.setattr(seeds, 'SEEDS_DIR', tmp_path)
    before = state(client)['incidents']
    assert client.post('/api/demo/reset', json={'seed': 'invalid'}).status_code == 404
    assert state(client)['incidents'] == before


def test_partial_coordinates_do_not_crash_ingestion(client):
    add('partial-first', lng=None, location_text=None)
    add('partial-second', location_text=None)


def test_pending_simulator_callback_cannot_mutate_reset_incident(client, monkeypatch, clock):
    captured = []
    class DeferredTimer:
        def __init__(self, delay, fn, args):
            captured.append((fn, args))
        def start(self):
            pass
    monkeypatch.setattr(simulator.threading, 'Timer', DeferredTimer)
    i = state(client)['incidents'][0]['id']
    clock.tick(3)
    assert len(captured) == 1
    assert len(client.get(f'/api/incidents/{i}').json()['callbacks']) == 1
    assert client.post('/api/demo/reset', json={'seed': 'storm_night'}).status_code == 200
    before = client.get(f'/api/incidents/{i}').json()
    fn, args = captured[0]
    fn(*args)
    assert client.get(f'/api/incidents/{i}').json() == before


def test_callback_call_id_cannot_be_reassigned_to_another_incident(client):
    original = state(client)['incidents'][0]['id']
    other = add('other-case')
    with Session(engine) as s:
        s.add(Callback(incident_id=original, call_id='bound-call', attempt_no=1))
        s.commit()
    before = client.get(f'/api/incidents/{other}').json()
    ladder.record_callback_outcome(CallbackOutcome(incident_id=other, call_id='bound-call', attempt_no=1, outcome='worse'))
    assert client.get(f'/api/incidents/{other}').json() == before
    with Session(engine) as s:
        callback = s.exec(select(Callback).where(Callback.call_id == 'bound-call')).one()
        assert callback.outcome is None


def test_same_call_attempt_is_not_applied_twice_under_different_ids(client):
    i = state(client)['incidents'][0]['id']
    ladder.record_callback_outcome(CallbackOutcome(incident_id=i, call_id='attempt-a', attempt_no=1, outcome='worse'))
    before = client.get(f'/api/incidents/{i}').json()
    ladder.record_callback_outcome(CallbackOutcome(incident_id=i, call_id='attempt-b', attempt_no=1, outcome='better'))
    assert client.get(f'/api/incidents/{i}').json() == before


@pytest.mark.parametrize('transcript', ['Nobody is trapped.', 'The driver is not trapped.', 'No child is injured.'])
def test_negated_danger_does_not_count_as_confirmed_evidence(client, transcript):
    word = 'injured' if 'injured' in transcript else 'trapped'
    i = add('negated-danger', transcript=transcript, danger_words=[word])
    assert client.get(f'/api/incidents/{i}').json()['risk_score'] == 5


def test_real_simulator_delivers_outcome_without_network(client, monkeypatch, clock):
    import time
    from app.voice import callbacks
    def forbidden(*args, **kwargs):
        raise AssertionError('Simulation attempted external HTTP')
    monkeypatch.setattr(callbacks.httpx, 'post', forbidden)
    monkeypatch.setattr(simulator, 'SIMULATED_DELAY_S', 0.02)
    clock.tick(3)
    i = state(client)['incidents'][0]['id']
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        detail = client.get(f'/api/incidents/{i}').json()
        # A polling response can straddle the background callback commit. Wait
        # for the complete expected projection, not just its callback row.
        if detail['callbacks'] and detail['callbacks'][0]['outcome'] is not None and detail['critical']:
            break
        time.sleep(0.02)
    assert detail['callbacks'][0]['outcome'] == 'worse'
    assert detail['critical'] is True


def test_revoked_consent_prevents_retry(client, calls, clock):
    i = state(client)['incidents'][0]['id']
    clock.tick(3)
    ladder.record_callback_outcome(CallbackOutcome(incident_id=i, call_id='test-call-1', attempt_no=1, outcome='no_answer'))
    with Session(engine) as s:
        for r in s.exec(select(Report).where(Report.incident_id == i)):
            r.callback_ok = False
            s.add(r)
        s.commit()
    clock.tick(3)
    assert len(calls) == 1
    assert any(d['kind'] == 'consent_unknown' for d in state(client)['incidents'][0]['debts'])


def test_same_schema_app_restart_preserves_evidence(client):
    from fastapi.testclient import TestClient
    from app.main import app
    i = state(client)['incidents'][0]['id']
    client.post(f'/api/incidents/{i}/simulate-callback', json={'outcome': 'worse'})
    before = client.get(f'/api/incidents/{i}').json()
    with TestClient(app) as restarted:
        assert restarted.get(f'/api/incidents/{i}').json() == before


@pytest.mark.parametrize('lat,lng', [(35.0, None), (None, -117.0)])
def test_partial_coordinate_pair_opens_location_debt(client, lat, lng):
    i = add('partial-pair', lat=lat, lng=lng, location_text=None)
    detail = client.get(f'/api/incidents/{i}').json()
    assert detail['lat'] is None and detail['lng'] is None
    assert any(d['kind'] == 'location' for d in detail['debts'])


def test_existing_callback_wrong_attempt_is_ignored(client):
    i = state(client)['incidents'][0]['id']
    with Session(engine) as s:
        s.add(Callback(incident_id=i, call_id='attempt-bound', attempt_no=1))
        s.commit()
    before = client.get(f'/api/incidents/{i}').json()
    ladder.record_callback_outcome(CallbackOutcome(incident_id=i, call_id='attempt-bound', attempt_no=2, outcome='worse'))
    assert client.get(f'/api/incidents/{i}').json() == before


@pytest.mark.parametrize('transcript,phrases,expected', [
    ('The car is not stuck.', ['car stuck'], 5),
    ('No one is trapped, but the water is rising.', ['trapped', 'rising'], 30),
    ('The driver is trapped.', ['trapped'], 30),
    ("The driver can't get out.", ["can't get out"], 30),
    ('The driver is not only trapped but injured.', ['trapped'], 30),
])
def test_danger_negation_preserves_affirmative_evidence(client, transcript, phrases, expected):
    i = add('danger-contrast', transcript=transcript, danger_words=phrases)
    assert client.get(f'/api/incidents/{i}').json()['risk_score'] == expected
