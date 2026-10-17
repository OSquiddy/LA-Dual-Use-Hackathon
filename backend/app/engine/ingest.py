"""Contract function: ingest_report(ReportIn) -> report id. Called by A's intake webhook and the seed loader."""
from datetime import timedelta

from sqlmodel import Session

from app.config import HAZARD_DEPARTMENT, HAZARD_LABELS, TIMING
from app.contracts import ReportIn
from app.db import engine
from app.engine import linker, risk
from app.engine.audit import log_event, open_debt
from app.engine.geocode import geocode
from app.models import Assignment, Incident, Report
from app.timeutil import to_db, utcnow


def ingest_report(r: ReportIn) -> int:
    with Session(engine) as s:
        report = Report(**r.model_dump(), incident_id=None)
        report.created_at = to_db(r.created_at)
        hit = None
        if report.lat is None or report.lng is None:
            hit = geocode(report.location_text)
            if hit:
                report.lat, report.lng = hit.lat, hit.lng
        s.add(report)

        incident = linker.find_incident(s, report)
        if incident is None:
            incident = _new_incident(s, report, hit.name if hit else None, hit.area if hit else None)
        else:
            log_event(s, incident.id, "linked", f"New report linked: {report.location_text or 'unknown location'}")
        report.incident_id = incident.id

        if report.lat is None:
            open_debt(s, incident.id, "location", "Exact location unclear")
        incident.risk_score = max(incident.risk_score, risk.score(s, incident))
        s.commit()
        return report.id


def _new_incident(s: Session, report: Report, place: str | None, area: str | None) -> Incident:
    label = HAZARD_LABELS.get(report.hazard_type, HAZARD_LABELS["other"])
    incident = Incident(
        title=f"{label} — {place or report.location_text or 'location unknown'}",
        area=area,
        hazard_type=report.hazard_type,
        lat=report.lat,
        lng=report.lng,
        created_at=report.created_at,
        next_step_at=utcnow() + timedelta(seconds=TIMING.nudge_s),
    )
    s.add(incident)
    s.flush()

    department = HAZARD_DEPARTMENT.get(report.hazard_type, HAZARD_DEPARTMENT["other"])
    s.add(Assignment(incident_id=incident.id, department=department))
    open_debt(s, incident.id, "no_owner", "No one has accepted")
    log_event(s, incident.id, "assigned", f"Sent to {department}; waiting for Accept")
    return incident
