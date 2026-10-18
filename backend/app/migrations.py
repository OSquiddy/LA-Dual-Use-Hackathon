"""Additive schema upgrades. Unknown legacy schemas are left for explicit review."""
from sqlalchemy import inspect


def upgrade_assignment_profiles(engine) -> None:
    """Add an optional snapshot; existing assignment fields are never backfilled or rewritten."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        if 'assignment' not in inspector.get_table_names():
            return
        columns = {column['name'] for column in inspector.get_columns('assignment')}
        original = {'id', 'incident_id', 'department', 'owner', 'assigned_at', 'acknowledged_at', 'accepted_at', 'default_owner_at'}
        if original <= columns and 'responsibility_profile' not in columns:
            connection.exec_driver_sql('ALTER TABLE assignment ADD COLUMN responsibility_profile JSON')

CALLBACK_COLUMNS = {
    "state": "VARCHAR NOT NULL DEFAULT 'unknown'", "scheduled_at": "DATETIME",
    "dispatch_started_at": "DATETIME", "result_due_at": "DATETIME", "request_key": "VARCHAR",
    "mode": "VARCHAR NOT NULL DEFAULT 'legacy'", "live_authorized": "BOOLEAN NOT NULL DEFAULT 0",
    "automatic": "BOOLEAN NOT NULL DEFAULT 1",
    "error_code": "VARCHAR", "transcript": "VARCHAR NOT NULL DEFAULT ''",
    "result_recorded": "BOOLEAN NOT NULL DEFAULT 0",
}


def upgrade_callbacks(engine) -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        if not {"callback", "report"} <= tables:
            return
        columns = {table: {c['name'] for c in inspector.get_columns(table)} for table in ('callback', 'report')}
        original = {"id", "incident_id", "report_id", "call_id", "phone", "attempt_no", "outcome", "danger", "summary", "called_at", "completed_at"}
        if not original <= columns['callback'] or not {"callback_ok", "transcript", "call_id"} <= columns['report']:
            return  # init_db's existing stale-schema check will refuse this unknown layout.
        duplicate = connection.exec_driver_sql(
            'SELECT 1 FROM callback GROUP BY incident_id, attempt_no HAVING count(*) > 1 LIMIT 1',
        ).first()
        if duplicate:
            raise RuntimeError('Duplicate callback attempts require review; existing data was preserved')
        for name, definition in CALLBACK_COLUMNS.items():
            if name not in columns['callback']:
                connection.exec_driver_sql(f'ALTER TABLE callback ADD COLUMN {name} {definition}')
        if 'callback_opt_out' not in columns['report']:
            connection.exec_driver_sql('ALTER TABLE report ADD COLUMN callback_opt_out BOOLEAN NOT NULL DEFAULT 0')
        connection.exec_driver_sql('CREATE UNIQUE INDEX IF NOT EXISTS uq_callback_attempt ON callback (incident_id, attempt_no)')
        connection.exec_driver_sql('CREATE UNIQUE INDEX IF NOT EXISTS uq_callback_request ON callback (request_key)')
        # Preserve every original evidence/consent value. Only new lifecycle fields are initialized.
        connection.exec_driver_sql("UPDATE callback SET state='completed' WHERE mode='legacy' AND outcome IS NOT NULL AND state='unknown'")
        connection.exec_driver_sql("UPDATE callback SET result_recorded=1 WHERE outcome IS NOT NULL")
