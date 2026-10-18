"""Upgrade old SQLite callback rows without changing existing evidence or consent."""
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import create_engine

from app.migrations import upgrade_callbacks


@pytest.fixture
def old_schema(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old-callbacks.db'}")
    with engine.begin() as c:
        c.exec_driver_sql('CREATE TABLE report (id INTEGER PRIMARY KEY, call_id TEXT, callback_ok BOOLEAN, transcript TEXT)')
        c.exec_driver_sql("INSERT INTO report VALUES (1, 'old-intake', 1, 'PRIVATE ORIGINAL EVIDENCE')")
        c.exec_driver_sql('''CREATE TABLE callback (id INTEGER PRIMARY KEY, incident_id INTEGER, report_id INTEGER,
            call_id TEXT, phone TEXT, attempt_no INTEGER, outcome TEXT, danger BOOLEAN, summary TEXT,
            called_at DATETIME, completed_at DATETIME)''')
        c.exec_driver_sql("INSERT INTO callback VALUES (1, 1, 1, 'old-completed', '+13235550177', 1, 'same', 0, 'original summary', '2026-01-01', '2026-01-01')")
        c.exec_driver_sql("INSERT INTO callback VALUES (2, 1, 1, 'old-unconfirmed', '+13235550177', 2, NULL, 0, '', '2026-01-01', NULL)")
    yield engine
    engine.dispose()


def test_upgrade_preserves_all_original_fields_is_repeatable_and_never_redispatches_legacy(old_schema):
    with old_schema.connect() as c:
        before_reports = c.exec_driver_sql('SELECT id, call_id, callback_ok, transcript FROM report').all()
        before_callbacks = c.exec_driver_sql('SELECT * FROM callback ORDER BY id').all()
    upgrade_callbacks(old_schema)
    upgrade_callbacks(old_schema)
    with old_schema.connect() as c:
        assert c.exec_driver_sql('SELECT id, call_id, callback_ok, transcript FROM report').all() == before_reports
        fields = 'id, incident_id, report_id, call_id, phone, attempt_no, outcome, danger, summary, called_at, completed_at'
        assert c.exec_driver_sql(f'SELECT {fields} FROM callback ORDER BY id').all() == before_callbacks
        assert c.exec_driver_sql('SELECT state, mode, result_recorded FROM callback ORDER BY id').all() == [('completed', 'legacy', 1), ('unknown', 'legacy', 0)]
        assert c.exec_driver_sql('SELECT callback_opt_out FROM report').scalar() == 0
    with pytest.raises(IntegrityError), old_schema.begin() as c:
        c.exec_driver_sql("INSERT INTO callback (incident_id, attempt_no) VALUES (1, 1)")


def test_duplicate_old_attempts_stop_before_any_schema_or_data_change(old_schema):
    with old_schema.begin() as c:
        c.exec_driver_sql("INSERT INTO callback (incident_id, attempt_no) VALUES (1, 1)")
    with pytest.raises(RuntimeError, match='existing data was preserved'):
        upgrade_callbacks(old_schema)
    with old_schema.connect() as c:
        assert c.exec_driver_sql('SELECT count(*) FROM callback').scalar() == 3
        assert 'state' not in {col['name'] for col in inspect(c).get_columns('callback')}
