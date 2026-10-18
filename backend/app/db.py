import logging
from collections.abc import Iterator

from sqlalchemy import func, inspect, select
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  (registers the tables)
from app.config import DB_PATH
from app.migrations import upgrade_callbacks

log = logging.getLogger(__name__)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def init_db() -> None:
    upgrade_callbacks(engine)
    if _schema_is_stale():
        raise RuntimeError("Database schema requires a coordinated migration; existing data was preserved")
    SQLModel.metadata.create_all(engine)
    upgrade_callbacks(engine)  # also installs attempt indexes for a newly created database
    ensure_unique_call_ids()


def ensure_unique_call_ids() -> None:
    """Add durable call-ID uniqueness to older databases without altering any rows.

    Refuse ambiguous old data instead of deleting it. Person B owns review/cleanup.
    """
    tables = [SQLModel.metadata.tables[name] for name in ("report", "callback")]
    with engine.begin() as connection:
        for table in tables:
            duplicate = connection.execute(
                select(func.count()).select_from(table).group_by(table.c.call_id)
                .having(func.count() > 1).limit(1)
            ).first()
            if duplicate:
                raise RuntimeError(f"Duplicate call IDs in {table.name}; existing data was preserved for review")
        inspector = inspect(connection)
        for table in tables:
            unique = inspector.get_unique_constraints(table.name) + [
                idx for idx in inspector.get_indexes(table.name) if idx.get("unique")
            ]
            if not any(item["column_names"] == ["call_id"] for item in unique):
                # Name differs from the scaffold's old non-unique ix_* indexes.
                # table.name is from the fixed metadata list above, never user input.
                connection.exec_driver_sql(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS uq_{table.name}_call_id '
                    f'ON "{table.name}" (call_id)',
                )


def reset_db() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    upgrade_callbacks(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def _schema_is_stale() -> bool:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    for table in SQLModel.metadata.sorted_tables:
        if table.name in existing:
            columns = {c["name"] for c in inspector.get_columns(table.name)}
            if not set(table.columns.keys()) <= columns:
                return True
    return False
