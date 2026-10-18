"""B12: department-silence detector. One department alert replaces hundreds of ticket alerts."""
from collections import Counter
from datetime import timedelta

from sqlmodel import Session, select

from app.config import DEPT_SILENCE_MIN_ASSIGNED
from app.engine import twists
from app.contracts import AlertView, DepartmentView
from app.models import Assignment
from app.timeutil import utcnow


def department_stats(s: Session) -> list[DepartmentView]:
    since = utcnow() - timedelta(hours=1)
    rows = s.exec(select(Assignment).where(Assignment.assigned_at >= since)).all()
    assigned = Counter(a.department for a in rows)
    accepted = Counter(a.department for a in rows if a.accepted_at)
    return [
        DepartmentView(
            name=name, assigned_1h=assigned[name], accepted_1h=accepted[name],
            silent=(assigned[name] >= DEPT_SILENCE_MIN_ASSIGNED and accepted[name] == 0)
            or (twists.current().dept_silent and name == "Street Services"),
        )
        for name in sorted(assigned)
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
