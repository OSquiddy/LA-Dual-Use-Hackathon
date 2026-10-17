"""B10: the supervisor's ranked, capped queue."""
from sqlmodel import Session, col, select

from app.config import SUPERVISOR_QUEUE_SIZE
from app.models import Incident


def queue(s: Session) -> list[int]:
    """TODO(B10): only step-5 / escalated or worsening incidents. For now: every unaccepted open incident."""
    rows = s.exec(
        select(Incident.id)
        .where(col(Incident.status).in_(["open", "escalated"]))
        .order_by(col(Incident.risk_score).desc(), col(Incident.created_at))
        .limit(SUPERVISOR_QUEUE_SIZE)
    )
    return list(rows)
