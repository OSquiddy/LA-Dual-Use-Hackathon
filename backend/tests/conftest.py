import os
import tempfile
from datetime import timedelta
from pathlib import Path

# Must run before app is imported: config reads the environment at import time,
# and these win over anything in a developer's .env.
os.environ["DB_PATH"] = str(Path(tempfile.gettempdir()) / "handoffproof_test.db")
os.environ["CALL_MODE"] = "simulate"
os.environ["TIMING_PROFILE"] = "demo"
os.environ["DEMO_RESIDENT_PHONE"] = ""
os.environ["RETELL_INTAKE_AGENT_ID"] = "synthetic-intake-agent"
os.environ["RETELL_CALLBACK_AGENT_ID"] = "synthetic-callback-agent"
os.environ["LADDER_ENABLED"] = "0"  # tests drive the ladder with Clock
os.environ['LIVE_CALLBACKS_ENABLED'] = '0'

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.engine import ladder  # noqa: E402
from app.main import app  # noqa: E402
from app.timeutil import utcnow  # noqa: E402
from app.voice import callbacks  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    from app.api import routes

    key = 'synthetic-assignment-reviewer-key'
    monkeypatch.setattr(routes, 'REVIEWER_API_KEY', key)
    with TestClient(app, headers={'Authorization': f'Bearer {key}'}) as c:
        assert c.post("/api/demo/reset", json={"seed": "storm_night"}).status_code == 200
        yield c


@pytest.fixture
def calls(monkeypatch):
    """Records outbound callback requests instead of calling Retell or starting simulator timers."""
    placed: list[dict] = []

    def fake_request_callback(incident_id, phone, attempt_no, vars, **kwargs):
        placed.append({"incident_id": incident_id, "phone": phone, "attempt_no": attempt_no, "vars": vars})
        return f"test-call-{len(placed)}"

    monkeypatch.setattr(callbacks, "request_callback", fake_request_callback)
    from app.voice import simulator
    monkeypatch.setattr(simulator, 'schedule', lambda *args: None)
    return placed


class Clock:
    """Moves the ladder forward far enough for one step per tick, without waiting."""

    def __init__(self):
        self.now = utcnow()

    def tick(self, times: int = 1) -> None:
        for _ in range(times):
            self.now += timedelta(seconds=100)
            ladder.tick(self.now)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def dispatched_callback():
    """A synthetic provider result must refer to a persisted dispatch, like production."""
    def create(incident_id, call_id, attempt_no=1):
        from sqlmodel import Session, select
        from app.db import engine
        from app.models import Callback, Report

        with Session(engine) as s:
            report = s.exec(select(Report).where(Report.incident_id == incident_id, Report.callback_ok == True)).first()
            job = Callback(incident_id=incident_id, report_id=report.id, phone=report.phone,
                           call_id=call_id, attempt_no=attempt_no, mode='simulate', state='calling')
            s.add(job)
            s.commit()
    return create


@pytest.fixture
def signed_webhook(client, monkeypatch):
    """Authenticate synthetic payloads with a test-only key; never read local Retell secrets."""
    import hashlib
    import copy
    import hmac
    import json
    import time
    from app.voice import webhooks

    key = "synthetic-test-signing-key"
    monkeypatch.setattr(webhooks, "RETELL_API_KEY", key)

    def send(payload=None, *, raw=None, timestamp=None):
        if raw is None:
            payload = copy.deepcopy(payload)
            if isinstance(payload, dict) and isinstance(payload.get("call"), dict):
                call = payload["call"]
                metadata = call.get("metadata")
                callback = isinstance(metadata, dict) and "incident_id" in metadata
                call.setdefault("agent_id", "synthetic-callback-agent" if callback else "synthetic-intake-agent")
            raw = json.dumps(payload).encode()
        timestamp = str(timestamp if timestamp is not None else int(time.time() * 1000))
        digest = hmac.new(key.encode(), raw + timestamp.encode(), hashlib.sha256).hexdigest()
        return client.post('/retell/webhook', content=raw, headers={
            'Content-Type': 'application/json', 'x-retell-signature': f'v={timestamp},d={digest}',
        })

    return send
