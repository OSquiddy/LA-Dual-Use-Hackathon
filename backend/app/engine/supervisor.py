"""B10: the supervisor's ranked, capped queue, plus the uncapped critical-alert lane."""
from sqlmodel import Session, col, func, select

from app.config import SUPERVISOR_MIN_RISK, SUPERVISOR_QUEUE_SIZE
from app.contracts import CriticalAlertView
from app.models import Debt, Incident
from app.timeutil import from_db

UNCERTAINTY_DEBTS = ("caller_unreachable", "consent_unknown", "location", "no_owner")


def queue(s: Session) -> list[int]:
    """Top 10 unaccepted incidents that need a supervisor: critical, or risk >= SUPERVISOR_MIN_RISK.

    Ranked by evidence-based risk. Ties go to the case we know least about (more open uncertainty
    debts), then the oldest. Low-risk unaccepted cases stay with their department's ladder.
    """
    rows = s.exec(select(Incident).where(col(Incident.status).in_(["open", "escalated"]))).all()
    eligible = [i for i in rows if i.critical or i.risk_score >= SUPERVISOR_MIN_RISK]
    eligible.sort(key=lambda i: (-i.risk_score, -_uncertainty(s, i), i.created_at))
    return [i.id for i in eligible[:SUPERVISOR_QUEUE_SIZE]]


def critical_alerts(s: Session) -> list[CriticalAlertView]:
    from app.engine.ladder import latest_assignment

    rows = s.exec(
        select(Incident)
        .where(Incident.critical == True, Incident.status != "closed")  # noqa: E712
        .order_by(col(Incident.risk_score).desc(), col(Incident.critical_since))
    ).all()
    alerts = []
    for incident in rows:
        assignment = latest_assignment(s, incident.id)
        alerts.append(CriticalAlertView(
            incident_id=incident.id,
            title=incident.title,
            reason=incident.critical_reason or "",
            quote=incident.critical_quote,
            evidence=incident.critical_evidence,
            since=from_db(incident.critical_since),
            accepted=bool(assignment and assignment.accepted_at),
            owner=assignment.owner if assignment else None,
        ))
    return alerts


def _uncertainty(s: Session, incident: Incident) -> int:
    return s.exec(
        select(func.count()).select_from(Debt).where(
            Debt.incident_id == incident.id, col(Debt.kind).in_(UNCERTAINTY_DEBTS), col(Debt.cleared_at).is_(None)
        )
    ).one()
