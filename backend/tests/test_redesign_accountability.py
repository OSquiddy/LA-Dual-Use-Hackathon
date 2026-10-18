"""The directory enriches new handoffs without rewriting historical evidence."""
import copy
import json
import os
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlmodel import Session, select

from app.db import engine
from app.engine import oncall
from app.contracts import ReportIn
from app.engine.ingest import ingest_report
from app.migrations import upgrade_assignment_profiles
from app.models import Assignment, Event, Report
from app.timeutil import utcnow


def test_directory_has_five_units_and_ten_fictional_staff(client):
    departments = client.get('/api/state').json()['departments']
    assert len(departments) == 5
    assert sum(len(d['staff']) for d in departments) == 10
    assert all(d['display_name'] and d['operational_unit'] for d in departments)
    assert all(p['fictional'] and p['role'] for d in departments for p in d['staff'])
    assert sum(d['active_incidents'] for d in departments) == 1
    assert sum(d['awaiting_acceptance'] for d in departments) == 1


def test_selection_is_stable_varied_and_respects_availability(monkeypatch):
    for dept in oncall.directory():
        first = oncall.default_owner(dept, 'Highland Park', 1)
        second = oncall.default_owner(dept, 'Highland Park', 2)
        assert first != second
        assert oncall.default_owner(dept, 'Highland Park', 1) == first
    config = copy.deepcopy(oncall._configuration())
    for p in config['_staff']:
        if p['department'] == 'Stormwater Operations':
            p['on_call'] = False
    monkeypatch.setattr(oncall, '_configuration', lambda: config)
    assert oncall.default_owner('Stormwater Operations', None, 3) is None
    assert oncall.default_owner('Unknown', None, 3) is None
    config['Street Services'].pop('*')
    assert oncall.default_owner('Street Services', None, 3) is None


def test_assignment_profile_is_immutable_when_roster_changes(client, calls, clock, monkeypatch):
    clock.tick(2)
    row = client.get('/api/state').json()['incidents'][0]
    before = client.get(f"/api/incidents/{row['id']}").json()
    profile = before['assignment']
    assert profile['staff_id'] and profile['owner_role'] and profile['profile_recorded']
    config = copy.deepcopy(oncall._configuration())
    for person in config['_staff']:
        person['name'] = 'Changed configuration name'
        person['role'] = 'Changed configuration role'
    for dept in config['_departments'].values():
        dept['unit'] = 'Changed configured unit'
    monkeypatch.setattr(oncall, '_configuration', lambda: config)
    after = client.get(f"/api/incidents/{row['id']}").json()
    assert after['assignment'] == profile
    assert after['assignment_history'] == before['assignment_history']


def test_legacy_profile_is_not_fabricated_or_backfilled(client):
    with Session(engine) as s:
        assignment = s.exec(select(Assignment)).first()
        assignment.owner = 'Historical named person'
        assignment.responsibility_profile = None
        s.add(assignment); s.commit(); s.refresh(assignment)
        original = assignment.model_dump()
        event_count = len(s.exec(select(Event)).all())
    data = client.get(f"/api/incidents/{original['incident_id']}").json()['assignment']
    assert data['owner_display_name'] == 'Historical named person'
    assert data['owner_role'] is None and data['operational_unit'] is None and not data['profile_recorded']
    with Session(engine) as s:
        assert s.get(Assignment, original['id']).model_dump() == original
        assert len(s.exec(select(Event)).all()) == event_count


def test_assignment_profile_migration_is_additive_idempotent(tmp_path):
    db = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with db.begin() as c:
        c.exec_driver_sql('CREATE TABLE assignment (id INTEGER PRIMARY KEY, incident_id INTEGER, department TEXT, owner TEXT, assigned_at TEXT, acknowledged_at TEXT, accepted_at TEXT, default_owner_at TEXT)')
        c.exec_driver_sql("INSERT INTO assignment VALUES (1, 7, 'Legacy department', 'Original person', '2026-10-01', NULL, NULL, NULL)")
        before = c.exec_driver_sql('SELECT * FROM assignment').all()
    upgrade_assignment_profiles(db); upgrade_assignment_profiles(db)
    with db.connect() as c:
        assert c.exec_driver_sql('SELECT id, incident_id, department, owner, assigned_at, acknowledged_at, accepted_at, default_owner_at FROM assignment').all() == before
        assert c.exec_driver_sql('SELECT responsibility_profile FROM assignment').scalar() is None
        assert 'responsibility_profile' in {c['name'] for c in inspect(c).get_columns('assignment')}


def test_history_pagination_includes_closed_cases_and_never_transcripts(client, calls, clock):
    i = client.get('/api/state').json()['incidents'][0]['id']
    clock.tick(2)
    client.post(f'/api/incidents/{i}/accept', json={'owner': 'Synthetic reviewer'})
    client.post(f'/api/incidents/{i}/close', json={'by': 'Synthetic reviewer'})
    collected = []
    before = None
    while True:
        page = client.get('/api/assignment-history', params={'limit': 1, **({'before_id': before} if before else {})})
        assert page.status_code == 200 and 'transcript' not in page.text and 'phone' not in page.text
        data = page.json()
        collected.extend(data['entries'])
        before = data['next_before_id']
        if not before:
            break
    assert len(collected) == 3
    assert len({e['assignment']['id'] for e in collected}) == 3
    assert all(e['status'] == 'closed' for e in collected)
    assert any(e['assignment']['accepted_at'] for e in collected)
    for params in [{'limit': 0}, {'limit': 101}, {'before_id': 0}]:
        assert client.get('/api/assignment-history', params=params).status_code == 422


def test_synthetic_redesign_snapshot(client, calls, clock):
    for n, hazard in enumerate(['pothole', 'stalled_vehicle', 'downed_tree', 'downed_line'], 1):
        ingest_report(ReportIn(source='seed', call_id=f'redesign-synthetic-{n}', hazard_type=hazard,
                              location_text=None if hazard == 'downed_tree' else 'Figueroa and Avenue 57', created_at=utcnow(),
                              anyone_in_danger=False, transcript='Caller reports possible electrical sparking.' if hazard == 'downed_line' else 'Synthetic test report.'))
    clock.tick(2)
    state = client.get('/api/state').json()
    details = {str(i['id']): client.get(f"/api/incidents/{i['id']}").json() for i in state['incidents']}
    assert len({i['department'] for i in state['incidents']}) == 5
    assert all(i['owner'] and not i['accepted'] for i in state['incidents'])
    if destination := os.environ.get('HANDOFFPROOF_REDESIGN_SNAPSHOTS'):
        Path(destination).write_text(json.dumps({'state': state, 'details': details, 'history': client.get('/api/assignment-history').json()}))
