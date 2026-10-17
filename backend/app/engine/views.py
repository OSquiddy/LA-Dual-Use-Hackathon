"""DB rows -> the REST shapes in contracts.py."""
from sqlmodel import Session, col, func, select

from app.config import TIMING_PROFILE
from app.contracts import (
    AssignmentView,
    CallbackView,
    DebtView,
    EventView,
    IncidentDetailView,
    IncidentView,
    ReportView,
    StateView,
)
from app.engine import silence, supervisor, twists
from app.engine.ladder import latest_assignment
from app.models import Callback, Debt, Event, Incident, Report
from app.timeutil import from_db, utcnow


def incident_view(s: Session, incident: Incident) -> IncidentView:
    assignment = latest_assignment(s, incident.id)
    report_count = s.exec(select(func.count()).select_from(Report).where(Report.incident_id == incident.id)).one()
    debts = s.exec(select(Debt).where(Debt.incident_id == incident.id, col(Debt.cleared_at).is_(None))).all()
    last_event = s.exec(select(Event).where(Event.incident_id == incident.id).order_by(col(Event.id).desc())).first()
    why = incident.critical_reason if incident.critical else (last_event.reason if last_event else "")
    return IncidentView(
        id=incident.id,
        title=incident.title,
        hazard_type=incident.hazard_type,
        status=incident.status,
        ladder_step=5 if incident.critical else incident.ladder_step,
        risk_score=incident.risk_score,
        report_count=report_count,
        department=assignment.department if assignment else None,
        owner=assignment.owner if assignment else None,
        accepted=bool(assignment and assignment.accepted_at),
        next_step_at=from_db(incident.next_step_at),
        debts=[DebtView(kind=d.kind, label=d.label) for d in debts],
        why=why or "",
        lat=incident.lat,
        lng=incident.lng,
        acknowledged=bool(assignment and assignment.acknowledged_at),
        critical=incident.critical,
    )


def incident_detail_view(s: Session, incident: Incident) -> IncidentDetailView:
    base = incident_view(s, incident)
    reports = s.exec(select(Report).where(Report.incident_id == incident.id).order_by(col(Report.created_at))).all()
    events = s.exec(select(Event).where(Event.incident_id == incident.id).order_by(col(Event.id))).all()
    callbacks = s.exec(select(Callback).where(Callback.incident_id == incident.id).order_by(col(Callback.id))).all()
    assignment = latest_assignment(s, incident.id)
    return IncidentDetailView(
        **base.model_dump(),
        reports=[
            ReportView(
                id=r.id,
                call_id=r.call_id,
                phone=mask_phone(r.phone),
                location_text=r.location_text,
                hazard_type=r.hazard_type,
                danger_words=r.danger_words,
                transcript=r.transcript,
                created_at=from_db(r.created_at),
                callback_ok=r.callback_ok,
            )
            for r in reports
        ],
        events=[
            EventView(type=e.type, reason=e.reason, at=from_db(e.at), actor=e.actor, evidence=e.evidence)
            for e in events
        ],
        callbacks=[
            CallbackView(
                attempt_no=c.attempt_no,
                outcome=c.outcome,
                danger=c.danger,
                summary=c.summary,
                called_at=from_db(c.called_at),
            )
            for c in callbacks
        ],
        assignment=AssignmentView(
            department=assignment.department,
            owner=assignment.owner,
            assigned_at=from_db(assignment.assigned_at),
            accepted_at=from_db(assignment.accepted_at),
            default_owner_at=from_db(assignment.default_owner_at),
            acknowledged_at=from_db(assignment.acknowledged_at),
            acknowledged_by=assignment.acknowledged_by,
            accepted_by=assignment.accepted_by,
        )
        if assignment
        else None,
    )


def state_view(s: Session) -> StateView:
    incidents = s.exec(
        select(Incident).where(Incident.status != "closed").order_by(col(Incident.risk_score).desc())
    ).all()
    return StateView(
        now=from_db(utcnow()),
        timing_profile=TIMING_PROFILE,
        twists=twists.current(),
        incidents=[incident_view(s, i) for i in incidents],
        supervisor_queue=supervisor.queue(s),
        departments=silence.department_stats(s),
        alerts=silence.alerts(s),
        critical_alerts=supervisor.critical_alerts(s),
    )


def mask_phone(phone: str | None) -> str | None:
    """The dashboard never shows a full resident number."""
    return f"•••{phone[-4:]}" if phone else None
