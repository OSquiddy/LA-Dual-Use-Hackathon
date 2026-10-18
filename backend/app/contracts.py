"""The seams between the three computers. SHARED FILE: message the team before changing it.

- ReportIn / CallbackOutcome: what PC-A (voice) hands to PC-B (engine).
- *View models: the REST shapes PC-C (dashboard) renders. frontend/src/types.ts mirrors them,
  and tests/test_contracts.py checks the frontend fixtures still match.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, StrictBool, field_validator

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
    callback_ok: bool = False  # True only for a clear yes; anything else means no outbound call
    callback_opt_out: bool = False
    transcript: str = ""
    created_at: datetime

    @field_validator('callback_ok', 'callback_opt_out', mode='before')
    @classmethod
    def explicit_boolean(cls, value):
        return value is True


class CallbackOutcome(BaseModel):
    incident_id: int
    call_id: str
    attempt_no: int
    outcome: Outcome | None = None
    danger: bool = False
    summary: str = ""  # e.g. "water at the curb and rising"
    transcript: str = ""
    request_key: str | None = None
    callback_opt_out: bool = False
    wrong_number: bool = False
    disconnection_reason: str | None = None


# --- Engine -> dashboard ---------------------------------------------------------------------

class DebtView(BaseModel):
    kind: str  # location | caller_unreachable | no_owner | no_update | consent_unknown
    label: str


class AssignmentView(BaseModel):
    department: str
    owner: str | None
    assigned_at: datetime
    accepted_at: datetime | None
    default_owner_at: datetime | None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    accepted_by: str | None = None
    id: int | None = None
    assigned_by: str | None = None
    change_reason: str | None = None


class IncidentView(BaseModel):
    id: int
    title: str
    hazard_type: str
    status: Status
    ladder_step: int  # 1 assigned · 2 nudge · 3 default owner · 4 callback · 5 supervisor (= critical)
    risk_score: int  # physical risk from evidence only; never moved by time or silence
    report_count: int
    department: str | None
    owner: str | None  # proposed (default on-call) or accepting owner; see `accepted`
    accepted: bool
    next_step_at: datetime | None
    debts: list[DebtView]
    why: str
    lat: float | None
    lng: float | None
    acknowledged: bool = False  # receipt only; never implies accepted
    critical: bool = False  # also listed in StateView.critical_alerts
    assignment: AssignmentView | None = None
    closed_at: datetime | None = None
    closed_by: str | None = None


class DepartmentView(BaseModel):
    name: str
    assigned_1h: int
    accepted_1h: int
    silent: bool


class AlertView(BaseModel):
    type: str  # department_silent | ...
    department: str | None = None
    text: str


class CriticalAlertView(BaseModel):
    """Pinned safety alert. Never capped by the top 10; stays until a human closes the case."""

    incident_id: int
    title: str
    reason: str
    quote: str = ""  # the resident's own words behind the alert, when there are any
    evidence: list[str] = []  # source refs, e.g. ["report:3", "callback:2"]
    since: datetime
    accepted: bool = False
    owner: str | None = None


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
    supervisor_queue: list[int]  # incident ids, highest risk first, capped at 10
    departments: list[DepartmentView]
    alerts: list[AlertView]
    critical_alerts: list[CriticalAlertView] = []  # uncapped, shown apart from the top 10


class ReportView(BaseModel):
    id: int
    call_id: str
    phone: str | None  # masked, e.g. "•••0103"
    location_text: str | None
    hazard_type: str
    danger_words: list[str]
    transcript: str
    created_at: datetime
    callback_ok: bool = False
    callback_opt_out: bool = False
    callback_eligible: bool = False


class EventView(BaseModel):
    type: str
    reason: str
    at: datetime
    actor: str = "engine"  # engine | resident | a named person
    evidence: list[str] = []  # source refs, e.g. ["report:3"]


class CallbackView(BaseModel):
    attempt_no: int
    outcome: Outcome | None  # None while the call is still ringing
    danger: bool
    summary: str
    called_at: datetime
    id: int | None = None
    state: str = 'unknown'
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    mode: str = 'legacy'
    transcript: str = ''  # only the reviewer-authorized evidence response populates this


class CallbackStatusView(BaseModel):
    eligible: bool = False
    reason: str = 'Callback eligibility has not been checked'
    scheduled_at: datetime | None = None
    call_mode: str = 'simulate'
    attempts_used: int = 0
    max_attempts: int = 2
    automatic_live_enabled: bool = False


class IncidentDetailView(IncidentView):
    reports: list[ReportView]
    events: list[EventView]
    callbacks: list[CallbackView]
    assignment_history: list[AssignmentView] = []
    callback_status: CallbackStatusView = Field(default_factory=CallbackStatusView)


class DepartmentAssignmentOption(BaseModel):
    department: str
    owners: list[str]


class AssignmentOptionsView(BaseModel):
    recommended_department: str
    area: str | None
    departments: list[DepartmentAssignmentOption]
    fictional_roster: bool = True


# --- Request bodies --------------------------------------------------------------------------

class AcceptIn(BaseModel):
    owner: str = Field(min_length=1, max_length=80)
    expected_assignment_id: int | None = Field(default=None, gt=0)


class AcknowledgeIn(BaseModel):
    by: str = Field(min_length=1, max_length=80)
    expected_assignment_id: int | None = Field(default=None, gt=0)


class ReassignIn(BaseModel):
    department: str = Field(min_length=1, max_length=80)
    owner: str | None = Field(default=None, min_length=1, max_length=80)
    by: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=240)
    expected_assignment_id: int | None = Field(default=None, gt=0)


class CloseIn(BaseModel):
    by: str = Field(min_length=1)  # a named human; the engine never closes a case
    note: str = ""


class SimulateCallbackIn(BaseModel):
    outcome: Outcome
    danger: bool = False


class RequestCallbackIn(BaseModel):
    by: str = Field(min_length=1, max_length=80)
    confirm_live: StrictBool = False


class CallbackOptOutIn(BaseModel):
    by: str = Field(min_length=1, max_length=80)
    reason: Literal['opt_out', 'wrong_number'] = 'opt_out'


class TwistIn(BaseModel):
    on: bool | None = None
    domain: str | None = None


class ResetIn(BaseModel):
    seed: str = "storm_night"
