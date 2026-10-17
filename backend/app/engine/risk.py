"""B5: physical-risk score. It moves only on evidence; time and silence never change it.

hazard base (highest among the linked reports)
+ 25 if a linked report has a supported danger phrase or a person at risk, or a callback reports danger
+ 5 per additional independent caller (distinct phone numbers, max +25)
+ 30 while the latest trend from a resident is "worse"; "same" adds nothing
- 10 when the latest trend is "better" (new evidence); it never closes the case

NOT risk points: no_answer, missing callback consent, an unaccepted handoff. Those are
contact/ownership uncertainty, tracked as debts and reviewed separately.
"""
import re
from dataclasses import dataclass

from sqlmodel import Session, col, select

from app.config import HAZARD_BASE_RISK, HAZARD_LABELS
from app.models import Callback, Incident, Report


@dataclass(frozen=True)
class Factor:
    points: int
    label: str
    evidence: tuple[str, ...] = ()


def score(s: Session, incident: Incident) -> int:
    return max(0, min(100, sum(f.points for f in breakdown(s, incident))))


def breakdown(s: Session, incident: Incident) -> list[Factor]:
    reports = s.exec(select(Report).where(Report.incident_id == incident.id).order_by(col(Report.created_at))).all()
    answered = s.exec(
        select(Callback)
        .where(Callback.incident_id == incident.id, col(Callback.outcome).in_(["worse", "same", "better"]))
        .order_by(col(Callback.id))
    ).all()

    hazard = max({incident.hazard_type, *(r.hazard_type for r in reports)}, key=_base)
    factors = [Factor(_base(hazard), f"{HAZARD_LABELS.get(hazard, hazard)} base")]

    danger_refs = [f"report:{r.id}" for r in reports if supported_danger(r)]
    danger_refs += [f"callback:{c.id}" for c in answered if c.danger]
    if danger_refs:
        factors.append(Factor(25, "Reported danger", tuple(danger_refs)))

    callers = {r.phone or f"report:{r.id}" for r in reports}
    if len(callers) > 1:
        factors.append(Factor(min(5 * (len(callers) - 1), 25), f"{len(callers)} independent callers"))

    trend = None
    for c in answered:
        if c.outcome in ("worse", "better"):
            trend = c
    if trend and trend.outcome == "worse":
        factors.append(Factor(30, "Resident says worse", (f"callback:{trend.id}",)))
    elif trend and trend.outcome == "better":
        factors.append(Factor(-10, "Resident says better", (f"callback:{trend.id}",)))
    return factors


def supported_danger(report: Report) -> list[str]:
    """Danger phrases backed by the caller's own words: every word of the phrase is in the transcript.

    Guards against an extracted "trapped" when the caller never said it. Retell's anyone_in_danger
    flag counts on its own: we over-flag a person at risk on purpose.
    """
    said = set(_words(report.transcript))
    phrases = [p for p in report.danger_words if _words(p) and set(_words(p)) <= said]
    if report.anyone_in_danger:
        phrases.append("someone in danger")
    return phrases


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _base(hazard: str) -> int:
    return HAZARD_BASE_RISK.get(hazard, HAZARD_BASE_RISK["other"])
