import logging
from collections.abc import Iterator

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  (registers the tables)
from app.config import DB_PATH

log = logging.getLogger(__name__)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def init_db() -> None:
    if _schema_is_stale():
        # Demo data only: a teammate's old local DB is rebuilt instead of failing on new columns.
        log.warning("Local database schema is out of date; recreating %s", DB_PATH)
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def reset_db() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


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
