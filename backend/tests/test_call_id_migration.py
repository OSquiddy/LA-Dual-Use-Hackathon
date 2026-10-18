"""Person B's approved migration preserves data or stops for review."""
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import create_engine

from app import db


@pytest.fixture
def legacy_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        for name in ('report', 'callback'):
            connection.exec_driver_sql(f'CREATE TABLE {name} (id INTEGER PRIMARY KEY, call_id TEXT NOT NULL)')
            connection.exec_driver_sql(f"INSERT INTO {name} (call_id) VALUES ('existing-{name}')")
    monkeypatch.setattr(db, 'engine', engine)
    yield engine
    engine.dispose()


def test_preserves_rows_and_is_repeatable(legacy_db):
    db.ensure_unique_call_ids()
    db.ensure_unique_call_ids()
    with legacy_db.connect() as connection:
        for name in ('report', 'callback'):
            assert connection.exec_driver_sql(f'SELECT count(*) FROM {name}').scalar() == 1
            assert any(i['unique'] for i in inspect(connection).get_indexes(name))
    for name in ('report', 'callback'):
        with pytest.raises(IntegrityError), legacy_db.begin() as connection:
            connection.exec_driver_sql(f"INSERT INTO {name} (call_id) VALUES ('existing-{name}')")


@pytest.mark.parametrize('name', ['report', 'callback'])
def test_duplicate_data_is_not_deleted(legacy_db, name):
    with legacy_db.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {name} (call_id) VALUES ('existing-{name}')")
    with pytest.raises(RuntimeError, match='existing data was preserved'):
        db.ensure_unique_call_ids()
    with legacy_db.connect() as connection:
        assert connection.exec_driver_sql(f'SELECT count(*) FROM {name}').scalar() == 2


def test_stale_schema_is_not_rebuilt(legacy_db):
    with pytest.raises(RuntimeError, match='existing data was preserved'):
        db.init_db()
    with legacy_db.connect() as connection:
        assert connection.exec_driver_sql('SELECT call_id FROM report').scalar() == 'existing-report'
