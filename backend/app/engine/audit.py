"""Debt list and audit-trail helpers. Every engine decision goes through log_event."""
from sqlmodel import Session, col, select

from app.models import Debt, Event
from app.timeutil import utcnow


def log_event(s: Session, incident_id: int | None, type: str, reason: str) -> Event:
    event = Event(incident_id=incident_id, type=type, reason=reason)
    s.add(event)
    return event


def open_debt(s: Session, incident_id: int, kind: str, label: str) -> Debt:
    existing = s.exec(
        select(Debt).where(Debt.incident_id == incident_id, Debt.kind == kind, col(Debt.cleared_at).is_(None))
    ).first()
    if existing:
        existing.label = label
        return existing
    debt = Debt(incident_id=incident_id, kind=kind, label=label)
    s.add(debt)
    return debt


def clear_debt(s: Session, incident_id: int, kind: str) -> None:
    for debt in s.exec(
        select(Debt).where(Debt.incident_id == incident_id, Debt.kind == kind, col(Debt.cleared_at).is_(None))
    ):
        debt.cleared_at = utcnow()
