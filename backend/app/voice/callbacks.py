"""Contract function: request_callback(...) -> call id. Called by B's ladder at step 4."""
import logging
import uuid

import httpx

from app.config import CALL_MODE, RETELL_API_KEY, RETELL_CALLBACK_AGENT_ID, RETELL_FROM_NUMBER
from app.engine.contact import valid_phone

log = logging.getLogger(__name__)

RETELL_API = "https://api.retellai.com"


def request_callback(incident_id: int, phone: str, attempt_no: int, vars: dict, *, request_key: str | None = None) -> str:
    """Start an outbound callback to the resident; the outcome arrives later via the webhook.

    vars become Retell dynamic variables, e.g. {"location": "...", "hazard": "..."}.
    Simulation never contacts Retell. The engine owns consent, durable dispatch and retries.
    """
    if not valid_phone(phone):
        raise ValueError('A validated stored callback number is required')
    if CALL_MODE == "simulate":
        call_id = f"sim-{request_key or uuid.uuid4().hex}"
        log.info("simulated callback %s for incident %s (attempt %s)", call_id, incident_id, attempt_no)
        return call_id
    if CALL_MODE != 'live' or not RETELL_API_KEY or not RETELL_CALLBACK_AGENT_ID or not valid_phone(RETELL_FROM_NUMBER):
        raise ValueError('Outbound callback configuration is unavailable')
    if not request_key:
        raise ValueError('A persistent callback request key is required')
    # Current documented API; no automatic transport retry can initiate another call.
    response = httpx.post(
        f"{RETELL_API}/v2/create-phone-call",
        headers={"Authorization": f"Bearer {RETELL_API_KEY}"},
        json={
            "from_number": RETELL_FROM_NUMBER,
            "to_number": phone,
            "override_agent_id": RETELL_CALLBACK_AGENT_ID,
            "override_agent_version": "latest_published",
            "metadata": {"incident_id": incident_id, "attempt_no": attempt_no, "callback_request_id": request_key},
            "idempotency_key": request_key,
            "retell_llm_dynamic_variables": {k: str(vars[k]) for k in ('hazard', 'location')},
            "honor_internal_dnc": True,
        },
        timeout=10,
    )
    response.raise_for_status()
    call_id = response.json().get('call_id')
    if not isinstance(call_id, str) or not call_id:
        raise ValueError('Provider acknowledgment lacks a call identifier')
    return call_id
