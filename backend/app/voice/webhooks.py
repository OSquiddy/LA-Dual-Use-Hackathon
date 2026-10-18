"""Authenticated Retell events -> existing intake and callback engine contracts."""
import json
from datetime import datetime, timezone
from threading import RLock

from fastapi import APIRouter, HTTPException, Request, Response

from app.config import HAZARD_TYPES, RETELL_API_KEY, RETELL_CALLBACK_AGENT_ID, RETELL_INTAKE_AGENT_ID
from app.contracts import CallbackOutcome, ReportIn
from app.engine.ingest import ingest_report
from app.engine.ladder import record_verified_callback_outcome
from app.voice.security import verify_signature

router = APIRouter()
# The demo runs one backend worker. Serialize delivery retries through commit; call IDs
# also have persistent database uniqueness, so intake remains idempotent after restart.
_delivery_lock = RLock()
NO_ANSWER_REASONS = {"dial_no_answer", "voicemail_reached", "dial_busy", "dial_failed"}
NO_ANSWER_REASONS |= {'ivr_reached', 'invalid_destination', 'user_declined', 'telephony_provider_unavailable', 'telephony_provider_permission_denied', 'sip_routing_error'}


async def verify_retell_request(request: Request) -> bytes:
    """Use original bytes for SDK verification, before any JSON parsing or writes."""
    raw = await request.body()
    if not verify_signature(raw, request.headers.get("x-retell-signature", ""), RETELL_API_KEY):
        raise HTTPException(401, "Invalid Retell signature")
    return raw


@router.post("/retell/webhook")
async def retell_webhook(request: Request) -> Response:
    raw = await verify_retell_request(request)
    try:
        body = json.loads(raw)
        if not isinstance(body, dict) or not isinstance(body.get("event"), str):
            raise ValueError("Expected event object")
        if body["event"] != "call_analyzed":
            return Response(status_code=204)
        call = body.get("call")
        if not isinstance(call, dict) or not isinstance(call.get("call_id"), str) or not call["call_id"].strip():
            raise ValueError("Missing call ID")
        agent_id = call.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("Missing agent identity")
        metadata = call.get("metadata")
        metadata = {} if metadata is None else metadata
        if not isinstance(metadata, dict):
            raise ValueError("Invalid metadata")
        analysis = call.get("call_analysis")
        if analysis is not None:
            if not isinstance(analysis, dict):
                raise ValueError("Invalid analysis")
            fields = analysis.get("custom_analysis_data")
            if fields is not None and not isinstance(fields, dict):
                raise ValueError("Invalid analysis fields")
        # Never infer agent identity from metadata supplied in the event.
        if not RETELL_INTAKE_AGENT_ID or not RETELL_CALLBACK_AGENT_ID or RETELL_INTAKE_AGENT_ID == RETELL_CALLBACK_AGENT_ID:
            raise HTTPException(503, "Retell agent configuration unavailable")
        if agent_id == RETELL_INTAKE_AGENT_ID:
            if "incident_id" in metadata:
                raise ValueError("Callback metadata on intake agent")
            result = intake_from_call(call)
            is_callback = False
        elif agent_id == RETELL_CALLBACK_AGENT_ID:
            result = callback_from_call(call)
            is_callback = True
        else:
            raise HTTPException(403, "Unauthorized Retell agent")
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, OSError):
        raise HTTPException(400, "Invalid webhook payload") from None
    with _delivery_lock:
        if is_callback:
            try:
                record_verified_callback_outcome(result)
            except ValueError:
                raise HTTPException(403, 'Callback does not match a dispatched attempt') from None
        else:
            ingest_report(result)
    return Response(status_code=204)


def intake_from_call(call: dict) -> ReportIn:
    fields = (call.get("call_analysis") or {}).get("custom_analysis_data") or {}
    hazard = fields.get("hazard_type") or "other"
    return ReportIn(
        source="retell", call_id=call["call_id"], phone=call.get("from_number"),
        location_text=fields.get("location_text"),
        hazard_type=hazard if hazard in HAZARD_TYPES else "other",
        danger_words=_as_list(fields.get("danger_words")),
        anyone_in_danger=_as_bool(fields.get("anyone_in_danger")),
        callback_ok=_as_bool(fields.get("callback_ok")),
        callback_opt_out=_as_bool(fields.get('callback_opt_out')) or call.get('disconnection_reason') == 'user_requested_dnc',
        transcript=call.get("transcript") or "", created_at=_call_time(call),
    )


def callback_from_call(call: dict) -> CallbackOutcome:
    metadata = call.get("metadata") or {}
    fields = (call.get("call_analysis") or {}).get("custom_analysis_data") or {}
    outcome = fields.get("outcome")
    if call.get("disconnection_reason") in NO_ANSWER_REASONS or (call.get('call_analysis') or {}).get('in_voicemail') is True:
        outcome = "no_answer"
    elif outcome not in ('worse', 'same', 'better'):
        outcome = None
    opt_out = _as_bool(fields.get('callback_opt_out')) or call.get('disconnection_reason') == 'user_requested_dnc'
    wrong_number = _as_bool(fields.get('wrong_number'))
    if wrong_number or (opt_out and outcome == 'no_answer'):
        outcome = None
    request_key = metadata.get('callback_request_id')
    if request_key is not None and (not isinstance(request_key, str) or len(request_key) > 128):
        raise ValueError('Invalid callback request reference')
    return CallbackOutcome(
        incident_id=_positive_int(metadata["incident_id"]), call_id=call["call_id"],
        attempt_no=_positive_int(metadata.get("attempt_no", 1)), outcome=outcome,
        danger=_as_bool(fields.get("anyone_in_danger")), summary=fields.get("summary") or "",
        transcript=call.get("transcript") or "",
        request_key=request_key, callback_opt_out=opt_out, wrong_number=wrong_number,
        disconnection_reason=call.get('disconnection_reason'),
    )


def _positive_int(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("Invalid callback identifier")
    parsed = int(value)
    if not 0 < parsed <= 2**63 - 1:
        raise ValueError("Invalid callback identifier")
    return parsed


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value.strip():
        return [w.strip() for w in value.split(",") if w.strip()]
    return []


def _as_bool(value) -> bool:
    """Retell's configured boolean extraction must explicitly be JSON true."""
    return value is True


def _call_time(call: dict) -> datetime:
    started_ms = call.get("start_timestamp")
    if started_ms is not None:
        return datetime.fromtimestamp(started_ms / 1000, tz=timezone.utc)
    return datetime.now(timezone.utc)
