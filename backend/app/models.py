"""Database tables. SHARED FILE: B edits it; message the team before changing a field.

Reports point at their incident (instead of incidents holding report_ids) so linking is one update,
and every original report stays its own row after linking.
"""
from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.timeutil import utcnow


class Incident(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    place: str | None = None  # gazetteer name of the first located report
    area: str | None = None
    hazard_type: str
    lat: float | None = None
    lng: float | None = None
    risk_score: int = 0  # physical risk from evidence only
    status: str = "open"  # open | accepted | escalated | closed
    ladder_step: int = 1  # 1 assigned · 2 nudge · 3 default owner · 4 follow-up
    next_step_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    closed_at: datetime | None = None
    closed_by: str | None = None
    # Critical alert (supervisor review). Stays visible until a human closes the case.
    critical: bool = False
    critical_kind: str | None = None  # evidence (danger / worse) | uncertainty (high risk, no contact)
    critical_reason: str | None = None
    critical_quote: str = ""
    critical_evidence: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    critical_since: datetime | None = None


class Report(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: int | None = Field(default=None, foreign_key="incident.id", index=True)
    source: str
    call_id: str = Field(index=True, unique=True)
    phone: str | None = None
    location_text: str | None = None
    lat: float | None = None
    lng: float | None = None
    hazard_type: str
    danger_words: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    anyone_in_danger: bool = False
    callback_ok: bool = False
    callback_opt_out: bool = False
    transcript: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Debt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: int = Field(foreign_key="incident.id", index=True)
    kind: str  # location | caller_unreachable | no_owner | no_update | consent_unknown
    label: str
    opened_at: datetime = Field(default_factory=utcnow)
    cleared_at: datetime | None = None


class Assignment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: int = Field(foreign_key="incident.id", index=True)
    department: str
    owner: str | None = None  # proposed default owner until someone accepts
    assigned_at: datetime = Field(default_factory=utcnow)
    acknowledged_at: datetime | None = None  # receipt only
    acknowledged_by: str | None = None
    accepted_at: datetime | None = None
    accepted_by: str | None = None
    default_owner_at: datetime | None = None
    responsibility_profile: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))


class Callback(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: int = Field(foreign_key="incident.id", index=True)
    report_id: int | None = Field(default=None, foreign_key="report.id")  # the consenting report
    call_id: str = Field(index=True, unique=True)
    phone: str | None = None
    attempt_no: int
    outcome: str | None = None  # worse | same | better | no_answer; None while ringing
    danger: bool = False
    summary: str = ""
    called_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    state: str = "unknown"  # scheduled | dispatching | calling | completed | failed | cancelled | unknown
    scheduled_at: datetime | None = None
    dispatch_started_at: datetime | None = None
    result_due_at: datetime | None = None  # durable simulation completion deadline
    request_key: str | None = Field(default=None, index=True, unique=True)
    mode: str = "legacy"  # historical rows are never redispatched
    live_authorized: bool = False
    automatic: bool = True  # manual one-call confirmation never enables queued automatic calls
    error_code: str | None = None  # finite codes, never raw provider exception text
    transcript: str = ""  # restricted evidence only
    result_recorded: bool = False


class ContactPreference(SQLModel, table=True):
    phone: str = Field(primary_key=True)  # private E.164 number; never projected into public API
    reason: str  # opt_out | wrong_number
    changed_at: datetime = Field(default_factory=utcnow)
    changed_by: str = "resident"


class Event(SQLModel, table=True):
    """Append-only audit trail; the newest reason is the incident's "why it's here" line."""

    id: int | None = Field(default=None, primary_key=True)
    incident_id: int | None = Field(default=None, foreign_key="incident.id", index=True)
    type: str
    reason: str
    actor: str = "engine"  # engine | resident | a named person
    evidence: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    at: datetime = Field(default_factory=utcnow)
