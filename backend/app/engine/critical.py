"""Critical alerts: what the supervisor must see regardless of the top-10 cap.

Two kinds, kept apart so we never claim more than we know:
- evidence:    a person in danger, or a resident says it's worse.
- uncertainty: already high risk, still unaccepted, and we can't reach anyone. Status unknown, NOT worse.
An evidence alert is never replaced by an uncertainty one. Only a human close clears the alert.
"""
from collections.abc import Sequence

from sqlmodel import Session

from app.engine.audit import log_event
from app.models import Incident
from app.timeutil import utcnow


def flag(
    s: Session,
    incident: Incident,
    kind: str,
    reason: str,
    quote: str = "",
    evidence: Sequence[str] = (),
    actor: str = "engine",
) -> None:
    if incident.status == "closed":
        return
    if incident.critical and incident.critical_kind == "evidence" and kind == "uncertainty":
        return
    if incident.critical and incident.critical_reason == reason:
        return
    if not incident.critical:
        incident.critical_since = utcnow()
    incident.critical = True
    incident.critical_kind = kind
    incident.critical_reason = reason
    incident.critical_quote = quote
    incident.critical_evidence = list(evidence)
    if incident.status == "open":
        incident.status = "escalated"
    log_event(s, incident.id, "critical", f"Supervisor review: {reason}", actor=actor, evidence=evidence)
