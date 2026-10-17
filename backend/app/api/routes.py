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
from app.models import Incident
from app.voice import simulator

router = APIRouter(prefix="/api")


def _incident_or_404(s: Session, incident_id: int) -> Incident:
    incident = s.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(404, f"incident {incident_id} not found")
    return incident


@router.get("/state", response_model=StateView)
def get_state(s: Session = Depends(get_session)):
    return views.state_view(s)


@router.get("/incidents/{incident_id}", response_model=IncidentDetailView)
def get_incident(incident_id: int, s: Session = Depends(get_session)):
    return views.incident_detail_view(s, _incident_or_404(s, incident_id))


@router.post("/incidents/{incident_id}/acknowledge", response_model=IncidentView)
def acknowledge_incident(incident_id: int, body: AcknowledgeIn, s: Session = Depends(get_session)):
    incident = _incident_or_404(s, incident_id)
    ladder.acknowledge(s, incident, body.by)
    return views.incident_view(s, incident)


@router.post("/incidents/{incident_id}/accept", response_model=IncidentView)
def accept_incident(incident_id: int, body: AcceptIn, s: Session = Depends(get_session)):
    incident = _incident_or_404(s, incident_id)
    ladder.accept(s, incident, body.owner)
    return views.incident_view(s, incident)


@router.post("/incidents/{incident_id}/close", response_model=IncidentView)
def close_incident(incident_id: int, body: CloseIn, s: Session = Depends(get_session)):
    incident = _incident_or_404(s, incident_id)
    ladder.close(s, incident, body.by, body.note)
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
    if not seeds.seed_exists(body.seed):
        raise HTTPException(404, f"seed {body.seed!r} not found")
    reset_db()
    twists.reset()
    seeds.load_seed(body.seed)
    s.expire_all()
    return views.state_view(s)
