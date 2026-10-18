"""REST API for the dashboard (PC-C). Shapes are in app/contracts.py."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.contracts import (
    AcceptIn,
    AcknowledgeIn,
    CloseIn,
    IncidentDetailView,
    IncidentView,
    ResetIn,
    SimulateCallbackIn,
    StateView,
    TwistIn,
)
from app.db import get_session, reset_db
from app.engine import ladder, seeds, twists, views
from app.engine.ingest import ingest_report
from app.models import Incident
from app.voice import simulator

router = APIRouter(prefix="/api")


def _incident_or_404(s: Session, incident_id: int) -> Incident:
    incident = s.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(404, f"incident {incident_id} not found")
    return incident


def _human_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise HTTPException(422, "A named human is required")
    return name


@router.get("/state", response_model=StateView)
def get_state(s: Session = Depends(get_session)):
    return views.state_view(s)


@router.get("/incidents/{incident_id}", response_model=IncidentDetailView)
def get_incident(incident_id: int, s: Session = Depends(get_session)):
    return views.incident_detail_view(s, _incident_or_404(s, incident_id))


@router.post("/incidents/{incident_id}/acknowledge", response_model=IncidentView)
def acknowledge_incident(incident_id: int, body: AcknowledgeIn, s: Session = Depends(get_session)):
    incident = _incident_or_404(s, incident_id)
    ladder.acknowledge(s, incident, _human_name(body.by))
    return views.incident_view(s, incident)


@router.post("/incidents/{incident_id}/accept", response_model=IncidentView)
def accept_incident(incident_id: int, body: AcceptIn, s: Session = Depends(get_session)):
    incident = _incident_or_404(s, incident_id)
    ladder.accept(s, incident, _human_name(body.owner))
    return views.incident_view(s, incident)


@router.post("/incidents/{incident_id}/close", response_model=IncidentView)
def close_incident(incident_id: int, body: CloseIn, s: Session = Depends(get_session)):
    incident = _incident_or_404(s, incident_id)
    ladder.close(s, incident, _human_name(body.by), body.note)
    return views.incident_view(s, incident)


@router.post("/incidents/{incident_id}/simulate-callback", response_model=IncidentDetailView)
def simulate_callback(incident_id: int, body: SimulateCallbackIn, s: Session = Depends(get_session)):
    _incident_or_404(s, incident_id)
    simulator.simulate_now(incident_id, body.outcome, body.danger)
    s.expire_all()
    return views.incident_detail_view(s, _incident_or_404(s, incident_id))


@router.post("/twists/{name}", response_model=StateView)
def set_twist(name: str, body: TwistIn, s: Session = Depends(get_session)):
    try:
        twists.set_twist(name, body)
    except KeyError:
        raise HTTPException(404, f"unknown twist {name!r}")
    return views.state_view(s)


@router.post("/demo/reset", response_model=StateView)
def reset_demo(body: ResetIn, s: Session = Depends(get_session)):
    try:
        domain, reports = seeds.prepare_seed(body.seed)
    except (OSError, ValueError, TypeError, OverflowError):
        raise HTTPException(404, "Unknown or invalid report scenario") from None
    # All rows have been validated and materialized before touching current data.
    reset_db()
    twists.reset(domain=domain)
    for report in reports:
        ingest_report(report)
    s.expire_all()
    return views.state_view(s)
