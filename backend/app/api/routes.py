"""REST API for the dashboard (PC-C). Shapes are in app/contracts.py."""
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlmodel import Session, select

from app.contracts import (
    AcceptIn,
    AcknowledgeIn,
    AssignmentOptionsView,
    AssignmentHistoryPage,
    AssignmentHistoryEntry,
    CloseIn,
    CallbackOptOutIn,
    IncidentDetailView,
    IncidentView,
    ResetIn,
    ReassignIn,
    RequestCallbackIn,
    SimulateCallbackIn,
    StateView,
    TwistIn,
)
from app.db import get_session, reset_db
from app.config import HAZARD_DEPARTMENT, REVIEWER_API_KEY
from app.engine import callback_jobs, contact, ladder, oncall, seeds, twists, views
from app.engine.assignments import assign, assignment_lock, latest_assignment
from app.engine.ingest import ingest_report
from app.models import Assignment, Incident, Report
from app.voice import callbacks, simulator

router = APIRouter(prefix="/api")


def _incident_or_404(s: Session, incident_id: int) -> Incident:
    incident = s.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(404, f"incident {incident_id} not found")
    return incident


def _human_name(value: str) -> str:
    name = value.strip()
    if not name or len(name) > 80 or any(c in name for c in "\r\n"):
        raise HTTPException(422, "A named human is required")
    return name


@router.get("/state", response_model=StateView)
def get_state(s: Session = Depends(get_session)):
    return views.state_view(s)


@router.get('/assignment-history', response_model=AssignmentHistoryPage)
def assignment_history(before_id: int | None = Query(default=None, gt=0), limit: int = Query(default=30, ge=1, le=100), s: Session = Depends(get_session)):
    query = select(Assignment).order_by(Assignment.id.desc()).limit(limit + 1)
    if before_id is not None:
        query = query.where(Assignment.id < before_id)
    rows = s.exec(query).all()
    entries = []
    for assignment in rows[:limit]:
        incident = s.get(Incident, assignment.incident_id)
        if incident:
            entries.append(AssignmentHistoryEntry(incident_id=incident.id, title=views.incident_view(s, incident).title,
                status=incident.status, assignment=views.assignment_view(s, assignment)))
    return AssignmentHistoryPage(entries=entries, next_before_id=rows[limit - 1].id if len(rows) > limit else None)


@router.get("/incidents/{incident_id}", response_model=IncidentDetailView)
def get_incident(incident_id: int, s: Session = Depends(get_session)):
    return views.incident_detail_view(s, _incident_or_404(s, incident_id))


def require_reviewer(authorization: str | None = Header(default=None)) -> None:
    if not REVIEWER_API_KEY.strip():
        raise HTTPException(503, "Reviewer access is not configured")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token.encode(), REVIEWER_API_KEY.encode()):
        raise HTTPException(401, "Reviewer authorization required", headers={"WWW-Authenticate": "Bearer"})


@router.get("/incidents/{incident_id}/evidence", response_model=IncidentDetailView, dependencies=[Depends(require_reviewer)])
def get_incident_evidence(incident_id: int, response: Response, s: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    return views.incident_detail_view(s, _incident_or_404(s, incident_id), include_evidence=True)


@router.post("/incidents/{incident_id}/acknowledge", response_model=IncidentView, dependencies=[Depends(require_reviewer)])
def acknowledge_incident(incident_id: int, body: AcknowledgeIn, s: Session = Depends(get_session)):
    with assignment_lock:
        incident = _incident_or_404(s, incident_id)
        _check_assignment(s, incident, body.expected_assignment_id)
        ladder.acknowledge(s, incident, _human_name(body.by))
        return views.incident_view(s, incident)


@router.post("/incidents/{incident_id}/accept", response_model=IncidentView, dependencies=[Depends(require_reviewer)])
def accept_incident(incident_id: int, body: AcceptIn, s: Session = Depends(get_session)):
    with assignment_lock:
        incident = _incident_or_404(s, incident_id)
        _check_assignment(s, incident, body.expected_assignment_id)
        ladder.accept(s, incident, _human_name(body.owner))
        return views.incident_view(s, incident)


def _check_assignment(s: Session, incident: Incident, expected: int | None) -> None:
    current = latest_assignment(s, incident.id)
    if expected is not None and (current is None or current.id != expected):
        raise HTTPException(409, "Assignment changed; refresh the incident before recording this action")
    if current is None:
        raise HTTPException(409, "Assign a responsible department before recording acknowledgment or acceptance")


@router.get("/incidents/{incident_id}/assignment-options", response_model=AssignmentOptionsView)
def assignment_options(incident_id: int, s: Session = Depends(get_session)):
    incident = _incident_or_404(s, incident_id)
    return AssignmentOptionsView(
        recommended_department=HAZARD_DEPARTMENT.get(incident.hazard_type, HAZARD_DEPARTMENT["other"]),
        area=incident.area, departments=oncall.assignment_options(incident.area),
    )


@router.post("/incidents/{incident_id}/reassign", response_model=IncidentDetailView, dependencies=[Depends(require_reviewer)])
def reassign_incident(incident_id: int, body: ReassignIn, s: Session = Depends(get_session)):
    by = _human_name(body.by)
    reason = body.reason.strip()
    if not reason or any(c in reason for c in "\r\n"):
        raise HTTPException(422, "A concise reason for reassignment is required")
    with assignment_lock:
        incident = _incident_or_404(s, incident_id)
        if incident.status == "closed":
            raise HTTPException(409, "Closed incidents cannot be reassigned")
        current = latest_assignment(s, incident.id)
        if body.expected_assignment_id is not None and (not current or current.id != body.expected_assignment_id):
            raise HTTPException(409, "Assignment changed; refresh before reassigning")
        options = {option['department']: option['owners'] for option in oncall.assignment_options(incident.area)}
        if body.department not in options:
            raise HTTPException(422, "Select a configured department")
        if body.owner is not None and body.owner not in options[body.department]:
            raise HTTPException(422, "Select an individual from this department's configured area roster")
        assign(s, incident, body.department, body.owner, by=by, reason=reason)
        s.commit()
        return views.incident_detail_view(s, incident)


@router.post("/incidents/{incident_id}/close", response_model=IncidentView, dependencies=[Depends(require_reviewer)])
def close_incident(incident_id: int, body: CloseIn, s: Session = Depends(get_session)):
    with assignment_lock:
        incident = _incident_or_404(s, incident_id)
        ladder.close(s, incident, _human_name(body.by), body.note)
        return views.incident_view(s, incident)


@router.post('/incidents/{incident_id}/request-callback', response_model=IncidentDetailView, dependencies=[Depends(require_reviewer)])
def request_callback(incident_id: int, body: RequestCallbackIn, s: Session = Depends(get_session)):
    with assignment_lock:
        incident = _incident_or_404(s, incident_id)
        try:
            job = callback_jobs.enqueue(s, incident, by=_human_name(body.by), confirm_live=body.confirm_live)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None
        s.commit()
        callback_jobs.dispatch_attempt(job.id)
        s.expire_all()
        return views.incident_detail_view(s, _incident_or_404(s, incident_id))


@router.post('/reports/{report_id}/callback-opt-out', response_model=IncidentDetailView, dependencies=[Depends(require_reviewer)])
def callback_opt_out(report_id: int, body: CallbackOptOutIn, s: Session = Depends(get_session)):
    with assignment_lock:
        report = s.get(Report, report_id)
        if report is None:
            raise HTTPException(404, 'Report not found')
        contact.block(s, report, body.reason, _human_name(body.by))
        s.commit()
        return views.incident_detail_view(s, _incident_or_404(s, report.incident_id))


@router.post("/incidents/{incident_id}/simulate-callback", response_model=IncidentDetailView, dependencies=[Depends(require_reviewer)])
def simulate_callback(incident_id: int, body: SimulateCallbackIn, s: Session = Depends(get_session)):
    if callbacks.CALL_MODE != 'simulate':
        raise HTTPException(409, 'Synthetic outcomes are available only in simulation mode')
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
