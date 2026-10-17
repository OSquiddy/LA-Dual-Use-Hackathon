"""B4: link related-but-different reports into one emerging incident.

Linking never merges or deletes reports: each one stays its own row, and the "linked" event says why.
"""
from dataclasses import dataclass
from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from sqlmodel import Session, col, func, select

from app.config import HAZARD_GROUPS, LINK_RADIUS_M, LINK_WINDOW_MIN
from app.engine.geocode import streets_in
from app.models import Incident, Report


@dataclass(frozen=True)
class Link:
    incident: Incident
    reason: str
    distance_m: float | None  # None when linked by street name only


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in metres."""
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(a))


def hazard_group(hazard_type: str) -> str | None:
    return next((name for name, members in HAZARD_GROUPS.items() if hazard_type in members), None)


def compatible(a: str, b: str) -> bool:
    group = hazard_group(a)
    return a == b or (group is not None and group == hazard_group(b))


def find_incident(s: Session, report: Report) -> Link | None:
    """The open incident this report belongs to, or None to start a new one.

    Same incident = compatible hazard group, within LINK_WINDOW_MIN of the incident's latest report,
    and within LINK_RADIUS_M of the incident's anchor (its first located report, so a chain of reports
    can't drift down the street). Without an exact spot on either side, fall back to the same named
    street. The nearest candidate wins.
    """
    window = timedelta(minutes=LINK_WINDOW_MIN)
    best: Link | None = None
    for incident in s.exec(select(Incident).where(col(Incident.status) != "closed")):
        if incident.id == report.incident_id or not compatible(report.hazard_type, incident.hazard_type):
            continue
        latest = s.exec(select(func.max(Report.created_at)).where(Report.incident_id == incident.id)).one()
        if latest is None or abs(report.created_at - latest) > window:
            continue
        minutes = round(abs(report.created_at - latest).total_seconds() / 60)
        group = hazard_group(report.hazard_type) or report.hazard_type

        if report.lat is not None and incident.lat is not None:
            d = distance_m(report.lat, report.lng, incident.lat, incident.lng)
            if d > LINK_RADIUS_M:
                continue
            reason = f"{d:.0f} m from the first report, {minutes} min after the last, same {group} hazard group"
            candidate = Link(incident, reason, d)
        else:
            shared = streets_in(report.location_text) & _incident_streets(s, incident)
            if not shared:
                continue
            reason = f"same street ({', '.join(sorted(shared)).title()}), no exact spot, {minutes} min after the last"
            candidate = Link(incident, reason, None)

        if best is None or _rank(candidate) < _rank(best):
            best = candidate
    return best


def _rank(link: Link) -> float:
    return link.distance_m if link.distance_m is not None else LINK_RADIUS_M + 1


def _incident_streets(s: Session, incident: Incident) -> set[str]:
    texts = s.exec(select(Report.location_text).where(Report.incident_id == incident.id)).all()
    return set().union(*(streets_in(t) for t in texts))
