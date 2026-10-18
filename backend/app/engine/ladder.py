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
from app.engine import critical, oncall, risk, silence, twists
from app.engine.audit import clear_debt, log_event, open_debt
from app.models import Assignment, Callback, Incident, Report
from app.timeutil import utcnow
from app.voice import callbacks

log = logging.getLogger(__name__)

ACTIVE = ("open", "escalated")


def tick(now: datetime | None = None) -> None:
    """Runs every LADDER_TICK_S seconds from main.ladder_loop; climbs one step per due incident."""
    now = now or utcnow()
    with Session(engine) as s:
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


def _nudge(s: Session, incident: Incident, now: datetime) -> None:
    department = latest_assignment(s, incident.id).department
    if not any(d.name == department and d.silent for d in silence.department_stats(s)):
        log_event(s, incident.id, "nudge", f"Not accepted after {_fmt(TIMING.nudge_s)}; reminder sent to {department}")
    else:
        log_event(s, incident.id, "nudge_suppressed", f"Department alert replaces reminder to {department}")
    incident.ladder_step = 2
    incident.next_step_at = now + timedelta(seconds=TIMING.default_owner_s - TIMING.nudge_s)


def _default_owner(s: Session, incident: Incident, now: datetime) -> None:
    assignment = latest_assignment(s, incident.id)
    name = oncall.default_owner(assignment.department, incident.area)
    if name:
        assignment.owner = name
        assignment.default_owner_at = now
        open_debt(s, incident.id, "no_owner", f"Assigned to {name}; not accepted yet")
        log_event(s, incident.id, "default_owner", f"Still not accepted; proposed owner {name}, not accepted yet")
    else:
        where = incident.area or "this area"
        open_debt(s, incident.id, "no_owner", f"No on-call contact configured for {assignment.department}")
        log_event(
            s, incident.id, "no_default_owner",
            f"No on-call contact configured for {assignment.department} in {where}; a person must assign it",
        )
    incident.ladder_step = 3
    incident.next_step_at = now + timedelta(seconds=TIMING.callback_s - TIMING.default_owner_s)


def _follow_up(s: Session, incident: Incident, now: datetime) -> None:
    """Step 4: call back a consenting caller, or record why we can't."""
    incident.ladder_step = 4
    incident.next_step_at = None
    target = callback_target(s, incident)
    if target is None:
        refresh_consent_debt(s, incident)
        log_event(s, incident.id, "no_callback", "No callback: no caller gave permission; a person must follow up")
        if incident.risk_score >= HIGH_RISK_THRESHOLD:
            critical.flag(
                s, incident, "uncertainty",
                f"High risk ({incident.risk_score}), still unaccepted, no callback permission; "
                "current conditions unknown",
            )
        return

    attempts = _count_callbacks(s, incident.id)
    if attempts >= MAX_CALLBACK_ATTEMPTS:
        return
    attempt_no = attempts + 1
    try:
        if twists.current().phones_down:
            raise ConnectionError("Simulated phone outage")
        call_id = callbacks.request_callback(
            incident.id,
            target.phone,
            attempt_no,
            {
                "location": target.location_text or incident.place or "the location you reported",
                "hazard": HAZARD_LABELS.get(incident.hazard_type, "report").lower(),
            },
        )
    except Exception as exc:
        log.warning("callback for incident %s failed: %s", incident.id, exc)
        failed = Callback(
            incident_id=incident.id, report_id=target.id, call_id=f"failed-{uuid.uuid4().hex[:8]}",
            phone=target.phone, attempt_no=attempt_no, outcome="no_answer", completed_at=now,
        )
        s.add(failed)
        s.flush()
        log_event(
            s, incident.id, "callback", f"Callback #{attempt_no} could not be placed; status unknown",
            evidence=[f"callback:{failed.id}"],
        )
        _after_no_answer(s, incident, attempt_no)
        return

    s.add(Callback(
        incident_id=incident.id, report_id=target.id, call_id=call_id,
        phone=target.phone, attempt_no=attempt_no, called_at=now,
    ))
    log_event(
        s, incident.id, "callback_requested",
        f"Callback #{attempt_no}: calling the resident who gave permission", evidence=[f"report:{target.id}"],
    )


def record_callback_outcome(o: CallbackOutcome) -> None:
    """Contract function, called by A's callback webhook and the simulator. Idempotent per call_id."""
    _record_callback_outcome(o, require_existing=False)


def record_scheduled_callback_outcome(o: CallbackOutcome) -> None:
    """A delayed simulator result is valid only for its still-pending database call.

    Reset removes that row, so an old timer cannot create a result on a reused incident ID.
    """
    _record_callback_outcome(o, require_existing=True)


def _record_callback_outcome(o: CallbackOutcome, *, require_existing: bool) -> None:
    with Session(engine) as s:
        incident = s.get(Incident, o.incident_id)
        if incident is None:
            return
        callback = s.exec(select(Callback).where(Callback.call_id == o.call_id)).first()
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
              or callback.outcome is not None):
            return  # Wrong case, wrong attempt, or a duplicate delivery.
        callback.outcome = o.outcome
        callback.danger = o.danger
        callback.summary = o.summary
        callback.completed_at = utcnow()
        s.flush()
        ref = [f"callback:{callback.id}"]

        if o.outcome == "no_answer":
            log_event(s, incident.id, "callback", f"Callback #{o.attempt_no}: no answer — status unknown, not worse", evidence=ref)
            _after_no_answer(s, incident, o.attempt_no)
        else:
            clear_debt(s, incident.id, "caller_unreachable")
            said = f"Callback #{o.attempt_no}: resident says {o.outcome}" + (f" — {o.summary}" if o.summary else "")
            log_event(s, incident.id, "callback", said, actor="resident", evidence=ref)
            incident.risk_score = risk.score(s, incident)
            if o.outcome == "worse" or o.danger:
                parts = (["Resident says it's worse"] if o.outcome == "worse" else []) + (
                    ["someone in danger"] if o.danger else []
                )
                critical.flag(
                    s, incident, "evidence", ", ".join(parts).capitalize(),
                    quote=o.summary, evidence=ref, actor="resident",
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
            f"High risk ({incident.risk_score}), still unaccepted, caller unreachable; "
            "current conditions unknown, not confirmed worse",
        )
    if attempt_no < MAX_CALLBACK_ATTEMPTS:
        incident.next_step_at = utcnow() + timedelta(seconds=TIMING.callback_retry_s)


def acknowledge(s: Session, incident: Incident, by: str) -> None:
    """Receipt only. The ladder keeps running until someone accepts."""
    assignment = latest_assignment(s, incident.id)
    if assignment is None or assignment.acknowledged_at or incident.status == "closed":
        return
    assignment.acknowledged_at = utcnow()
    assignment.acknowledged_by = by
    log_event(s, incident.id, "acknowledged", f"Acknowledged by {by} (receipt only; not accepted)", actor=by)
    s.commit()


def accept(s: Session, incident: Incident, owner: str) -> None:
    assignment = latest_assignment(s, incident.id)
    if assignment is None or incident.status in ("accepted", "closed"):
        return
    assignment.owner = owner
    assignment.accepted_at = utcnow()
    assignment.accepted_by = owner
    incident.status = "accepted"
    incident.next_step_at = None
    clear_debt(s, incident.id, "no_owner")
    log_event(s, incident.id, "accepted", f"Accepted by {owner} ({assignment.department})", actor=owner)
    s.commit()


def close(s: Session, incident: Incident, by: str, note: str = "") -> None:
    """Only a named human closes a case. Nothing in the engine calls this."""
    incident.status = "closed"
    incident.closed_at = utcnow()
    incident.closed_by = by
    incident.next_step_at = None
    log_event(s, incident.id, "closed", f"Closed by {by}" + (f": {note}" if note else ""), actor=by)
    s.commit()


def callback_target(s: Session, incident: Incident) -> Report | None:
    """The most recent linked report whose caller clearly agreed to a callback and left a number."""
    return s.exec(
        select(Report)
        .where(Report.incident_id == incident.id, Report.callback_ok == True, col(Report.phone).is_not(None))  # noqa: E712
        .order_by(col(Report.created_at).desc())
    ).first()


def refresh_consent_debt(s: Session, incident: Incident) -> None:
    if callback_target(s, incident) is None:
        open_debt(s, incident.id, "consent_unknown", "No callback permission; follow-up needs a person")
    else:
        clear_debt(s, incident.id, "consent_unknown")


def latest_assignment(s: Session, incident_id: int) -> Assignment | None:
    return s.exec(
        select(Assignment).where(Assignment.incident_id == incident_id).order_by(col(Assignment.id).desc())
    ).first()


def _count_callbacks(s: Session, incident_id: int) -> int:
    return s.exec(select(func.count()).select_from(Callback).where(Callback.incident_id == incident_id)).one()


def _fmt(seconds: int) -> str:
    return f"{seconds} s" if seconds < 120 else f"{seconds // 60} min"
