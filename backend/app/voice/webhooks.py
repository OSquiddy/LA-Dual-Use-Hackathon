"""A3/A9: Retell call webhooks -> ReportIn (intake) or CallbackOutcome (callback).

Point the Retell webhook at  {PUBLIC_BASE_URL}/retell/webhook.
Payload field names below are our best reading of Retell's docs; check them against the first real
payload (save it as tests/fixtures/retell_call_analyzed.json) and fix the mapping here.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response

from app.config import HAZARD_TYPES
from app.contracts import CallbackOutcome, ReportIn
from app.engine.ingest import ingest_report
from app.engine.ladder import record_callback_outcome

log = logging.getLogger(__name__)
router = APIRouter()

NO_ANSWER_REASONS = {"dial_no_answer", "voicemail_reached", "dial_busy", "dial_failed"}


@router.post("/retell/webhook")
async def retell_webhook(request: Request) -> Response:
    # TODO(A3): verify the x-retell-signature header with RETELL_API_KEY before trusting the body.
    body = await request.json()
    event, call = body.get("event"), body.get("call", {})
    log.info("retell %s %s", event, call.get("call_id"))

    if event == "call_analyzed":
        metadata = call.get("metadata") or {}
        if "incident_id" in metadata:
            record_callback_outcome(callback_from_call(call))
        else:
            ingest_report(intake_from_call(call))
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
        anyone_in_danger=bool(fields.get("anyone_in_danger")),
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
        danger=bool(fields.get("anyone_in_danger")),
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
