"""Finite, source-grounded alert projections; original evidence stays in its source row.

Never interpolate transcripts, extracted free text, or callback summaries into these sentences.
Uncertainty and reported observations remain distinct from verified facts.
"""
import re
from collections.abc import Sequence

from sqlmodel import Session, col, select

from app.engine.risk import _affirmed, supported_danger
from app.engine.source_text import caller_text
from app.models import Callback, Event, Incident, Report

CONTEXT = {
    "flood": "near reported flooding", "water_on_road": "near reported roadway water",
    "blocked_drain": "near a reported blocked drain", "stalled_vehicle": "near a reported stalled vehicle",
    "downed_line": "near a reported downed power line", "outage": "near a reported power outage",
    "downed_tree": "near a reported downed tree", "pothole": "near a reported pothole",
    "debris": "near reported debris",
}
# Only these fixed descriptions can appear. Agent questions and negated caller statements
# cannot supply a specific indicator; a positive danger extraction still warrants review.
INDICATORS = (
    (("injured", "injuries", "injury"), "possible injuries"),
    (("trapped", "can't get out", "cannot get out", "car stuck"), "a possibly trapped person"),
    (("someone in the water",), "a person possibly in the water"),
    (("sparking",), "possible electrical sparking"),
    (("rising",), "possibly rising water"),
)


def report_summary(report: Report) -> str:
    if not supported_danger(report):
        return "Reported incident requires review; specific danger is unconfirmed"
    clauses = re.split(r"[.!?;,\n]|\b(?:but|however|yet)\b", caller_text(report.transcript).lower().replace("’", "'"))
    extracted = " ".join(report.danger_words).lower()
    for terms, description in INDICATORS:
        if any(_affirmed(term, clauses) and (report.anyone_in_danger or term in extracted) for term in terms):
            return f"Caller reports {description} {CONTEXT.get(report.hazard_type, 'at the reported location')}. Details are unverified."
    return f"Caller reports someone possibly in danger {CONTEXT.get(report.hazard_type, 'at the reported location')}. Specific danger is unconfirmed."


def callback_summary(callback: Callback) -> str:
    if callback.error_code == 'wrong_number':
        return 'Wrong number reported; further callbacks blocked; incident conditions unknown'
    if callback.error_code == 'opt_out':
        return 'Resident opted out; further callbacks blocked; incident conditions unknown'
    if callback.outcome == "no_answer":
        return "Caller unreachable; current conditions unknown, not confirmed worse"
    if callback.outcome == "worse":
        return "Resident says it's worse" + ("; reports possible danger" if callback.danger else "")
    if callback.danger:
        return "Resident reports possible danger; details are unverified"
    return {"same": "Resident reports conditions unchanged", "better": "Resident reports improvement"}.get(
        callback.outcome, "Condition update unavailable; current conditions unknown" if callback.result_recorded else "Callback pending; current conditions unknown",
    )


def alert_reason(s: Session, incident: Incident, *, evidence: Sequence[str] | None = None, kind: str | None = None) -> str:
    if (kind or incident.critical_kind) == "uncertainty":
        from app.engine.ladder import callback_blocker

        blocker = callback_blocker(s, incident)
        latest = s.exec(select(Callback).where(Callback.incident_id == incident.id).order_by(col(Callback.id).desc())).first()
        unreachable = latest is not None and latest.outcome == "no_answer"
        contact = blocker[2] if blocker else "caller unreachable" if unreachable else "follow-up needs human review"
        ending = ", not confirmed worse" if unreachable else ""
        responsibility = "responsibility accepted" if incident.status in {"accepted", "closed"} else "still unaccepted"
        return f"High risk ({incident.risk_score}), {responsibility}, {contact}; current conditions unknown{ending}"
    for ref in reversed(list(evidence if evidence is not None else incident.critical_evidence)):
        table, _, raw_id = ref.partition(":")
        if not raw_id.isdigit() or len(raw_id) > 18:
            continue
        model = {"report": Report, "callback": Callback}.get(table)
        source = s.get(model, int(raw_id)) if model else None
        if source is None or source.incident_id != incident.id:
            continue
        if isinstance(source, Report):
            return report_summary(source)
        return callback_summary(source)
    return "Reported danger requires human review; source details are unconfirmed"


def event_reason(s: Session, incident: Incident, event: Event) -> str:
    """Old databases may contain raw callback summaries in event reasons. Project safely."""
    if event.type == "callback":
        for ref in event.evidence:
            table, _, raw_id = ref.partition(":")
            if table == "callback" and raw_id.isdigit() and len(raw_id) <= 18:
                callback = s.get(Callback, int(raw_id))
                if callback and callback.incident_id == incident.id:
                    return (f"Callback #{callback.attempt_no}: resident says {callback.outcome}" + ("; possible danger reported" if callback.danger else "")) if callback.outcome else callback_summary(callback)
        return "Callback update recorded; review authorized evidence"
    if event.type == "critical":
        return "Supervisor review: " + alert_reason(s, incident, evidence=event.evidence)
    if event.type == "no_callback":
        return "Callback not placed; recorded permission and a reachable number are required"
    # Defense for historical free-text fields: multi-turn/multiline or excessive
    # content is evidence to review, never a dashboard reason. No excerpt is used.
    if len(event.reason) > 320 or "\n" in event.reason or re.search(r"\b(?:Agent|User|Assistant):", event.reason, re.I):
        return "Incident update recorded; review authorized evidence"
    return event.reason


def display_location(location: str | None) -> str:
    if not location or len(location) > 160 or "\n" in location or re.search(r"\b(?:Agent|User|Assistant):", location, re.I):
        return "location requires review"
    return location
