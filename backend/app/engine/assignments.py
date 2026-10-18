"""Responsibility transitions using existing Assignment rows and append-only Events."""
from collections.abc import Sequence
from datetime import datetime, timedelta
from threading import RLock

from sqlmodel import Session, col, select

from app.config import TIMING
from app.engine.audit import clear_debt, open_debt, log_event
from app.engine import oncall
from app.models import Assignment, Incident
from app.timeutil import utcnow

# One local backend worker, as specified by the demo architecture. Serialize human
# transitions and ladder assignment updates so stale forms cannot accept a new handoff.
assignment_lock = RLock()


def latest_assignment(s: Session, incident_id: int) -> Assignment | None:
    return s.exec(select(Assignment).where(Assignment.incident_id == incident_id).order_by(col(Assignment.id).desc())).first()


def assign(
    s: Session, incident: Incident, department: str, owner: str | None, *, by: str,
    reason: str, now: datetime | None = None, from_roster: bool = False,
    reset_ladder: bool = True, evidence: Sequence[str] = (),
) -> Assignment:
    """A changed department/person creates a new row; old acknowledgments never transfer."""
    previous = latest_assignment(s, incident.id)
    if previous and (previous.department, previous.owner) == (department, owner):
        return previous
    if previous:
        from app.engine.callback_jobs import cancel_pending

        cancel_pending(s, incident, 'assignment_changed')
    now = now or utcnow()
    assignment = Assignment(
        incident_id=incident.id, department=department, owner=owner, assigned_at=now,
        default_owner_at=now if from_roster else None,
        responsibility_profile=oncall.assignment_profile(department, owner, incident.area),
    )
    s.add(assignment)
    s.flush()
    clear_debt(s, incident.id, "department_assignment")
    refs = [f"assignment:{assignment.id}", *evidence]
    if previous:
        refs.append(f"assignment:{previous.id}")
    action = "default_owner" if from_roster else "reassigned" if previous else "assigned"
    log_event(s, incident.id, action, f"Assigned to {department}; individual: {owner or 'not assigned'}. {reason}", actor=by, evidence=refs)
    open_debt(s, incident.id, "no_owner", f"Assigned to {owner}; not accepted yet" if owner else "Department assigned; no individual has accepted")
    if reset_ladder:
        incident.status = "escalated" if incident.critical else "open"
        incident.ladder_step = 1
        incident.next_step_at = now + timedelta(seconds=TIMING.nudge_s)
    return assignment
