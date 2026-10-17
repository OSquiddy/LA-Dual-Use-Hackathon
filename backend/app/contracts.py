"""The seams between the three computers. SHARED FILE: message the team before changing it.

- ReportIn / CallbackOutcome: what PC-A (voice) hands to PC-B (engine).
- *View models: the REST shapes PC-C (dashboard) renders. frontend/src/types.ts mirrors them,
  and tests/test_contracts.py checks the frontend fixtures still match.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Outcome = Literal["worse", "same", "better", "no_answer"]
Status = Literal["open", "accepted", "escalated", "closed"]


# --- Voice -> engine -------------------------------------------------------------------------

class ReportIn(BaseModel):
    source: Literal["retell", "seed"]
    call_id: str
    phone: str | None = None
    location_text: str | None = None
    lat: float | None = None  # engine geocodes from the gazetteer if None
    lng: float | None = None
    hazard_type: str  # one of config.HAZARD_TYPES
    danger_words: list[str] = []
    anyone_in_danger: bool = False
    transcript: str = ""
    created_at: datetime


class CallbackOutcome(BaseModel):
    incident_id: int
    call_id: str
    attempt_no: int
    outcome: Outcome
    danger: bool = False
    summary: str = ""  # e.g. "water at the curb and rising"
    transcript: str = ""


# --- Engine -> dashboard ---------------------------------------------------------------------

class DebtView(BaseModel):
    kind: str  # location | caller_unreachable | no_owner | no_update
    label: str


class IncidentView(BaseModel):
    id: int
    title: str
    hazard_type: str
    status: Status
    ladder_step: int  # 1 assigned · 2 nudge · 3 default owner · 4 callback · 5 supervisor
    risk_score: int
    report_count: int
    department: str | None
    owner: str | None
    accepted: bool
    next_step_at: datetime | None
    debts: list[DebtView]
    why: str
    lat: float | None
    lng: float | None


class DepartmentView(BaseModel):
    name: str
    assigned_1h: int
    accepted_1h: int
    silent: bool


class AlertView(BaseModel):
    type: str  # department_silent | ...
    department: str | None = None
    text: str


class TwistsView(BaseModel):
    dept_silent: bool = False
    surge: bool = False
    phones_down: bool = False
    domain: str = "storm"


class StateView(BaseModel):
    now: datetime
    timing_profile: str
    twists: TwistsView
    incidents: list[IncidentView]
    supervisor_queue: list[int]  # incident ids, highest risk first
    departments: list[DepartmentView]
    alerts: list[AlertView]


class ReportView(BaseModel):
    id: int
    call_id: str
    phone: str | None
    location_text: str | None
    hazard_type: str
    danger_words: list[str]
    transcript: str
    created_at: datetime


class EventView(BaseModel):
    type: str
    reason: str
    at: datetime


class CallbackView(BaseModel):
    attempt_no: int
    outcome: Outcome | None  # None while the call is still ringing
    danger: bool
    summary: str
    called_at: datetime


class AssignmentView(BaseModel):
    department: str
    owner: str | None
    assigned_at: datetime
    accepted_at: datetime | None
    default_owner_at: datetime | None


class IncidentDetailView(IncidentView):
    reports: list[ReportView]
    events: list[EventView]
    callbacks: list[CallbackView]
    assignment: AssignmentView | None


# --- Request bodies --------------------------------------------------------------------------

class AcceptIn(BaseModel):
    owner: str = Field(min_length=1)


class CloseIn(BaseModel):
    by: str = Field(min_length=1)  # a named human; the engine never closes a case
    note: str = ""


class SimulateCallbackIn(BaseModel):
    outcome: Outcome
    danger: bool = False


class TwistIn(BaseModel):
    on: bool | None = None
    domain: str | None = None


class ResetIn(BaseModel):
    seed: str = "storm_night"
