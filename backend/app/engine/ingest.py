"""Contract function: ingest_report(ReportIn) -> report id. Called by A's intake webhook and the seed loader."""
from datetime import timedelta

from sqlmodel import Session, col, func, select

from app.config import EMERGING_HAZARD, HAZARD_DEPARTMENT, HAZARD_LABELS, TIMING
from app.contracts import ReportIn
from app.db import engine
from app.engine import critical, ladder, linker, risk
from app.engine.audit import log_event, open_debt
from app.engine.geocode import GeoHit, geocode
from app.models import Assignment, Incident, Report
from app.timeutil import to_db, utcnow


def ingest_report(r: ReportIn) -> int:
    """Store the report as its own row, then link it to an incident or start one. Idempotent per call_id."""
    with Session(engine) as s:
        existing = s.exec(select(Report).where(Report.call_id == r.call_id)).first()
        if existing:  # Retell may deliver the same webhook twice
            return existing.id

        report = Report(**r.model_dump())
        report.created_at = to_db(r.created_at)
        hit = None
        if report.lat is None or report.lng is None:
            # A partial coordinate pair is unresolved, not a usable map position.
            report.lat, report.lng = None, None
            hit = geocode(report.location_text)
            if hit:
                report.lat, report.lng = hit.lat, hit.lng
        s.add(report)
        s.flush()

        link = linker.find_incident(s, report)
        if link is None:
            incident = _new_incident(s, report, hit)
        else:
            incident = link.incident
            report.incident_id = incident.id
            s.flush()
            _absorb(s, incident, report, hit, link)

        _refresh_location_debt(s, incident)
        ladder.refresh_consent_debt(s, incident)
        incident.risk_score = risk.score(s, incident)
        if report.anyone_in_danger:
            critical.flag(
                s, incident, "evidence", "Caller reports someone in danger",
                quote=report.transcript, evidence=[f"report:{report.id}"], actor="resident",
            )
        s.commit()
        return report.id


def _new_incident(s: Session, report: Report, hit: GeoHit | None) -> Incident:
    incident = Incident(
        title="",
        place=hit.name if hit else None,
        area=hit.area if hit else None,
        hazard_type=report.hazard_type,
        lat=report.lat,
        lng=report.lng,
        created_at=report.created_at,
        next_step_at=utcnow() + timedelta(seconds=TIMING.nudge_s),
    )
    incident.title = _title(incident, report.location_text)
    s.add(incident)
    s.flush()
    report.incident_id = incident.id

    department = HAZARD_DEPARTMENT.get(report.hazard_type, HAZARD_DEPARTMENT["other"])
    s.add(Assignment(incident_id=incident.id, department=department))
    open_debt(s, incident.id, "no_owner", "No one has accepted")
    log_event(s, incident.id, "assigned", f"Sent to {department}; waiting for Accept", evidence=[f"report:{report.id}"])
    return incident


def _absorb(s: Session, incident: Incident, report: Report, hit: GeoHit | None, link: linker.Link) -> None:
    hazards = set(s.exec(select(Report.hazard_type).where(Report.incident_id == incident.id)).all())
    group = linker.hazard_group(report.hazard_type)
    if group in EMERGING_HAZARD and len(hazards) >= 2:
        incident.hazard_type = EMERGING_HAZARD[group]
    if incident.lat is None and report.lat is not None:
        incident.lat, incident.lng = report.lat, report.lng
        if hit:
            incident.place, incident.area = hit.name, hit.area
    incident.title = _title(incident, incident.title.split(" — ", 1)[-1])
    where = report.location_text or "unknown location"
    log_event(s, incident.id, "linked", f"Linked report #{report.id} ({where}): {link.reason}", evidence=[f"report:{report.id}"])


def _refresh_location_debt(s: Session, incident: Incident) -> None:
    unclear = s.exec(
        select(func.count()).select_from(Report).where(Report.incident_id == incident.id, col(Report.lat).is_(None))
    ).one()
    if unclear:
        noun = "report" if unclear == 1 else "reports"
        open_debt(s, incident.id, "location", f"Exact location unclear ({unclear} {noun})")


def _title(incident: Incident, fallback_location: str | None) -> str:
    label = HAZARD_LABELS.get(incident.hazard_type, HAZARD_LABELS["other"])
    return f"{label} — {incident.place or fallback_location or 'location unknown'}"
