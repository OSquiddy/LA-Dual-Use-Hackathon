"""B12: department-silence detector. One department alert replaces hundreds of ticket alerts."""
from collections import Counter
from datetime import timedelta

from sqlmodel import Session, select

from app.config import DEPT_SILENCE_MIN_ASSIGNED  # noqa: F401
from app.contracts import AlertView, DepartmentView
from app.models import Assignment
from app.timeutil import utcnow


def department_stats(s: Session) -> list[DepartmentView]:
    since = utcnow() - timedelta(hours=1)
    rows = s.exec(select(Assignment).where(Assignment.assigned_at >= since)).all()
    assigned = Counter(a.department for a in rows)
    accepted = Counter(a.department for a in rows if a.accepted_at)
    # TODO(B12): silent = assigned >= DEPT_SILENCE_MIN_ASSIGNED and accepted == 0, or twists.dept_silent
    return [
        DepartmentView(name=name, assigned_1h=assigned[name], accepted_1h=accepted[name], silent=False)
        for name in sorted(assigned)
    ]


def alerts(s: Session) -> list[AlertView]:
    """TODO(B12): one department_silent alert per silent department, e.g.
    "Street Services accepted 0 of 12 in the last hour", and suppress that department's nudges."""
    return []
