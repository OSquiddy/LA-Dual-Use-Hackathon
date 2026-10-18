"""DB rows -> the REST shapes in contracts.py."""
from sqlmodel import Session, col, func, select

from app.config import DANGER_WORDS, HAZARD_LABELS, TIMING_PROFILE
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
from app.engine import callback_jobs, contact, silence, supervisor, twists
from app.engine.evidence import alert_reason, callback_summary, display_location, event_reason
from app.engine.ladder import callback_blocker, latest_assignment
from app.models import Assignment, Callback, ContactPreference, Debt, Event, Incident, Report
from app.timeutil import from_db, utcnow


def incident_view(s: Session, incident: Incident) -> IncidentView:
    assignment = latest_assignment(s, incident.id)
    report_count = s.exec(select(func.count()).select_from(Report).where(Report.incident_id == incident.id)).one()
    debts = s.exec(select(Debt).where(Debt.incident_id == incident.id, col(Debt.cleared_at).is_(None))).all()
    last_event = s.exec(select(Event).where(Event.incident_id == incident.id).order_by(col(Event.id).desc())).first()
    why = alert_reason(s, incident) if incident.critical else (event_reason(s, incident, last_event) if last_event else "")
    # Derive contact blockers from persisted report consent, including older rows
    # mislabeled as no-consent when only a callback number was missing. No writes.
    projected_debts = [DebtView(kind=d.kind, label=d.label) for d in debts if d.kind not in {"consent_unknown", "callback_number_missing", "callback_number_invalid", "callback_opt_out"}]
    blocker = callback_blocker(s, incident)
    if blocker:
        projected_debts.append(DebtView(kind=blocker[0], label=blocker[1]))
    return IncidentView(
        id=incident.id,
        title=f"{HAZARD_LABELS.get(incident.hazard_type, 'Report')} — {display_location(incident.place or incident.title.split(' — ', 1)[-1])}",
        hazard_type=incident.hazard_type,
        status=incident.status,
        ladder_step=5 if incident.critical else incident.ladder_step,
        risk_score=incident.risk_score,
        report_count=report_count,
        department=assignment.department if assignment else None,
        owner=assignment.owner if assignment else None,
        accepted=bool(assignment and assignment.accepted_at),
        next_step_at=from_db(incident.next_step_at),
        debts=projected_debts,
        why=why or "",
        lat=incident.lat,
        lng=incident.lng,
        acknowledged=bool(assignment and assignment.acknowledged_at),
        critical=incident.critical,
        assignment=assignment_view(s, assignment) if assignment else None,
        closed_at=from_db(incident.closed_at),
        closed_by=incident.closed_by,
    )


def incident_detail_view(s: Session, incident: Incident, *, include_evidence: bool = False) -> IncidentDetailView:
    base = incident_view(s, incident)
    reports = s.exec(select(Report).where(Report.incident_id == incident.id).order_by(col(Report.created_at))).all()
    events = s.exec(select(Event).where(Event.incident_id == incident.id).order_by(col(Event.id))).all()
    callbacks = s.exec(select(Callback).where(Callback.incident_id == incident.id).order_by(col(Callback.id))).all()
    history = s.exec(select(Assignment).where(Assignment.incident_id == incident.id).order_by(col(Assignment.id))).all()
    return IncidentDetailView(
        **base.model_dump(),
        reports=[
            ReportView(
                id=r.id,
                call_id=r.call_id,
                phone=mask_phone(r.phone),
                location_text=r.location_text if include_evidence else display_location(r.location_text),
                hazard_type=r.hazard_type,
                danger_words=r.danger_words if include_evidence else [word for word in DANGER_WORDS if word in r.danger_words],
                transcript=r.transcript if include_evidence else "",
                created_at=from_db(r.created_at),
                callback_ok=r.callback_ok,
                callback_opt_out=r.callback_opt_out or bool(r.phone and s.get(ContactPreference, r.phone)),
                callback_eligible=contact.eligible_report(s, r),
            )
            for r in reports
        ],
        events=[
            EventView(type=e.type, reason=event_reason(s, incident, e), at=from_db(e.at), actor=e.actor, evidence=e.evidence)
            for e in events
        ],
        callbacks=[
            CallbackView(
                attempt_no=c.attempt_no,
                outcome=c.outcome,
                danger=c.danger,
                summary=c.summary if include_evidence else callback_summary(c),
                called_at=from_db(c.called_at),
                id=c.id, state=c.state, scheduled_at=from_db(c.scheduled_at), completed_at=from_db(c.completed_at),
                error_code=c.error_code, mode=c.mode, transcript=c.transcript if include_evidence else '',
            )
            for c in callbacks
        ],
        assignment_history=[assignment_view(s, assignment) for assignment in history],
        callback_status=callback_jobs.status(s, incident),
    )


def assignment_view(s: Session, assignment: Assignment) -> AssignmentView:
    ref = f"assignment:{assignment.id}"
    events = s.exec(select(Event).where(Event.incident_id == assignment.incident_id).order_by(col(Event.id))).all()
    creation = next((e for e in events if e.type in {"assigned", "reassigned", "default_owner"} and e.evidence[:1] == [ref]), None)
    return AssignmentView(
        id=assignment.id, department=assignment.department, owner=assignment.owner,
        assigned_at=from_db(assignment.assigned_at), default_owner_at=from_db(assignment.default_owner_at),
        acknowledged_at=from_db(assignment.acknowledged_at), acknowledged_by=assignment.acknowledged_by,
        accepted_at=from_db(assignment.accepted_at), accepted_by=assignment.accepted_by,
        assigned_by=creation.actor if creation else None,
        change_reason=event_reason(s, s.get(Incident, assignment.incident_id), creation) if creation else None,
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
    return f"•••{phone[-4:]}" if phone and phone.strip() else None
