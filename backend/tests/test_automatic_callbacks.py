"""Isolated callback lifecycle regressions. No provider requests or local production DB writes."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import httpx
import pytest
from sqlmodel import Session, select

from app import db
from app.contracts import CallbackOutcome, ReportIn
from app.engine import callback_jobs, contact, ladder
from app.engine.ingest import ingest_report
from app.models import Callback, Incident, Report
from app.timeutil import utcnow
from app.voice import callbacks, simulator


def detail(client):
    return client.get('/api/incidents/1').json()


def result(outcome='same', **call_fields):
    return {'event': 'call_analyzed', 'call': {
        'call_id': 'test-call-1', 'metadata': {'incident_id': 1, 'attempt_no': 1},
        'call_analysis': {'custom_analysis_data': {'outcome': outcome}}, **call_fields,
    }}


def consenting_intake():
    return ingest_report(ReportIn(source='retell', call_id='synthetic-real-intake', hazard_type='flood',
        location_text='Figueroa and Avenue fifty two', phone='+13235550103', callback_ok=True, created_at=utcnow()))


@pytest.mark.parametrize('permission', [True, False, None, 'true', 'yes', 1, 0, {}, []])
def test_consent_is_only_explicit_boolean_true(permission):
    r = ReportIn(source='retell', call_id='strict-consent', hazard_type='other', created_at=utcnow(), callback_ok=permission)
    assert r.callback_ok is (permission is True)


@pytest.mark.parametrize('consent,phone,allowed', [
    (True, '+13235550177', True), (False, '+13235550177', False),
    (True, None, False), (True, '3235550177', False), (True, '+01235550177', False),
    (True, '+13235550177 extra', False), (True, '+1234567890123456', False),
])
def test_automatic_dispatch_checks_stored_consent_and_number(client, calls, clock, consent, phone, allowed):
    with Session(db.engine) as s:
        for r in s.exec(select(Report)):
            r.callback_ok, r.phone = consent, phone
        s.commit()
    clock.tick(3)
    assert len(calls) == int(allowed)
    assert all(c['phone'] == phone for c in calls)


def test_assignment_and_acknowledgment_do_not_skip_deadline(client, calls):
    with Session(db.engine) as s:
        due = s.get(Incident, 1).next_step_at
    from app.timeutil import from_db
    due = from_db(due)
    ladder.tick(due - timedelta(seconds=1))
    assert calls == []
    ladder.tick(due)
    assert detail(client)['ladder_step'] == 2 and not calls
    ladder.tick(due + timedelta(seconds=15))
    assert detail(client)['owner'] and not detail(client)['accepted'] and not calls
    assert client.post('/api/incidents/1/acknowledge', json={'by': 'Synthetic operator'}).status_code == 200
    ladder.tick(due + timedelta(seconds=29))
    assert not calls
    ladder.tick(due + timedelta(seconds=30))
    assert len(calls) == 1
    ladder.tick(due + timedelta(seconds=30))
    assert len(calls) == 1


@pytest.mark.parametrize('action,body', [('accept', {'owner': 'Synthetic operator'}), ('close', {'by': 'Synthetic reviewer'})])
def test_human_action_cancels_durable_pending_attempt(client, calls, action, body):
    with Session(db.engine) as s:
        callback_jobs.enqueue(s, s.get(Incident, 1))
        s.commit()
    assert client.post('/api/incidents/1/' + action, json=body).status_code == 200
    callback_jobs.dispatch_due()
    assert not calls
    assert detail(client)['callbacks'][0]['state'] == 'cancelled'


def test_concurrent_controlled_requests_only_dispatch_once(client, calls):
    def send(_):
        return client.post('/api/incidents/1/request-callback', json={'by': 'Synthetic reviewer'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(send, range(2))) == [200, 409]
    assert len(calls) == 1
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda _: callback_jobs.dispatch_due(), range(3)))
    assert len(calls) == 1


@pytest.mark.parametrize('path,body', [
    ('/api/incidents/1/request-callback', {'by': 'Synthetic operator'}),
    ('/api/incidents/1/accept', {'owner': 'Synthetic operator'}),
    ('/api/incidents/1/acknowledge', {'by': 'Synthetic operator'}),
    ('/api/incidents/1/close', {'by': 'Synthetic operator'}),
    ('/api/reports/1/callback-opt-out', {'by': 'Synthetic operator'}),
    ('/api/incidents/1/simulate-callback', {'outcome': 'same'}),
])
def test_controlled_actions_require_authorization(client, path, body):
    assert client.post(path, json=body, headers={'Authorization': ''}).status_code == 401


def test_request_cannot_choose_an_arbitrary_phone(client, calls):
    assert client.post('/api/incidents/1/request-callback', json={'by': 'Synthetic operator', 'phone': '+13235550999'}).status_code == 200
    assert calls[0]['phone'] == '+13235550103'


@pytest.mark.parametrize('outcome,delta,critical', [('worse', 30, True), ('same', 0, False), ('better', -10, False)])
def test_signed_result_is_once_only_and_preserves_evidence(client, calls, clock, signed_webhook, outcome, delta, critical):
    before = detail(client)['risk_score']
    clock.tick(3)
    payload = result(outcome, transcript='Agent: PRIVATE CALLBACK\nUser: uncertain condition',
                     call_analysis={'custom_analysis_data': {'outcome': outcome, 'summary': 'PRIVATE SUMMARY ' * 200}})
    assert signed_webhook(payload).status_code == 204
    after = detail(client)
    assert after['risk_score'] == min(100, before + delta)
    assert after['critical'] is critical and after['status'] != 'closed'
    assert after['callbacks'][0]['state'] == 'completed'
    assert 'PRIVATE' not in json.dumps([after, client.get('/api/state').json()])
    evidence = client.get('/api/incidents/1/evidence').json()
    assert evidence['callbacks'][0]['transcript'] == payload['call']['transcript']
    assert 'PRIVATE SUMMARY' in evidence['callbacks'][0]['summary']
    assert signed_webhook(payload).status_code == 204
    assert detail(client) == after


@pytest.mark.parametrize('reason', ['dial_no_answer', 'voicemail_reached', 'dial_busy', 'dial_failed', 'invalid_destination'])
def test_failed_contact_is_unknown_conditions_with_bounded_retry(client, calls, clock, signed_webhook, reason):
    clock.tick(3)
    before = detail(client)['risk_score']
    assert signed_webhook(result(None, disconnection_reason=reason)).status_code == 204
    assert detail(client)['risk_score'] == before
    assert detail(client)['callbacks'][0]['outcome'] == 'no_answer'
    clock.tick()
    assert len(calls) == 2
    payload = result(None, call_id='test-call-2', metadata={'incident_id': 1, 'attempt_no': 2}, disconnection_reason=reason)
    assert signed_webhook(payload).status_code == 204
    clock.tick(5)
    assert len(calls) == 2 and detail(client)['next_step_at'] is None


def test_immediate_danger_escalates_even_when_conditions_same(client, calls, clock, signed_webhook):
    clock.tick(3)
    assert signed_webhook(result('same', call_analysis={'custom_analysis_data': {'outcome': 'same', 'anyone_in_danger': True}})).status_code == 204
    assert detail(client)['critical'] and detail(client)['ladder_step'] == 5


@pytest.mark.parametrize('fields', [{}, {'outcome': 'unexpected'}, {'outcome': 'no_answer'}])
def test_missing_analysis_never_invents_a_resident_answer(client, calls, clock, signed_webhook, fields):
    clock.tick(3)
    assert signed_webhook(result(None, call_analysis={'custom_analysis_data': fields})).status_code == 204
    d = detail(client)
    assert d['callbacks'][0]['outcome'] is None and d['callbacks'][0]['state'] == 'unknown'
    assert any(debt['kind'] == 'callback_unknown' for debt in d['debts'])
    clock.tick(5)
    assert len(calls) == 1


@pytest.mark.parametrize('change', ['unknown-call', 'wrong-attempt', 'wrong-case', 'wrong-key'])
def test_signed_callback_needs_a_dispatched_attempt(client, calls, clock, signed_webhook, change):
    clock.tick(3)
    payload = result()
    if change == 'unknown-call': payload['call']['call_id'] = 'unrelated'
    if change == 'wrong-attempt': payload['call']['metadata']['attempt_no'] = 2
    if change == 'wrong-case': payload['call']['metadata']['incident_id'] = 999
    if change == 'wrong-key': payload['call']['metadata']['callback_request_id'] = 'untrusted'
    before = detail(client)
    assert signed_webhook(payload).status_code == 403
    assert detail(client) == before


def test_interrupted_dispatch_is_not_redispatched_but_nonce_can_reconcile(client, calls, signed_webhook):
    with Session(db.engine) as s:
        job = callback_jobs.enqueue(s, s.get(Incident, 1))
        job.state = 'dispatching'
        key = job.request_key
        s.commit()
    callback_jobs.recover_interrupted()
    callback_jobs.dispatch_due()
    assert not calls and detail(client)['callbacks'][0]['state'] == 'unknown'
    assert signed_webhook(result('same', call_id='recovered-provider-call', metadata={
        'incident_id': 1, 'attempt_no': 1, 'callback_request_id': key})).status_code == 204
    assert detail(client)['callbacks'][0]['state'] == 'completed'


def test_provider_timeout_never_redispatches_ambiguous_send(client, monkeypatch, clock):
    sent = []
    def timeout(*args, **kwargs):
        sent.append(1)
        raise httpx.ReadTimeout('synthetic timeout')
    monkeypatch.setattr(callbacks, 'request_callback', timeout)
    clock.tick(10)
    assert len(sent) == 1
    assert detail(client)['callbacks'][0]['state'] == 'unknown'
    assert client.post('/api/incidents/1/request-callback', json={'by': 'Synthetic reviewer'}).status_code == 409


def test_simulated_result_survives_lost_in_memory_timer(client, calls, clock):
    clock.tick(3)
    with Session(db.engine) as s:
        job = s.exec(select(Callback)).one()
        job.result_due_at = utcnow() - timedelta(seconds=1)
        s.commit()
    callback_jobs.finish_simulated_due()
    after = detail(client)
    assert after['callbacks'][0]['outcome'] == simulator.SCRIPTED_ANSWER[0]
    callback_jobs.finish_simulated_due()
    assert detail(client) == after and len(calls) == 1


def test_missing_live_result_becomes_unknown_not_automatic_redial(client, calls, clock):
    clock.tick(3)
    with Session(db.engine) as s:
        job = s.exec(select(Callback)).one()
        job.mode, job.dispatch_started_at = 'live', utcnow() - timedelta(hours=1)
        s.commit()
    callback_jobs.expire_missing_results()
    assert detail(client)['callbacks'][0]['error_code'] == 'result_missing'
    clock.tick(5)
    assert len(calls) == 1


@pytest.mark.parametrize('field', ['callback_opt_out', 'wrong_number'])
def test_opt_out_or_wrong_number_blocks_future_reports_on_same_contact(client, calls, clock, signed_webhook, field):
    clock.tick(3)
    with Session(db.engine) as s:
        phone = s.exec(select(Callback)).one().phone
    assert signed_webhook(result(None, call_analysis={'custom_analysis_data': {field: True}})).status_code == 204
    r = ingest_report(ReportIn(source='retell', call_id='new-consenting-report', hazard_type='other',
                              phone=phone, callback_ok=True, transcript='yes', created_at=utcnow()))
    with Session(db.engine) as s:
        assert not contact.eligible_report(s, s.get(Report, r))
    assert detail(client)['callbacks'][0]['outcome'] is None
    clock.tick(4)
    assert len(calls) == 1


def test_opt_out_before_dispatch_cancels_pending_contact(client, calls):
    with Session(db.engine) as s:
        job = callback_jobs.enqueue(s, s.get(Incident, 1))
        report_id = job.report_id
        s.commit()
    assert client.post(f'/api/reports/{report_id}/callback-opt-out', json={'by': 'Synthetic operator'}).status_code == 200
    callback_jobs.dispatch_due()
    assert not calls and detail(client)['callbacks'][0]['state'] == 'cancelled'


def test_simulation_cannot_reach_the_provider(client, monkeypatch):
    monkeypatch.setattr(callbacks.httpx, 'post', lambda *a, **k: pytest.fail('Simulation reached provider'))
    monkeypatch.setattr(simulator, 'schedule', lambda *a: None)
    response = client.post('/api/incidents/1/request-callback', json={'by': 'Synthetic reviewer'})
    assert response.status_code == 200 and response.json()['callbacks'][0]['mode'] == 'simulate'


def test_live_call_requires_separate_confirmation_and_sends_documented_body(client, monkeypatch):
    consenting_intake()
    # Live path is exercised with a fake HTTP transport and synthetic credentials only.
    monkeypatch.setattr(callbacks, 'CALL_MODE', 'live')
    monkeypatch.setattr(callbacks, 'RETELL_API_KEY', 'synthetic-only-key')
    monkeypatch.setattr(callbacks, 'RETELL_FROM_NUMBER', '+13235550188')
    monkeypatch.setattr(callbacks, 'RETELL_CALLBACK_AGENT_ID', 'synthetic-callback-agent')
    seen = []
    def post(url, **kwargs):
        seen.append((url, kwargs))
        return httpx.Response(201, json={'call_id': 'synthetic-live-id'}, request=httpx.Request('POST', url))
    monkeypatch.setattr(callbacks.httpx, 'post', post)
    assert client.post('/api/incidents/1/request-callback', json={'by': 'Synthetic reviewer'}).status_code == 409
    assert not seen
    response = client.post('/api/incidents/1/request-callback', json={'by': 'Synthetic reviewer', 'confirm_live': True})
    assert response.status_code == 200 and len(seen) == 1
    url, request = seen[0]
    body = request['json']
    assert url == 'https://api.retellai.com/v2/create-phone-call'
    assert body['from_number'] == '+13235550188' and body['to_number'] == '+13235550103'
    assert body['override_agent_id'] == 'synthetic-callback-agent'
    assert body['override_agent_version'] == 'latest_published'
    assert body['honor_internal_dnc'] is True
    assert body['metadata']['incident_id'] == 1 and body['metadata']['attempt_no'] == 1
    assert body['idempotency_key'] == body['metadata']['callback_request_id']
    assert set(body['retell_llm_dynamic_variables']) == {'hazard', 'location'}
    assert request['headers']['Authorization'] == 'Bearer synthetic-only-key'


def test_live_automation_remains_disabled_without_separate_gate(client, calls, clock, monkeypatch):
    monkeypatch.setattr(callbacks, 'CALL_MODE', 'live')
    monkeypatch.setattr(callback_jobs, 'LIVE_CALLBACKS_ENABLED', False)
    clock.tick(5)
    assert not calls and not detail(client)['callbacks']


def test_controlled_request_never_drains_other_scheduled_contacts(client, calls):
    report_id = ingest_report(ReportIn(source='retell', call_id='other-contact', hazard_type='outage',
        location_text='Unknown remote block', phone='+13235550177', callback_ok=True, created_at=utcnow()))
    with Session(db.engine) as s:
        other = s.get(Incident, s.get(Report, report_id).incident_id)
        job = callback_jobs.enqueue(s, other)
        job_id = job.id
        s.commit()
    assert client.post('/api/incidents/1/request-callback', json={'by': 'Synthetic reviewer'}).status_code == 200
    assert len(calls) == 1 and calls[0]['incident_id'] == 1
    with Session(db.engine) as s:
        assert s.get(Callback, job_id).state == 'scheduled'


def test_queued_automatic_live_attempt_is_cancelled_when_live_gate_disabled(client, calls, monkeypatch):
    consenting_intake()
    with Session(db.engine) as s:
        job = callback_jobs.enqueue(s, s.get(Incident, 1), automatic=True)
        job.mode, job.live_authorized = 'live', True
        s.commit()
    monkeypatch.setattr(callbacks, 'CALL_MODE', 'live')
    monkeypatch.setattr(callback_jobs, 'LIVE_CALLBACKS_ENABLED', False)
    callback_jobs.dispatch_due()
    assert not calls and detail(client)['callbacks'][0]['state'] == 'cancelled'


def test_fast_correlated_missing_analysis_is_not_overwritten_as_calling(client, monkeypatch):
    def fast_result(incident_id, phone, attempt_no, variables, *, request_key):
        ladder.record_verified_callback_outcome(CallbackOutcome(incident_id=incident_id, attempt_no=attempt_no,
            call_id='fast-result', request_key=request_key))
        return 'fast-result'
    monkeypatch.setattr(callbacks, 'request_callback', fast_result)
    assert client.post('/api/incidents/1/request-callback', json={'by': 'Synthetic reviewer'}).status_code == 200
    assert detail(client)['callbacks'][0]['state'] == 'unknown'
    assert detail(client)['callbacks'][0]['error_code'] == 'analysis_missing'


def test_voicemail_cannot_create_danger_evidence_from_extraction(client, calls, clock, signed_webhook):
    clock.tick(3)
    assert signed_webhook(result('worse', disconnection_reason='voicemail_reached',
        call_analysis={'custom_analysis_data': {'outcome': 'worse', 'anyone_in_danger': True}})).status_code == 204
    callback = detail(client)['callbacks'][0]
    assert callback['outcome'] == 'no_answer' and not callback['danger']


def test_live_misconfiguration_is_rejected_before_creating_dispatch(client, monkeypatch):
    consenting_intake()
    monkeypatch.setattr(callbacks, 'CALL_MODE', 'live')
    monkeypatch.setattr(callbacks, 'RETELL_FROM_NUMBER', '')
    assert client.post('/api/incidents/1/request-callback', json={'by': 'Synthetic reviewer', 'confirm_live': True}).status_code == 409
    assert not detail(client)['callbacks']


def test_fictional_seed_permission_can_never_authorize_a_live_callback(client, calls, monkeypatch):
    monkeypatch.setattr(callbacks, 'CALL_MODE', 'live')
    assert client.post('/api/incidents/1/request-callback', json={'by': 'Synthetic reviewer', 'confirm_live': True}).status_code == 409
    assert not calls and not detail(client)['callbacks']


def test_synthetic_outcomes_cannot_be_inserted_while_in_live_mode(client, monkeypatch):
    monkeypatch.setattr(callbacks, 'CALL_MODE', 'live')
    assert client.post('/api/incidents/1/simulate-callback', json={'outcome': 'worse'}).status_code == 409
    assert not detail(client)['callbacks']
