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
os.environ["LADDER_ENABLED"] = "0"  # tests drive the ladder with Clock

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.engine import ladder  # noqa: E402
from app.main import app  # noqa: E402
from app.timeutil import utcnow  # noqa: E402
from app.voice import callbacks  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        assert c.post("/api/demo/reset", json={"seed": "storm_night"}).status_code == 200
        yield c


@pytest.fixture
def calls(monkeypatch):
    """Records outbound callback requests instead of calling Retell or starting simulator timers."""
    placed: list[dict] = []

    def fake_request_callback(incident_id, phone, attempt_no, vars):
        placed.append({"incident_id": incident_id, "phone": phone, "attempt_no": attempt_no, "vars": vars})
        return f"test-call-{len(placed)}"

    monkeypatch.setattr(callbacks, "request_callback", fake_request_callback)
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
