"""Durable callback attempts. Commit intent before dispatch; ambiguous sends are never retried.

The existing single-worker ladder owns timing. A provider idempotency key and trusted
metadata correlate a result even if the process dies before saving the provider call ID.
"""
import uuid
from datetime import timedelta

import httpx
from sqlmodel import Session, col, select

from app.config import CALLBACK_RESULT_TIMEOUT_S, HAZARD_LABELS, LIVE_CALLBACKS_ENABLED, MAX_CALLBACK_ATTEMPTS
from app.contracts import CallbackOutcome, CallbackStatusView
from app.db import engine
from app.engine import contact, twists
from app.engine.assignments import assignment_lock
from app.engine.audit import log_event, open_debt
from app.models import Callback, Incident, Report
from app.timeutil import from_db, utcnow
from app.voice import callbacks, simulator

ACTIVE = ('scheduled', 'dispatching', 'calling', 'unknown')


def rows(s: Session, incident_id: int):
    return s.exec(select(Callback).where(Callback.incident_id == incident_id).order_by(col(Callback.attempt_no))).all()


def cancel_pending(s: Session, incident: Incident, reason: str = 'responsibility_accepted') -> None:
    for job in rows(s, incident.id):
        if job.state == 'scheduled':
            job.state, job.error_code, job.completed_at = 'cancelled', reason, utcnow()
            log_event(s, incident.id, 'callback_cancelled', 'Pending callback cancelled before dispatch', evidence=[f'callback:{job.id}'])


def enqueue(s: Session, incident: Incident, now=None, *, by='engine', confirm_live=False) -> Callback:
    if incident.status not in ('open', 'escalated'):
        raise ValueError('Accepted or closed incidents cannot request a callback')
    prior = rows(s, incident.id)
    if any(c.state in ACTIVE or (c.outcome is None and c.mode == 'legacy') for c in prior):
        raise ValueError('A callback is already pending or requires reconciliation')
    if len(prior) >= MAX_CALLBACK_ATTEMPTS:
        raise ValueError('Callback attempt limit reached')
    report = contact.target(s, incident)
    if report is None:
        raise ValueError('Explicit consent and a valid unblocked stored number are required')
    mode = callbacks.CALL_MODE
    if mode not in ('simulate', 'live'):
        raise ValueError('Callback mode is not configured')
    if mode == 'live' and not (confirm_live if by != 'engine' else LIVE_CALLBACKS_ENABLED):
        raise ValueError('Live callbacks require explicit authorization')
    key = uuid.uuid4().hex
    job = Callback(incident_id=incident.id, report_id=report.id, phone=report.phone,
                   call_id=f'pending-{key}', request_key=key, mode=mode,
                   attempt_no=max((c.attempt_no for c in prior), default=0) + 1,
                   state='scheduled', scheduled_at=now or utcnow(), live_authorized=mode == 'live')
    s.add(job)
    s.flush()
    incident.next_step_at = None
    log_event(s, incident.id, 'callback_scheduled', f'Callback #{job.attempt_no} scheduled after consent and number checks',
              actor=by, evidence=[f'callback:{job.id}', f'report:{report.id}'])
    return job


def dispatch_due(now=None) -> None:
    now = now or utcnow()
    with assignment_lock:
        with Session(engine) as s:
            ids = list(s.exec(select(Callback.id).where(Callback.state == 'scheduled', col(Callback.scheduled_at) <= now)))
        for job_id in ids:
            _dispatch(job_id)
    finish_simulated_due()
    expire_missing_results()


def _dispatch(job_id: int) -> None:
    with Session(engine) as s:
        job = s.get(Callback, job_id)
        if job is None or job.state != 'scheduled':
            return
        incident, report = s.get(Incident, job.incident_id), s.get(Report, job.report_id)
        if (incident is None or incident.status not in ('open', 'escalated') or report is None
                or report.incident_id != incident.id or not contact.eligible_report(s, report) or report.phone != job.phone):
            job.state, job.error_code, job.completed_at = 'cancelled', 'eligibility_changed', utcnow()
            if incident:
                log_event(s, incident.id, 'callback_cancelled', 'Callback eligibility changed before dispatch', evidence=[f'callback:{job.id}'])
            s.commit()
            return
        if job.mode != callbacks.CALL_MODE or (job.mode == 'live' and not job.live_authorized):
            job.state, job.error_code = 'cancelled', 'mode_changed'
            s.commit()
            return
        # This commit is the dispatch boundary. Acceptance/closure use the same lock.
        job.state, job.dispatch_started_at = 'dispatching', utcnow()
        s.commit()
        variables = {'location': report.location_text or incident.place or 'the location you reported',
                     'hazard': HAZARD_LABELS.get(incident.hazard_type, 'Report').lower()}
        try:
            if twists.current().phones_down:
                _known_failure(s, job, 'phone_outage')
                return
            call_id = callbacks.request_callback(incident.id, job.phone, job.attempt_no, variables, request_key=job.request_key)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                _known_failure(s, job, 'provider_rejected')
            else:
                _unknown(s, job, incident)
            return
        except Exception:
            # A timeout/lost response may follow a successful provider dispatch. A
            # second attempt would risk calling twice; wait for a correlated webhook.
            _unknown(s, job, incident)
            return
        s.refresh(job)  # A fast correlated webhook may already have completed this attempt.
        if job.outcome is not None or job.state == 'completed':
            return
        job.call_id, job.state = call_id, 'calling'
        if job.mode == 'simulate':
            job.result_due_at = utcnow() + timedelta(seconds=simulator.SIMULATED_DELAY_S)
        log_event(s, incident.id, 'callback_requested', f'Callback #{job.attempt_no}: ' + ('SIMULATED follow-up' if job.mode == 'simulate' else 'calling the consenting resident'), evidence=[f'callback:{job.id}', f'report:{report.id}'])
        s.commit()
        if job.mode == 'simulate':
            simulator.schedule(incident.id, call_id, job.attempt_no)


def _known_failure(s: Session, job: Callback, code: str) -> None:
    from app.engine.ladder import record_callback_outcome

    job.error_code, job.state = code, 'failed'
    s.commit()
    record_callback_outcome(CallbackOutcome(
        incident_id=job.incident_id, call_id=job.call_id, attempt_no=job.attempt_no, outcome='no_answer'))


def _unknown(s: Session, job: Callback, incident: Incident) -> None:
    from app.config import HIGH_RISK_THRESHOLD
    from app.engine import critical

    job.state, job.error_code = 'unknown', 'dispatch_unknown'
    open_debt(s, incident.id, 'callback_unknown', 'Callback dispatch unconfirmed; human reconciliation required')
    log_event(s, incident.id, 'callback_unknown', 'Callback dispatch unconfirmed; automatic redispatch blocked', evidence=[f'callback:{job.id}'])
    if incident.risk_score >= HIGH_RISK_THRESHOLD:
        critical.flag(s, incident, 'uncertainty')
    s.commit()


def recover_interrupted() -> None:
    """Startup recovery never repeats a potentially transmitted call."""
    with Session(engine) as s:
        for job in s.exec(select(Callback).where(Callback.state == 'dispatching')):
            job.state, job.error_code = 'unknown', 'dispatch_interrupted'
        s.commit()


def finish_simulated_due() -> None:
    with Session(engine) as s:
        due = s.exec(select(Callback).where(Callback.mode == 'simulate', Callback.state == 'calling', col(Callback.result_due_at) <= utcnow())).all()
        outcomes = [(c.incident_id, c.call_id, c.attempt_no) for c in due]
    for incident_id, call_id, attempt in outcomes:
        from app.contracts import CallbackOutcome

        outcome, danger, summary = simulator.SCRIPTED_ANSWER
        simulator._deliver_scheduled(CallbackOutcome(incident_id=incident_id, call_id=call_id, attempt_no=attempt, outcome=outcome, danger=danger, summary=summary))


def expire_missing_results() -> None:
    with Session(engine) as s:
        due = s.exec(select(Callback).where(Callback.state == 'calling', col(Callback.dispatch_started_at) < utcnow() - timedelta(seconds=CALLBACK_RESULT_TIMEOUT_S))).all()
        for job in due:
            job.state, job.error_code = 'unknown', 'result_missing'
            open_debt(s, job.incident_id, 'callback_unknown', 'Callback result missing; human review required before another call')
        s.commit()


def status(s: Session, incident: Incident) -> CallbackStatusView:
    jobs = rows(s, incident.id)
    blocked = contact.blocker(s, incident)
    reason = blocked[1] if blocked else 'Explicit consent and a valid stored resident number are present'
    eligible = blocked is None and incident.status in ('open', 'escalated') and len(jobs) < MAX_CALLBACK_ATTEMPTS
    if incident.status not in ('open', 'escalated'):
        eligible, reason = False, 'Responsibility accepted or incident closed; automatic callback cancelled'
    elif any(c.state in ACTIVE for c in jobs):
        eligible, reason = False, 'Callback already pending or awaiting reconciliation'
    elif len(jobs) >= MAX_CALLBACK_ATTEMPTS:
        eligible, reason = False, 'Callback attempt limit reached'
    deadline = next((c.scheduled_at for c in jobs if c.state == 'scheduled'), None)
    if deadline is None and eligible and incident.ladder_step == 3:
        deadline = incident.next_step_at
    return CallbackStatusView(eligible=eligible, reason=reason, scheduled_at=from_db(deadline),
                              attempts_used=len(jobs), max_attempts=MAX_CALLBACK_ATTEMPTS,
                              call_mode=callbacks.CALL_MODE, automatic_live_enabled=LIVE_CALLBACKS_ENABLED)
