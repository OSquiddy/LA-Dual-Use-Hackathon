"""The escalation ladder (B7–B11) and the contract function record_callback_outcome.

Never automated: closing a case, deciding someone is safe because they didn't answer,
dispatching emergency services, issuing or lifting an order.
"""
from sqlmodel import Session, col, select

from app.contracts import CallbackOutcome
from app.db import engine
from app.engine import risk
from app.engine.audit import clear_debt, log_event
from app.models import Assignment, Callback, Incident
from app.timeutil import utcnow


def tick() -> None:
    """Runs every LADDER_TICK_S seconds from main.ladder_loop.

    TODO(B7): for each open incident whose next_step_at has passed, climb one step:
      1 -> 2 nudge the department queue
      2 -> 3 default owner from seeds/oncall.json (B8)
      3 -> 4 ONLY if the caller's callback_ok is true: voice.callbacks.request_callback(...) and
             insert a Callback row. No consent -> no call, log the reason, keep the debt.
      4 -> 5 supervisor review on explicit worsening / reported danger, or an already high-risk
             case whose caller is unreachable (no_answer alone never means worse) (B9)
    Log an Event with a one-line reason at every step. Age advances the handoff, never the risk score.
    """


def accept(s: Session, incident: Incident, owner: str) -> None:
    assignment = latest_assignment(s, incident.id)
    if assignment is None or incident.status == "closed":
        return
    assignment.owner = owner
    assignment.accepted_at = utcnow()
    incident.status = "accepted"
    incident.next_step_at = None
    clear_debt(s, incident.id, "no_owner")
    log_event(s, incident.id, "accepted", f"Accepted by {owner} ({assignment.department})")
    s.commit()


def close(s: Session, incident: Incident, by: str, note: str = "") -> None:
    """Only a named human closes a case. Nothing in the engine calls this."""
    incident.status = "closed"
    incident.closed_at = utcnow()
    incident.closed_by = by
    incident.next_step_at = None
    log_event(s, incident.id, "closed", f"Closed by {by}" + (f": {note}" if note else ""))
    s.commit()


def record_callback_outcome(o: CallbackOutcome) -> None:
    """Contract function, called by A's callback webhook and the simulator."""
    with Session(engine) as s:
        incident = s.get(Incident, o.incident_id)
        if incident is None:
            return
        callback = s.exec(select(Callback).where(Callback.call_id == o.call_id)).first()
        if callback is None:
            callback = Callback(incident_id=o.incident_id, call_id=o.call_id, attempt_no=o.attempt_no)
            s.add(callback)
        callback.outcome = o.outcome
        callback.danger = o.danger
        callback.summary = o.summary
        callback.completed_at = utcnow()

        said = "no answer" if o.outcome == "no_answer" else f"resident says {o.outcome}"
        log_event(s, incident.id, "callback", f"Callback #{o.attempt_no}: {said}" + (f" — {o.summary}" if o.summary else ""))
        # TODO(B9): open/clear caller_unreachable; retry on no_answer only within the agreed
        # consent and retry policy; step 5 on worse / danger, or no_answer on an already
        # high-risk case. no_answer is unknown status, not evidence of worsening.
        incident.risk_score = max(incident.risk_score, risk.score(s, incident))
        s.commit()


def latest_assignment(s: Session, incident_id: int) -> Assignment | None:
    return s.exec(
        select(Assignment).where(Assignment.incident_id == incident_id).order_by(col(Assignment.id).desc())
    ).first()
