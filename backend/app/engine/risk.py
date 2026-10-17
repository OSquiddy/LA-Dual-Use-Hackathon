"""B5: risk score. It climbs on evidence of danger and never falls because of time or silence."""
from sqlmodel import Session

from app.config import HAZARD_BASE_RISK
from app.models import Incident


def score(s: Session, incident: Incident) -> int:
    """TODO(B5) v1 formula from the build plan:

    hazard base
    + 25 if any linked report has danger words
    + 5 per extra linked report (max +25)
    + 30 per "worse" callback, + 10 per "same", - 10 per "better"
    + 15 per no_answer
    + 10 while a caller_unreachable debt is open
    """
    return HAZARD_BASE_RISK.get(incident.hazard_type, HAZARD_BASE_RISK["other"])
