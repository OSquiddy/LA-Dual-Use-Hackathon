"""Physical danger is based on evidence, never silence or ownership uncertainty."""
import re

from sqlmodel import Session, select

from app.config import DANGER_WORDS, HAZARD_BASE_RISK
from app.models import Callback, Incident, Report


def supported_danger(report: Report) -> bool:
    if report.anyone_in_danger:
        return True
    transcript = report.transcript.lower()
    return any(
        phrase.lower() in DANGER_WORDS
        and re.search(rf"\b{re.escape(phrase.lower())}\b", transcript)
        and not re.search(rf"\b(?:no|not|never)\s+(?:\w+\s+){{0,2}}{re.escape(phrase.lower())}\b", transcript)
        for phrase in report.danger_words
    )


def score(s: Session, incident: Incident) -> int:
    reports = s.exec(select(Report).where(Report.incident_id == incident.id)).all()
    callbacks = s.exec(select(Callback).where(Callback.incident_id == incident.id)).all()
    base = max((HAZARD_BASE_RISK.get(r.hazard_type, 10) for r in reports), default=HAZARD_BASE_RISK.get(incident.hazard_type, 10))
    # The same caller repeating a report is not another independent witness.
    sources = {r.phone or r.call_id for r in reports}
    danger = any(supported_danger(r) for r in reports) or any(c.danger for c in callbacks)
    worsening = sum(c.outcome == "worse" for c in callbacks)
    return base + (25 if danger else 0) + min(25, 5 * max(0, len(sources) - 1)) + 30 * worsening
