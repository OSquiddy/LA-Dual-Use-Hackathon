"""Retell evidence boundaries and explicit per-report consent; synthetic data only."""
import json

import pytest
from sqlmodel import Session, select

from app.api import routes
from app.db import engine
from app.models import Callback, Debt, Event, Incident, Report

MISSING = object()
KEY = "synthetic-reviewer-test-key"


def intake(signed_webhook, *, consent=MISSING, phone=None, transcript="User: There might be injuries near roadway water.", danger=True, words=None, call_id="evidence-intake"):
    fields = {"location_text": "Unmapped synthetic street", "hazard_type": "water_on_road",
              "danger_words": ["injured"] if words is None else words, "anyone_in_danger": danger}
    if consent is not MISSING:
        fields["callback_ok"] = consent
    payload = {"event": "call_analyzed", "call": {"call_id": call_id, "transcript": transcript,
               "call_analysis": {"custom_analysis_data": fields}}}
    if phone is not None:
        payload["call"]["from_number"] = phone
    assert signed_webhook(payload).status_code == 204
    with Session(engine) as s:
        report = s.exec(select(Report).where(Report.call_id == call_id)).one()
        return report.incident_id, report.id


@pytest.fixture
def reviewer(monkeypatch):
    monkeypatch.setattr(routes, "REVIEWER_API_KEY", KEY)
    return {"Authorization": f"Bearer {KEY}"}


def test_long_transcript_is_preserved_but_absent_from_every_dashboard_projection(client, signed_webhook, reviewer):
    transcript = "Agent: Are you injured?\nUser: There may be injuries near roadway water.\n" + "User: PRIVATE FULL CONVERSATION\n" * 1000
    i, report_id = intake(signed_webhook, transcript=transcript)
    state = client.get('/api/state').json()
    alert = next(a for a in state['critical_alerts'] if a['incident_id'] == i)
    assert alert['quote'] == ''
    assert 'possible injuries' in alert['reason'] and 'unverified' in alert['reason']
    assert len(alert['reason']) < 200 and alert['evidence'] == [f'report:{report_id}']
    detail = client.get(f'/api/incidents/{i}').json()
    assert detail['reports'][0]['transcript'] == ''
    assert 'PRIVATE FULL CONVERSATION' not in json.dumps([state, detail])
    assert all(len(e['reason']) < 320 for e in detail['events'])
    response = client.get(f'/api/incidents/{i}/evidence', headers=reviewer)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    assert response.json()['reports'][0]['transcript'] == transcript
    with Session(engine) as s:
        assert s.get(Report, report_id).transcript == transcript
        assert s.get(Incident, i).critical_quote == ''
        assert all('PRIVATE FULL CONVERSATION' not in e.reason for e in s.exec(select(Event).where(Event.incident_id == i)))


@pytest.mark.parametrize('transcript,words,expected', [
    ('Agent: Is anyone injured or trapped?\nUser: I cannot tell.', ['injured', 'trapped'], 'Specific danger is unconfirmed'),
    ('User: Nobody is injured. Nobody is trapped.', ['injured', 'trapped'], 'Specific danger is unconfirmed'),
    ('Agent: Anyone hurt?\nUser: There may be injuries.', ['injured'], 'possible injuries'),
    ('User: A person may be trapped.', ['trapped'], 'possibly trapped'),
    ('User: Water is rising.', ['rising'], 'possibly rising water'),
])
def test_summary_preserves_uncertainty_and_uses_caller_not_agent_evidence(client, signed_webhook, transcript, words, expected):
    i, _ = intake(signed_webhook, transcript=transcript, words=words)
    reason = next(a['reason'] for a in client.get('/api/state').json()['critical_alerts'] if a['incident_id'] == i)
    assert expected in reason
    assert 'confirmed injuries' not in reason and 'Agent:' not in reason


def test_agent_questions_alone_cannot_raise_danger_risk(client, signed_webhook):
    i, _ = intake(signed_webhook, transcript='Agent: Are you trapped?\nUser: I do not know.', words=['trapped'], danger=False)
    detail = client.get(f'/api/incidents/{i}').json()
    assert detail['risk_score'] == 25 and detail['critical'] is False


@pytest.mark.parametrize('consent,expected', [(True, True), (False, False), (MISSING, False), (None, False), ('true', False), ('yes', False), (1, False)])
def test_explicit_extracted_consent_is_persisted_per_report_without_transcript_inference(client, signed_webhook, reviewer, consent, expected):
    transcript = 'Agent: May an AI agent call you back?\nUser: Yes, you may call me back.'
    i, report_id = intake(signed_webhook, consent=consent, transcript=transcript)
    with Session(engine) as s:
        report = s.get(Report, report_id)
        assert report.callback_ok is expected
        assert report.transcript == transcript
    for path, headers in [(f'/api/incidents/{i}', {}), (f'/api/incidents/{i}/evidence', reviewer)]:
        assert client.get(path, headers=headers).json()['reports'][0]['callback_ok'] is expected


@pytest.mark.parametrize('phone', [None, '', '   '])
def test_consented_web_call_without_number_does_not_claim_permission_was_denied(client, signed_webhook, calls, clock, phone):
    i, _ = intake(signed_webhook, consent=True, phone=phone)
    clock.tick(3)
    detail = client.get(f'/api/incidents/{i}').json()
    assert detail['reports'][0]['callback_ok'] is True
    assert detail['reports'][0]['phone'] is None
    assert any(d['kind'] == 'callback_number_missing' for d in detail['debts'])
    assert not any(d['kind'] == 'consent_unknown' for d in detail['debts'])
    assert not any(c['incident_id'] == i for c in calls)
    assert 'no callback permission' not in json.dumps(detail).lower()
    with Session(engine) as s:
        assert not s.exec(select(Debt).where(Debt.incident_id == i, Debt.kind == 'consent_unknown', Debt.cleared_at == None)).all()  # noqa: E711


def test_consented_number_remains_eligible_but_other_report_does_not_inherit_permission(client, signed_webhook, calls, clock):
    i, _ = intake(signed_webhook, consent=True, phone='+13235550180', danger=False)
    intake(signed_webhook, consent=False, phone='+13235550181', danger=False, call_id='declining-witness')
    clock.tick(3)
    assert next(c for c in calls if c['incident_id'] == i)['phone'] == '+13235550180'
    with Session(engine) as s:
        assert s.exec(select(Report).where(Report.call_id == 'declining-witness')).one().callback_ok is False


def test_legacy_quote_and_incorrect_contact_debt_are_projected_safely_without_rewriting_sources(client, signed_webhook, reviewer):
    transcript = 'User: There might be injuries.\nPRIVATE LEGACY CONVERSATION'
    i, report_id = intake(signed_webhook, consent=True, transcript=transcript)
    with Session(engine) as s:
        incident = s.get(Incident, i)
        incident.critical_quote = transcript
        incident.critical_reason = transcript
        s.add(Debt(incident_id=i, kind='consent_unknown', label='No callback permission'))
        s.add(Event(incident_id=i, type='callback', reason=transcript))
        s.commit()
    detail = client.get(f'/api/incidents/{i}').json()
    state = client.get('/api/state').json()
    assert 'PRIVATE LEGACY' not in json.dumps([state, detail])
    assert 'consent_unknown' not in [d['kind'] for d in detail['debts']]
    assert 'callback_number_missing' in [d['kind'] for d in detail['debts']]
    with Session(engine) as s:
        assert s.get(Report, report_id).transcript == transcript
        assert s.get(Incident, i).critical_quote == transcript


def test_callback_summary_is_evidence_not_an_event_or_alert_reason(client, signed_webhook, reviewer):
    i = client.get('/api/state').json()['incidents'][0]['id']
    summary = 'Agent: PRIVATE CALLBACK CONVERSATION\nUser: ' + 'water rising ' * 1000
    payload = {'event': 'call_analyzed', 'call': {'call_id': 'callback-private', 'metadata': {'incident_id': i},
               'call_analysis': {'custom_analysis_data': {'outcome': 'worse', 'anyone_in_danger': True, 'summary': summary}}}}
    assert signed_webhook(payload).status_code == 204
    assert 'PRIVATE CALLBACK' not in json.dumps([client.get('/api/state').json(), client.get(f'/api/incidents/{i}').json()])
    assert client.get(f'/api/incidents/{i}/evidence', headers=reviewer).json()['callbacks'][0]['summary'] == summary
    with Session(engine) as s:
        assert s.exec(select(Callback).where(Callback.call_id == 'callback-private')).one().summary == summary
        assert all('PRIVATE CALLBACK' not in e.reason for e in s.exec(select(Event).where(Event.incident_id == i)))


@pytest.mark.parametrize('authorization', [None, 'Bearer wrong-key', 'Basic synthetic-reviewer-test-key'])
def test_evidence_requires_reviewer_authorization(client, reviewer, authorization):
    headers = {'Authorization': authorization} if authorization else {}
    assert client.get('/api/incidents/1/evidence', headers=headers).status_code == 401
    assert client.get('/api/incidents/999999/evidence', headers=headers).status_code == 401


def test_unconfigured_reviewer_access_fails_closed_and_preserves_every_report(client, monkeypatch):
    monkeypatch.setattr(routes, 'REVIEWER_API_KEY', '')
    before = client.get('/api/incidents/1').json()
    assert client.get('/api/incidents/1/evidence', headers={'Authorization': f'Bearer {KEY}'}).status_code == 503
    assert client.get('/api/incidents/1').json() == before


def test_simulation_response_does_not_bypass_evidence_authorization(client):
    response = client.post('/api/incidents/1/simulate-callback', json={'outcome': 'worse'})
    assert response.status_code == 200
    assert all(r['transcript'] == '' for r in response.json()['reports'])


def test_high_risk_missing_number_is_uncertainty_without_claiming_worsening(client, signed_webhook, calls, clock):
    i, _ = intake(signed_webhook, consent=True, danger=False)
    with Session(engine) as s:
        incident = s.get(Incident, i)
        incident.risk_score = 65
        s.commit()
    clock.tick(3)
    alert = next(a for a in client.get('/api/state').json()['critical_alerts'] if a['incident_id'] == i)
    assert 'callback number missing' in alert['reason'] and 'unknown' in alert['reason']
    assert 'worse' not in alert['reason'] and 'permission' not in alert['reason']


def test_persistent_uncertainty_alert_does_not_misstate_acceptance_or_new_contact_information(client, signed_webhook, calls, clock):
    i, report_id = intake(signed_webhook, consent=True, danger=False)
    with Session(engine) as s:
        incident = s.get(Incident, i)
        incident.risk_score = 65
        s.commit()
    clock.tick(3)
    assert client.post(f'/api/incidents/{i}/accept', json={'owner': 'Synthetic reviewer'}).status_code == 200
    with Session(engine) as s:
        report = s.get(Report, report_id)
        report.phone = '+13235550180'
        s.commit()
    alert = next(a for a in client.get('/api/state').json()['critical_alerts'] if a['incident_id'] == i)
    assert alert['accepted'] is True and 'responsibility accepted' in alert['reason']
    assert 'still unaccepted' not in alert['reason'] and 'unreachable' not in alert['reason']
    assert 'number missing' not in alert['reason'] and 'unknown' in alert['reason']
