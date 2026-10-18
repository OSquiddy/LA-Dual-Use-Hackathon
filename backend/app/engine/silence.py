"""B12: department-silence detector. One department alert replaces hundreds of ticket alerts."""
from collections import Counter
from datetime import timedelta

from sqlmodel import Session, select

from app.config import DEPT_SILENCE_MIN_ASSIGNED, HAZARD_DEPARTMENT
from app.engine import oncall, twists
from app.contracts import AlertView, DepartmentView
from app.models import Assignment, Incident
from app.timeutil import utcnow


def department_stats(s: Session) -> list[DepartmentView]:
    since = utcnow() - timedelta(hours=1)
    rows = s.exec(select(Assignment).where(Assignment.assigned_at >= since)).all()
    # Reassignments retain history rows. Count incidents per department, not snapshots.
    assigned = Counter(department for _, department in {(a.incident_id, a.department) for a in rows})
    accepted = Counter(department for _, department in {(a.incident_id, a.department) for a in rows if a.accepted_at})
    active, awaiting = Counter(), Counter()
    for incident in s.exec(select(Incident).where(Incident.status != 'closed')):
        current = s.exec(select(Assignment).where(Assignment.incident_id == incident.id).order_by(Assignment.id.desc())).first()
        if current:
            active[current.department] += 1
            if not current.accepted_at:
                awaiting[current.department] += 1
    return [
        DepartmentView(
            name=name, assigned_1h=assigned[name], accepted_1h=accepted[name],
            silent=(assigned[name] >= DEPT_SILENCE_MIN_ASSIGNED and accepted[name] == 0)
            or (twists.current().dept_silent and name == HAZARD_DEPARTMENT['flood']),
            display_name=oncall.department_info(name).get('display_name', name),
            operational_unit=oncall.department_info(name).get('unit'), active_incidents=active[name],
            awaiting_acceptance=awaiting[name], staff=oncall.department_staff(name),
        )
        for name in sorted(set(assigned) | set(active) | set(oncall.directory()))
    ]


def alerts(s: Session) -> list[AlertView]:
    """One operational alert per department; critical incident alerts remain independent."""
    return [
        AlertView(
            type="department_silent", department=d.name,
            text=f"{d.name} accepted {d.accepted_1h} of {d.assigned_1h} in the last hour",
        )
        for d in department_stats(s) if d.silent
    ]
