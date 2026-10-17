import os
import tempfile
from pathlib import Path

# Must run before app is imported: config reads the environment at import time.
os.environ["DB_PATH"] = str(Path(tempfile.gettempdir()) / "handoffproof_test.db")
os.environ["CALL_MODE"] = "simulate"
os.environ["TIMING_PROFILE"] = "demo"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        assert c.post("/api/demo/reset", json={"seed": "storm_night"}).status_code == 200
        yield c
