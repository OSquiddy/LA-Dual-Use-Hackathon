"""Contract function: request_callback(...) -> call id. Called by B's ladder at step 4."""
import logging
import uuid

import httpx

from app.config import CALL_MODE, RETELL_API_KEY, RETELL_CALLBACK_AGENT_ID, RETELL_FROM_NUMBER

log = logging.getLogger(__name__)

RETELL_API = "https://api.retellai.com"


def request_callback(incident_id: int, phone: str, attempt_no: int, vars: dict) -> str:
    """Start an outbound callback to the resident; the outcome arrives later via the webhook.

    vars become Retell dynamic variables, e.g. {"location": "...", "hazard": "..."}.
    The phones_down twist is handled by the ladder before this is called (B14).
    """
    if CALL_MODE != "live":
        from app.voice import simulator

        call_id = f"sim-{uuid.uuid4().hex[:8]}"
        simulator.schedule(incident_id, call_id, attempt_no)
        log.info("simulated callback %s for incident %s (attempt %s)", call_id, incident_id, attempt_no)
        return call_id

    # TODO(A8): verify endpoint and field names against Retell's current API docs.
    response = httpx.post(
        f"{RETELL_API}/v2/create-phone-call",
        headers={"Authorization": f"Bearer {RETELL_API_KEY}"},
        json={
            "from_number": RETELL_FROM_NUMBER,
            "to_number": phone,
            "override_agent_id": RETELL_CALLBACK_AGENT_ID,
            "metadata": {"incident_id": incident_id, "attempt_no": attempt_no},
            "retell_llm_dynamic_variables": {k: str(v) for k, v in vars.items()},
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["call_id"]
