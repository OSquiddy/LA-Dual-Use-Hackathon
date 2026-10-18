"""Live pause/resume safety checks use a private synthetic settings file and fake calls."""
import pytest

from app.engine import callback_jobs, live_control
from app.voice import callbacks


@pytest.fixture
def switch(tmp_path, monkeypatch):
    path = tmp_path / '.env'
    monkeypatch.setattr(live_control, 'SETTINGS_FILE', path)
    return path


@pytest.mark.parametrize('content,allowed', [
    ('CALL_MODE=live\nLIVE_CALLBACKS_ENABLED=1\n', True),
    ('CALL_MODE=live\nLIVE_CALLBACKS_ENABLED=0\n', False),
    ('CALL_MODE=simulate\nLIVE_CALLBACKS_ENABLED=1\n', False),
    ('CALL_MODE=live\nLIVE_CALLBACKS_ENABLED=true\n', False),
    ('CALL_MODE=live\n', False), ('', False),
])
def test_live_switch_requires_both_explicit_values(switch, content, allowed):
    switch.write_text(content)
    assert live_control.automatic_enabled(True) is allowed


def test_file_cannot_authorize_a_process_started_without_automation(switch):
    switch.write_text('CALL_MODE=live\nLIVE_CALLBACKS_ENABLED=1\n')
    assert not live_control.automatic_enabled(False)


def test_missing_file_disables_automatic_calls(switch):
    assert not live_control.automatic_enabled(True)


def test_edits_take_effect_without_restarting_and_unreadable_file_fails_closed(switch):
    switch.write_text('CALL_MODE=live\nLIVE_CALLBACKS_ENABLED=1\n')
    assert live_control.automatic_enabled(True)
    switch.write_text('CALL_MODE=live\nLIVE_CALLBACKS_ENABLED=0\n')
    assert not live_control.automatic_enabled(True)
    switch.unlink()
    switch.mkdir()
    assert not live_control.automatic_enabled(True)


def test_paused_due_case_resumes_once_without_bypassing_eligibility(client, calls, clock, monkeypatch, switch):
    from app.contracts import ReportIn
    from app.engine.ingest import ingest_report
    from app.timeutil import utcnow

    ingest_report(ReportIn(source='retell', call_id='synthetic-live-switch-report', hazard_type='flood',
        location_text='Figueroa and Avenue fifty two', phone='+13235550177', callback_ok=True, created_at=utcnow()))
    monkeypatch.setattr(callbacks, 'CALL_MODE', 'live')
    monkeypatch.setattr(callbacks, 'RETELL_API_KEY', 'synthetic-key')
    monkeypatch.setattr(callbacks, 'RETELL_CALLBACK_AGENT_ID', 'synthetic-callback-agent')
    monkeypatch.setattr(callbacks, 'RETELL_FROM_NUMBER', '+13235550188')
    monkeypatch.setattr(callback_jobs, 'LIVE_CALLBACKS_ENABLED', True)
    switch.write_text('CALL_MODE=live\nLIVE_CALLBACKS_ENABLED=0\n')
    clock.tick(4)
    assert not calls
    paused = client.get('/api/incidents/1').json()
    assert paused['next_step_at'] and not paused['callback_status']['automatic_live_enabled']
    switch.write_text('CALL_MODE=live\nLIVE_CALLBACKS_ENABLED=1\n')
    clock.tick()
    assert len(calls) == 1 and calls[0]['phone'] == '+13235550177'
    clock.tick(3)
    assert len(calls) == 1
    assert client.get('/api/incidents/1').json()['callback_status']['automatic_live_enabled']
