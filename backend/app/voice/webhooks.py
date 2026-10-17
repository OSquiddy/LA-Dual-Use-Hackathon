"""A3/A9: Retell call webhooks -> ReportIn (intake) or CallbackOutcome (callback).

Point the Retell webhook at  {PUBLIC_BASE_URL}/retell/webhook.
Payload field names below are our best reading of Retell's docs; check them against the first real
payload (save it as tests/fixtures/retell_call_analyzed.json) and fix the mapping here.
"""
import logging
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import ValidationError

from app.config import HAZARD_TYPES, RETELL_API_KEY
from app.voice.security import verify_signature
from app.contracts import CallbackOutcome, ReportIn
from app.engine.ingest import ingest_report
from app.engine.ladder import record_callback_outcome

log = logging.getLogger(__name__)
router = APIRouter()

NO_ANSWER_REASONS = {"dial_no_answer", "voicemail_reached", "dial_busy", "dial_failed"}


@router.post("/retell/webhook")
async def retell_webhook(request: Request) -> Response:
    raw = await request.body()
    if not verify_signature(raw, request.headers.get("x-retell-signature", ""), RETELL_API_KEY):
        raise HTTPException(401, "Invalid webhook signature")
    try:
        body = json.loads(raw)
        if not isinstance(body, dict) or not isinstance(body.get("event"), str):
            raise ValueError("Expected event object")
        event = body["event"]
        if event != "call_analyzed":
            return Response(status_code=204)
        call = body.get("call")
        if not isinstance(call, dict) or not isinstance(call.get("call_id"), str) or not call["call_id"].strip():
            raise ValueError("Missing call ID")
        metadata = call.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ValueError("Invalid metadata")
        if "incident_id" in metadata:
            outcome = callback_from_call(call)
            if outcome.incident_id <= 0 or outcome.attempt_no <= 0:
                raise ValueError("Invalid callback identifiers")
        else:
            report = intake_from_call(call)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, OSError, ValidationError):
        # Never echo provider payloads, phone numbers, or transcripts in errors.
        raise HTTPException(422, "Invalid webhook payload") from None
    if "incident_id" in metadata:
        record_callback_outcome(outcome)
    else:
        ingest_report(report)
    return Response(status_code=204)


def intake_from_call(call: dict) -> ReportIn:
    fields = (call.get("call_analysis") or {}).get("custom_analysis_data") or {}
    hazard = fields.get("hazard_type") or "other"
    return ReportIn(
        source="retell",
        call_id=call["call_id"],
        phone=call.get("from_number"),
        location_text=fields.get("location_text"),
        hazard_type=hazard if hazard in HAZARD_TYPES else "other",
        danger_words=_as_list(fields.get("danger_words")),
        anyone_in_danger=_boolean(fields.get("anyone_in_danger")),
        transcript=call.get("transcript") or "",
        created_at=_call_time(call),
    )


def callback_from_call(call: dict) -> CallbackOutcome:
    metadata = call.get("metadata") or {}
    fields = (call.get("call_analysis") or {}).get("custom_analysis_data") or {}
    outcome = fields.get("outcome")
    if call.get("disconnection_reason") in NO_ANSWER_REASONS or outcome not in ("worse", "same", "better"):
        outcome = "no_answer"
    return CallbackOutcome(
        incident_id=int(metadata["incident_id"]),
        call_id=call["call_id"],
        attempt_no=int(metadata.get("attempt_no", 1)),
        outcome=outcome,
        danger=_boolean(fields.get("anyone_in_danger")),
        summary=fields.get("summary") or "",
        transcript=call.get("transcript") or "",
    )


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value.strip():
        return [w.strip() for w in value.split(",") if w.strip()]
    return []


def _call_time(call: dict) -> datetime:
    started_ms = call.get("start_timestamp")
    if started_ms:
        return datetime.fromtimestamp(started_ms / 1000, tz=timezone.utc)
    return datetime.now(timezone.utc)


def _boolean(value) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ValueError("Expected boolean")
    return value
