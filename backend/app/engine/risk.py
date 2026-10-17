"""B5: physical-risk score. It moves only on evidence; time and silence never change it."""
from sqlmodel import Session

from app.config import HAZARD_BASE_RISK
from app.models import Incident


def score(s: Session, incident: Incident) -> int:
    """TODO(B5) v1 formula from the build plan:

    hazard base
    + 25 if a linked report has a supported danger phrase or a person at risk
    + 5 per additional independently sourced report (max +25)
    + 30 for explicit worsening; "same" adds nothing
    - only verified improvement (new evidence) may lower it, and never closes the case

    NOT risk points: no_answer, missing callback consent, an unaccepted handoff. Those are
    contact/ownership uncertainty, tracked as debts and reviewed separately.
    """
    return HAZARD_BASE_RISK.get(incident.hazard_type, HAZARD_BASE_RISK["other"])
