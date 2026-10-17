"""Database tables. SHARED FILE: B edits it; message the team before changing a field.

Reports point at their incident (instead of incidents holding report_ids) so linking is one update.
"""
from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.timeutil import utcnow


class Incident(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    area: str | None = None
    hazard_type: str
    lat: float | None = None
    lng: float | None = None
    risk_score: int = 0
    status: str = "open"  # open | accepted | escalated | closed
    ladder_step: int = 1  # 1 assigned · 2 nudge · 3 default owner · 4 callback · 5 supervisor
    next_step_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    closed_at: datetime | None = None
    closed_by: str | None = None


class Report(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: int | None = Field(default=None, foreign_key="incident.id", index=True)
    source: str
    call_id: str = Field(index=True)
    phone: str | None = None
    location_text: str | None = None
    lat: float | None = None
    lng: float | None = None
    hazard_type: str
    danger_words: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    anyone_in_danger: bool = False
    transcript: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Debt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: int = Field(foreign_key="incident.id", index=True)
    kind: str  # location | caller_unreachable | no_owner | no_update
    label: str
    opened_at: datetime = Field(default_factory=utcnow)
    cleared_at: datetime | None = None


class Assignment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: int = Field(foreign_key="incident.id", index=True)
    department: str
    owner: str | None = None
    assigned_at: datetime = Field(default_factory=utcnow)
    accepted_at: datetime | None = None
    default_owner_at: datetime | None = None


class Callback(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: int = Field(foreign_key="incident.id", index=True)
    call_id: str = Field(index=True)
    phone: str | None = None
    attempt_no: int
    outcome: str | None = None  # worse | same | better | no_answer; None while ringing
    danger: bool = False
    summary: str = ""
    called_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None


class Event(SQLModel, table=True):
    """Audit trail; the newest reason is the incident's "why it's here" line."""

    id: int | None = Field(default=None, primary_key=True)
    incident_id: int | None = Field(default=None, foreign_key="incident.id", index=True)
    type: str
    reason: str
    at: datetime = Field(default_factory=utcnow)
