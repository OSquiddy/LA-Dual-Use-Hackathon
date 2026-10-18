"""Responsibility follows configuration and recorded human actions, never inferred receipt."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlmodel import Session, select

from app.config import HAZARD_DEPARTMENT
from app.api import routes
from app.contracts import ReportIn
from app.db import engine
from app.engine import oncall
from app.engine.ingest import ingest_report
from app.models import Assignment, Incident, Report
from app.timeutil import utcnow

KEY = 'synthetic-assignment-reviewer-key'
AUTH = {'Authorization': f'Bearer {KEY}'}


@pytest.fixture(autouse=True)
def configured_reassignment_authorization(monkeypatch):
    monkeypatch.setattr(routes, 'REVIEWER_API_KEY', KEY)


def case_id(client):
    return client.get('/api/state').json()['incidents'][0]['id']


def detail(client, i):
    response = client.get(f'/api/incidents/{i}')
    assert response.status_code == 200
    return response.json()


def reassign(client, i, *, department='Urban Forestry', owner=None, expected=None, by='Synthetic supervisor', reason='Route to the configured response team'):
    body = {'department': department, 'owner': owner, 'by': by, 'reason': reason}
    if expected is not None:
        body['expected_assignment_id'] = expected
    return client.post(f'/api/incidents/{i}/reassign', json=body, headers=AUTH)


@pytest.mark.parametrize('hazard,department', sorted(HAZARD_DEPARTMENT.items()))
def test_hazard_routing_and_configured_department_roster(client, calls, clock, hazard, department):
    report_id = ingest_report(ReportIn(source='seed', call_id=f'routing-{hazard}', hazard_type=hazard,
                                     location_text='Figueroa and Avenue 57', created_at=utcnow()))
    with Session(engine) as s:
        i = s.get(Report, report_id).incident_id
    initial = detail(client, i)
    assert initial['department'] == department
    assert initial['owner'] is None and not initial['accepted'] and not initial['acknowledged']
    clock.tick(2)
    current = detail(client, i)
    assert current['owner'] == oncall.default_owner(department, 'Highland Park', i)
    assert current['assignment']['department'] == department
    assert current['assignment']['default_owner_at'] is not None
    assert not current['accepted'] and not current['acknowledged']
    assert current['assignment_history'][0]['owner'] is None
    assert current['assignment_history'][-1] == current['assignment']


def test_current_assignment_metadata_is_identical_in_state_detail_and_critical_lane(client, calls, clock):
    i = case_id(client)
    clock.tick(2)
    client.post(f'/api/incidents/{i}/simulate-callback', json={'outcome': 'worse'})
    state = client.get('/api/state').json()
    row = next(row for row in state['incidents'] if row['id'] == i)
    current = detail(client, i)
    assert row['assignment'] == current['assignment']
    assert row['assignment']['assigned_at'] and row['assignment']['id']
    assert row['assignment']['assigned_by'] == 'engine'
    alert = next(a for a in state['critical_alerts'] if a['incident_id'] == i)
    assert alert['owner'] == row['assignment']['owner'] and alert['accepted'] is False


def test_acknowledgment_is_recorded_on_its_assignment_and_never_transfers_to_new_owner(client, calls, clock):
    i = case_id(client)
    first = detail(client, i)['assignment']
    response = client.post(f'/api/incidents/{i}/acknowledge', json={'by': 'Synthetic clerk', 'expected_assignment_id': first['id']})
    assert response.status_code == 200 and response.json()['acknowledged'] and not response.json()['accepted']
    clock.tick(2)
    current = detail(client, i)
    assert current['assignment']['owner'] and not current['acknowledged'] and not current['accepted']
    assert current['assignment_history'][0]['acknowledged_by'] == 'Synthetic clerk'
    assert current['assignment_history'][0]['acknowledged_at']
    assert any(e['type'] == 'acknowledged' and e['evidence'] == [f"assignment:{first['id']}"] for e in current['events'])


def test_reassignment_preserves_old_acceptance_and_reports_but_requires_new_handoff(client, calls, clock):
    i = case_id(client)
    clock.tick(2)
    person = detail(client, i)['owner']
    client.post(f'/api/incidents/{i}/acknowledge', json={'by': person})
    client.post(f'/api/incidents/{i}/accept', json={'owner': person})
    before = detail(client, i)
    with Session(engine) as s:
        evidence = [(r.id, r.transcript, r.callback_ok) for r in s.exec(select(Report))]
    target = oncall.default_owner('Urban Forestry', 'Highland Park')
    response = reassign(client, i, owner=target, expected=before['assignment']['id'])
    assert response.status_code == 200
    after = response.json()
    assert after['department'] == 'Urban Forestry' and after['owner'] == target
    assert after['status'] == 'open' and not after['accepted'] and not after['acknowledged']
    assert after['next_step_at'] and after['risk_score'] == before['risk_score']
    assert before['assignment'] in after['assignment_history']
    assert after['assignment']['assigned_by'] == 'Synthetic supervisor'
    assert any(e['type'] == 'reassigned' and e['actor'] == 'Synthetic supervisor' for e in after['events'])
    with Session(engine) as s:
        assert [(r.id, r.transcript, r.callback_ok) for r in s.exec(select(Report))] == evidence


def test_named_acceptance_retains_the_previous_individual_in_history(client, calls, clock):
    i = case_id(client)
    clock.tick(2)
    old = detail(client, i)['assignment']
    response = client.post(f'/api/incidents/{i}/accept', json={'owner': 'Synthetic accepting person', 'expected_assignment_id': old['id']})
    assert response.status_code == 200
    current = detail(client, i)
    assert current['assignment']['accepted_by'] == 'Synthetic accepting person'
    assert current['assignment']['accepted_at'] and current['status'] == 'accepted'
    assert not current['acknowledged']  # Acceptance never invents a receipt event.
    assert old in current['assignment_history']
    assert any(e['type'] == 'accepted' and e['evidence'] == [f"assignment:{current['assignment']['id']}"] for e in current['events'])


def test_human_acceptance_and_acknowledgment_are_idempotent(client):
    i = case_id(client)
    for action, body in [('acknowledge', {'by': 'Synthetic operator'}), ('accept', {'owner': 'Synthetic operator'})]:
        assert client.post(f'/api/incidents/{i}/{action}', json=body).status_code == 200
        before = detail(client, i)
        assert client.post(f'/api/incidents/{i}/{action}', json=body).status_code == 200
        assert detail(client, i) == before


@pytest.mark.parametrize('department,owner', [('Made-up department', None), ('Urban Forestry', 'J. Ramirez (on-call)'), ('Street Services', 'Invented person')])
def test_reassignment_rejects_unknown_department_or_wrong_roster_without_mutation(client, department, owner):
    i = case_id(client)
    before = detail(client, i)
    assert reassign(client, i, department=department, owner=owner).status_code == 422
    assert detail(client, i) == before


@pytest.mark.parametrize('by,reason', [('  ', 'Reason'), ('Synthetic\noperator', 'Reason'), ('Synthetic operator', '   '), ('Synthetic operator', 'Agent: line\nUser: line')])
def test_reassignment_requires_named_actor_and_concise_reason(client, by, reason):
    i = case_id(client)
    before = detail(client, i)
    assert reassign(client, i, by=by, reason=reason).status_code == 422
    assert detail(client, i) == before


@pytest.mark.parametrize('action,body', [('acknowledge', {'by': 'Synthetic operator'}), ('accept', {'owner': 'Synthetic operator'}), ('reassign', {'department': 'Urban Forestry', 'by': 'Synthetic operator', 'reason': 'New handoff'})])
def test_stale_assignment_actions_fail_without_touching_new_assignment(client, action, body):
    i = case_id(client)
    old = detail(client, i)['assignment']['id']
    assert reassign(client, i).status_code == 200
    before = detail(client, i)
    response = client.post(f'/api/incidents/{i}/{action}', json={**body, 'expected_assignment_id': old}, headers=AUTH if action == 'reassign' else {})
    assert response.status_code == 409
    assert detail(client, i) == before


def test_concurrent_stale_forms_cannot_both_reassign_one_handoff(client):
    i = case_id(client)
    old = detail(client, i)['assignment']['id']
    def send(department):
        return reassign(client, i, department=department, expected=old).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(send, ['Urban Forestry', 'Power & Water']))
    assert sorted(statuses) == [200, 409]
    assert len(detail(client, i)['assignment_history']) == 2


def test_repeated_identical_assignment_does_not_reset_receipt_or_add_history(client):
    i = case_id(client)
    client.post(f'/api/incidents/{i}/acknowledge', json={'by': 'Synthetic operator'})
    before = detail(client, i)
    assert reassign(client, i, department=before['department'], owner=before['owner']).status_code == 200
    assert detail(client, i) == before


def test_department_metrics_count_incidents_not_assignment_history(client):
    i = case_id(client)
    target = oncall.default_owner('Street Services', 'Highland Park')
    reassign(client, i, department='Street Services', owner=target)
    reassign(client, i, department='Street Services', owner=None)
    client.post(f'/api/incidents/{i}/accept', json={'owner': 'Synthetic operator'})
    department = next(d for d in client.get('/api/state').json()['departments'] if d['name'] == 'Street Services')
    assert department['assigned_1h'] == 1 and department['accepted_1h'] == 1
    assert not department['silent']


def test_explicit_citywide_roster_handles_unknown_area_without_guessing_location(client):
    rid = ingest_report(ReportIn(source='seed', call_id='unknown-area-owner', hazard_type='downed_tree', created_at=utcnow()))
    with Session(engine) as s:
        i = s.get(Report, rid).incident_id
    options = client.get(f'/api/incidents/{i}/assignment-options').json()
    assert options['recommended_department'] == 'Urban Forestry' and options['area'] is None
    assert all(option['owners'] for option in options['departments'])
    assert reassign(client, i, owner=oncall.default_owner('Urban Forestry', None, i)).status_code == 200
    current = detail(client, i)
    assert current['lat'] is None and current['lng'] is None
    assert current['assignment']['roster_area'] == 'Citywide demo coverage'
    assert not current['accepted']


def test_closure_records_actor_and_time_once_and_blocks_reassignment(client):
    i = case_id(client)
    response = client.post(f'/api/incidents/{i}/close', json={'by': 'Synthetic closing reviewer'})
    assert response.status_code == 200
    closed = response.json()
    assert closed['status'] == 'closed' and closed['closed_by'] == 'Synthetic closing reviewer' and closed['closed_at']
    before = detail(client, i)
    assert reassign(client, i).status_code == 409
    assert client.post(f'/api/incidents/{i}/close', json={'by': 'Different reviewer'}).status_code == 200
    assert detail(client, i) == before


def test_critical_review_retains_new_accountability_after_reassignment(client):
    i = case_id(client)
    client.post(f'/api/incidents/{i}/simulate-callback', json={'outcome': 'worse'})
    client.post(f'/api/incidents/{i}/accept', json={'owner': 'Synthetic accepting person'})
    assert reassign(client, i).status_code == 200
    state = client.get('/api/state').json()
    row = next(row for row in state['incidents'] if row['id'] == i)
    assert row['critical'] and row['status'] == 'escalated' and row['department'] == 'Urban Forestry'
    assert not row['accepted'] and i in state['supervisor_queue']
    assert next(a for a in state['critical_alerts'] if a['incident_id'] == i)['accepted'] is False


def test_missing_department_can_be_seen_and_assigned_without_a_crash_or_false_acceptance(client, calls, clock):
    i = case_id(client)
    with Session(engine) as s:
        for row in s.exec(select(Assignment).where(Assignment.incident_id == i)):
            s.delete(row)
        s.commit()
    clock.tick()
    current = detail(client, i)
    assert current['department'] is None and current['assignment'] is None
    assert not current['acknowledged'] and not current['accepted']
    assert any(d['kind'] == 'department_assignment' for d in current['debts'])
    assert client.post(f'/api/incidents/{i}/accept', json={'owner': 'Synthetic operator'}).status_code == 409
    assert reassign(client, i).status_code == 200
    assert detail(client, i)['department'] == 'Urban Forestry'
    assert not any(d['kind'] == 'department_assignment' for d in detail(client, i)['debts'])


@pytest.mark.parametrize('authorization', [None, 'Bearer wrong-key', f'Basic {KEY}', 'Bearer '])
def test_unauthorized_reassignment_is_rejected_before_incident_lookup_and_preserves_history(client, authorization):
    i = case_id(client)
    before = detail(client, i)
    headers = {'Authorization': authorization or ''}
    body = {'department': 'Urban Forestry', 'by': 'Synthetic supervisor', 'reason': 'Routing change'}
    for target in [i, 999999]:
        response = client.post(f'/api/incidents/{target}/reassign', json=body, headers=headers)
        assert response.status_code == 401 and response.headers['www-authenticate'] == 'Bearer'
    assert detail(client, i) == before


@pytest.mark.parametrize('configured_key', ['', '   '])
def test_unconfigured_reassignment_authorization_fails_closed_without_mutation(client, monkeypatch, configured_key):
    i = case_id(client)
    before = detail(client, i)
    monkeypatch.setattr(routes, 'REVIEWER_API_KEY', configured_key)
    assert reassign(client, i).status_code == 503
    assert detail(client, i) == before


def test_reviewer_key_in_request_body_does_not_authorize_reassignment(client):
    i = case_id(client)
    before = detail(client, i)
    response = client.post(f'/api/incidents/{i}/reassign', json={
        'department': 'Urban Forestry', 'by': 'Synthetic supervisor', 'reason': 'Routing change', 'reviewer_key': KEY,
    }, headers={'Authorization': ''})
    assert response.status_code == 401
    assert detail(client, i) == before


def test_authorized_reassignment_records_actor_and_time_without_storing_or_logging_token(client, caplog):
    from app.models import Event

    i = case_id(client)
    before = detail(client, i)
    with Session(engine) as s:
        old_events = {e.id: e.model_dump() for e in s.exec(select(Event).where(Event.incident_id == i))}
    response = reassign(client, i)
    assert response.status_code == 200
    current = response.json()
    assert current['assignment']['assigned_by'] == 'Synthetic supervisor' and current['assignment']['assigned_at']
    assert not current['accepted'] and not current['acknowledged']
    assert all(row in current['assignment_history'] for row in before['assignment_history'])
    assert KEY not in response.text and KEY not in caplog.text
    with Session(engine) as s:
        events = s.exec(select(Event).where(Event.incident_id == i)).all()
        assert all(s.get(Event, event_id).model_dump() == old for event_id, old in old_events.items())
        assert any(e.type == 'reassigned' and e.actor == 'Synthetic supervisor' and e.at for e in events)
        assert all(KEY not in str(e.model_dump()) for e in events)
