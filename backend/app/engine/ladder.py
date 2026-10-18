"""The escalation ladder (B7–B11) and the contract function record_callback_outcome.

Steps (timing from config.TIMING): 1 assigned -> 2 nudge -> 3 default on-call owner -> 4 follow-up.
Step 4 calls back only a caller who said yes (callback_ok). Supervisor review (shown as step 5) is a
critical alert raised on evidence (danger, "worse") or on high risk that nobody owns and nobody can
confirm. Age advances the handoff; it never touches the risk score.

Never automated: accepting for a human, closing a case, deciding someone is safe because they didn't
answer, calling without consent, dispatching emergency services, issuing or lifting an order.
"""
import logging
import uuid
from datetime import datetime, timedelta

from sqlmodel import Session, col, func, select

from app.config import HAZARD_LABELS, HIGH_RISK_THRESHOLD, MAX_CALLBACK_ATTEMPTS, TIMING
from app.contracts import CallbackOutcome
from app.db import engine
from app.engine import callback_jobs, contact, critical, oncall, risk, silence, twists
from app.engine.audit import clear_debt, log_event, open_debt
from app.engine.assignments import assign, assignment_lock, latest_assignment
from app.models import Assignment, Callback, Incident, Report
from app.timeutil import utcnow
from app.voice import callbacks

log = logging.getLogger(__name__)

ACTIVE = ("open", "escalated")


def tick(now: datetime | None = None) -> None:
    """Runs every LADDER_TICK_S seconds from main.ladder_loop; climbs one step per due incident."""
    now = now or utcnow()
    with assignment_lock, Session(engine) as s:
        due = s.exec(
            select(Incident).where(
                col(Incident.status).in_(ACTIVE),
                col(Incident.next_step_at).is_not(None),
                col(Incident.next_step_at) <= now,
            )
        ).all()
        for incident in due:
            if incident.ladder_step == 1:
                _nudge(s, incident, now)
            elif incident.ladder_step == 2:
                _default_owner(s, incident, now)
            else:
                _follow_up(s, incident, now)
            s.commit()
        callback_jobs.dispatch_due(now)


def _nudge(s: Session, incident: Incident, now: datetime) -> None:
    assignment = latest_assignment(s, incident.id)
    if assignment is None:
        _missing_department(s, incident)
        return
    department = assignment.department
    if not any(d.name == department and d.silent for d in silence.department_stats(s)):
        log_event(s, incident.id, "nudge", f"Not accepted after {_fmt(TIMING.nudge_s)}; reminder sent to {department}")
    else:
        log_event(s, incident.id, "nudge_suppressed", f"Department alert replaces reminder to {department}")
    incident.ladder_step = 2
    incident.next_step_at = now + timedelta(seconds=TIMING.default_owner_s - TIMING.nudge_s)


def _default_owner(s: Session, incident: Incident, now: datetime) -> None:
    assignment = latest_assignment(s, incident.id)
    if assignment is None:
        _missing_department(s, incident)
        return
    name = oncall.default_owner(assignment.department, incident.area)
    if assignment.owner:
        pass  # An explicit assignment is not replaced by the automatic roster step.
    elif name:
        assign(s, incident, assignment.department, name, by="engine", now=now, from_roster=True,
               reset_ladder=False, reason="Configured demo on-call roster; not acknowledged or accepted.")
    else:
        where = incident.area or "this area"
        open_debt(s, incident.id, "no_owner", f"No on-call contact configured for {assignment.department}")
        log_event(
            s, incident.id, "no_default_owner",
            f"No on-call contact configured for {assignment.department} in {where}; a person must assign it",
        )
    incident.ladder_step = 3
    incident.next_step_at = now + timedelta(seconds=TIMING.callback_s - TIMING.default_owner_s)


def _missing_department(s: Session, incident: Incident) -> None:
    incident.next_step_at = None
    open_debt(s, incident.id, "department_assignment", "Responsible department not assigned; a human must assign it")
    log_event(s, incident.id, "assignment_missing", "Awaiting department assignment; no individual or acceptance has been inferred")


def _follow_up(s: Session, incident: Incident, now: datetime) -> None:
    """Step 4: call back a consenting caller, or record why we can't."""
    incident.ladder_step = 4
    incident.next_step_at = None
    target = callback_target(s, incident)
    if target is None:
        refresh_consent_debt(s, incident)
        blocker = callback_blocker(s, incident)
        log_event(s, incident.id, "no_callback", f"No callback: {blocker[2]}; a person must follow up")
        if incident.risk_score >= HIGH_RISK_THRESHOLD:
            critical.flag(
                s, incident, "uncertainty",
            )
        return

    try:
        callback_jobs.enqueue(s, incident, now)
    except ValueError:
        log_event(s, incident.id, 'callback_blocked', 'Callback not scheduled: pending attempt, attempt limit, or live authorization gate')


def record_callback_outcome(o: CallbackOutcome) -> None:
    """Contract function, called by A's callback webhook and the simulator. Idempotent per call_id."""
    _record_callback_outcome(o, require_existing=False)


def record_verified_callback_outcome(o: CallbackOutcome) -> None:
    """A verified agent still needs metadata bound to a durable dispatched attempt."""
    with assignment_lock:
        with Session(engine) as s:
            job = s.exec(select(Callback).where(Callback.call_id == o.call_id)).first()
            if job is None and o.request_key:
                job = s.exec(select(Callback).where(Callback.request_key == o.request_key)).first()
            if (job is None or job.incident_id != o.incident_id or job.attempt_no != o.attempt_no
                    or job.state in ('scheduled', 'cancelled')
                    or (o.request_key is not None and job.request_key != o.request_key)):
                raise ValueError('Callback is not bound to a dispatched request')
        _record_callback_outcome(o, require_existing=True)


def record_scheduled_callback_outcome(o: CallbackOutcome) -> None:
    """A delayed simulator result is valid only for its still-pending database call.

    Reset removes that row, so an old timer cannot create a result on a reused incident ID.
    """
    _record_callback_outcome(o, require_existing=True)


def _record_callback_outcome(o: CallbackOutcome, *, require_existing: bool) -> None:
    with assignment_lock, Session(engine) as s:
        incident = s.get(Incident, o.incident_id)
        if incident is None:
            return
        callback = s.exec(select(Callback).where(Callback.call_id == o.call_id)).first()
        if callback is None and o.request_key:
            callback = s.exec(select(Callback).where(Callback.request_key == o.request_key)).first()
            if callback and callback.state not in ('scheduled', 'cancelled'):
                callback.call_id = o.call_id
        if callback is None:
            if require_existing:
                return
            attempt = s.exec(select(Callback).where(
                Callback.incident_id == o.incident_id, Callback.attempt_no == o.attempt_no,
            )).first()
            if attempt is not None:
                return  # A different call ID cannot overwrite this attempt's evidence.
            callback = Callback(incident_id=o.incident_id, call_id=o.call_id, attempt_no=o.attempt_no)
            s.add(callback)
        elif (callback.incident_id != o.incident_id or callback.attempt_no != o.attempt_no
              or callback.outcome is not None or callback.result_recorded or callback.state == 'cancelled'):
            return  # Wrong case, wrong attempt, or a duplicate delivery.
        if o.callback_opt_out or o.wrong_number:
            report = s.get(Report, callback.report_id) if callback.report_id else None
            if report:
                contact.block(s, report, 'wrong_number' if o.wrong_number else 'opt_out')
        callback.outcome = None if o.wrong_number else o.outcome
        callback.danger = False if o.wrong_number else o.danger
        callback.summary = o.summary
        callback.transcript = o.transcript
        callback.result_recorded = True
        callback.state = 'failed' if callback.error_code in ('phone_outage', 'provider_rejected') else 'completed'
        if o.outcome is None:
            callback.error_code = 'wrong_number' if o.wrong_number else 'opt_out' if o.callback_opt_out else 'analysis_missing'
            callback.state = 'completed' if o.callback_opt_out or o.wrong_number else 'unknown'
        clear_debt(s, incident.id, 'callback_unknown')
        callback.completed_at = utcnow()
        s.flush()
        ref = [f"callback:{callback.id}"]

        if callback.outcome is None:
            log_event(s, incident.id, 'callback', 'Callback completed without a verified condition update; human review required', evidence=ref)
            if callback.danger:
                critical.flag(s, incident, 'evidence', evidence=ref, actor='resident')
        elif o.outcome == "no_answer":
            log_event(s, incident.id, "callback", f"Callback #{o.attempt_no}: no answer — status unknown, not worse", evidence=ref)
            _after_no_answer(s, incident, o.attempt_no)
        else:
            clear_debt(s, incident.id, "caller_unreachable")
            said = f"Callback #{o.attempt_no}: resident says {o.outcome}" + ("; possible danger reported" if o.danger else "")
            log_event(s, incident.id, "callback", said, actor="resident", evidence=ref)
            incident.risk_score = risk.score(s, incident)
            if o.outcome == "worse" or o.danger:
                critical.flag(
                    s, incident, "evidence",
                    evidence=ref, actor="resident",
                )
        s.commit()


def _after_no_answer(s: Session, incident: Incident, attempt_no: int) -> None:
    """A missed call is a contact debt, never evidence that conditions changed."""
    missed = s.exec(
        select(func.count()).select_from(Callback)
        .where(Callback.incident_id == incident.id, Callback.outcome == "no_answer")
    ).one()
    open_debt(s, incident.id, "caller_unreachable", f"Caller unreachable ({missed} missed)")
    if incident.status not in ACTIVE:
        return
    if incident.risk_score >= HIGH_RISK_THRESHOLD:
        critical.flag(
            s, incident, "uncertainty",
        )
    if (attempt_no < MAX_CALLBACK_ATTEMPTS and contact.target(s, incident) is not None
            and (callbacks.CALL_MODE != "live" or callback_jobs.LIVE_CALLBACKS_ENABLED)):
        incident.next_step_at = utcnow() + timedelta(seconds=TIMING.callback_retry_s)


def acknowledge(s: Session, incident: Incident, by: str) -> None:
    """Receipt only. The ladder keeps running until someone accepts."""
    assignment = latest_assignment(s, incident.id)
    if assignment is None or assignment.acknowledged_at or incident.status == "closed":
        return
    assignment.acknowledged_at = utcnow()
    assignment.acknowledged_by = by
    log_event(s, incident.id, "acknowledged", f"Acknowledged by {by} for {assignment.department} (receipt only; not accepted)",
              actor=by, evidence=[f"assignment:{assignment.id}"])
    s.commit()


def accept(s: Session, incident: Incident, owner: str) -> None:
    assignment = latest_assignment(s, incident.id)
    if assignment is None or incident.status in ("accepted", "closed"):
        return
    if assignment.owner != owner:
        assignment = assign(s, incident, assignment.department, owner, by=owner,
                            reason="Named human took responsibility; prior assignment retained.")
    assignment.accepted_at = utcnow()
    assignment.accepted_by = owner
    callback_jobs.cancel_pending(s, incident)
    incident.status = "accepted"
    incident.next_step_at = None
    clear_debt(s, incident.id, "no_owner")
    log_event(s, incident.id, "accepted", f"Accepted by {owner} ({assignment.department})", actor=owner,
              evidence=[f"assignment:{assignment.id}"])
    s.commit()


def close(s: Session, incident: Incident, by: str, note: str = "") -> None:
    """Only a named human closes a case. Nothing in the engine calls this."""
    if incident.status == "closed":
        return
    callback_jobs.cancel_pending(s, incident, "incident_closed")
    incident.status = "closed"
    incident.closed_at = utcnow()
    incident.closed_by = by
    incident.next_step_at = None
    assignment = latest_assignment(s, incident.id)
    log_event(s, incident.id, "closed", f"Closed by {by}" + (f": {note}" if note else ""), actor=by,
              evidence=[f"assignment:{assignment.id}"] if assignment else [])
    s.commit()


def callback_target(s: Session, incident: Incident) -> Report | None:
    return contact.target(s, incident)


def callback_blocker(s: Session, incident: Incident) -> tuple[str, str, str] | None:
    return contact.blocker(s, incident)


def refresh_consent_debt(s: Session, incident: Incident) -> None:
    blocker = callback_blocker(s, incident)
    for kind in ("consent_unknown", "callback_number_missing", "callback_number_invalid", "callback_opt_out"):
        if not blocker or kind != blocker[0]:
            clear_debt(s, incident.id, kind)
    if blocker:
        open_debt(s, incident.id, blocker[0], blocker[1])


def _count_callbacks(s: Session, incident_id: int) -> int:
    return s.exec(select(func.count()).select_from(Callback).where(Callback.incident_id == incident_id)).one()


def _fmt(seconds: int) -> str:
    return f"{seconds} s" if seconds < 120 else f"{seconds // 60} min"
