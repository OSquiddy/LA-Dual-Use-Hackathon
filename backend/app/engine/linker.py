"""B4: link related-but-different reports into one emerging incident."""
from math import asin, cos, radians, sin, sqrt

from sqlmodel import Session

from app.config import HAZARD_GROUPS, LINK_RADIUS_M, LINK_WINDOW_MIN  # noqa: F401
from app.models import Incident, Report


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in metres."""
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(a))


def hazard_group(hazard_type: str) -> str | None:
    return next((name for name, members in HAZARD_GROUPS.items() if hazard_type in members), None)


def find_incident(s: Session, report: Report) -> Incident | None:
    """Return the open incident this report belongs to, or None to start a new one.

    TODO(B4): open incidents within LINK_RADIUS_M and LINK_WINDOW_MIN whose hazard is in the same
    HAZARD_GROUPS group; if the report has no lat/lng, fall back to matching the street name.
    Until then every report starts its own incident.
    """
    return None
