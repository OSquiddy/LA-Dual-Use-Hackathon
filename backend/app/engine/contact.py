"""Explicit consent and stored number checks; no transcript-based consent inference."""
import re

from sqlmodel import Session, col, select

from app.models import Callback, ContactPreference, Incident, Report
from app.engine.audit import log_event
from app.timeutil import utcnow


def valid_phone(value: str | None) -> bool:
    return isinstance(value, str) and re.fullmatch(r"\+[1-9][0-9]{7,14}", value) is not None


def eligible_report(s: Session, report: Report, *, live_only=False) -> bool:
    return (not live_only or report.source == 'retell') and report.callback_ok is True and not report.callback_opt_out and valid_phone(report.phone) and s.get(ContactPreference, report.phone) is None


def target(s: Session, incident: Incident, *, live_only=False) -> Report | None:
    reports = s.exec(select(Report).where(Report.incident_id == incident.id).order_by(col(Report.created_at).desc(), col(Report.id).desc())).all()
    return next((r for r in reports if eligible_report(s, r, live_only=live_only)), None)


def blocker(s: Session, incident: Incident, *, live_only=False) -> tuple[str, str, str] | None:
    reports = s.exec(select(Report).where(Report.incident_id == incident.id)).all()
    if any(eligible_report(s, r, live_only=live_only) for r in reports):
        return None
    if live_only and not any(r.source == 'retell' and r.callback_ok for r in reports):
        return ('consent_unknown', 'Live callbacks require explicit consent from a resident intake call; seed permissions authorize simulation only', 'no live resident consent')
    if any(r.callback_opt_out or (valid_phone(r.phone) and s.get(ContactPreference, r.phone)) for r in reports):
        return ('callback_opt_out', 'Callback blocked by opt-out or wrong-number record; a person must follow up', 'callback contact blocked')
    consented = [r for r in reports if r.callback_ok and (not live_only or r.source == 'retell')]
    if consented:
        if any(r.phone and r.phone.strip() for r in consented):
            return ('callback_number_invalid', 'Callback permitted; a valid E.164 callback number is required', 'callback number invalid')
        return ('callback_number_missing', 'Callback permitted; callback number missing. A person must follow up', 'callback number missing')
    return ('consent_unknown', 'No callback permission recorded; follow-up needs a person', 'no callback permission recorded')


def block(s: Session, report: Report, reason: str, by: str = 'resident') -> None:
    existing = s.get(ContactPreference, report.phone) if valid_phone(report.phone) else None
    if report.callback_opt_out and (not valid_phone(report.phone) or existing is not None):
        return
    report.callback_opt_out = True
    if valid_phone(report.phone):
        preference = s.get(ContactPreference, report.phone)
        if preference is None:
            s.add(ContactPreference(phone=report.phone, reason=reason, changed_by=by))
        else:
            preference.reason, preference.changed_by, preference.changed_at = reason, by, utcnow()
        jobs = s.exec(select(Callback).where(Callback.phone == report.phone, Callback.state == 'scheduled')).all()
    else:
        jobs = s.exec(select(Callback).where(Callback.report_id == report.id, Callback.state == 'scheduled')).all()
    for job in jobs:
        job.state, job.error_code, job.completed_at = 'cancelled', 'contact_blocked', utcnow()
    log_event(s, report.incident_id, 'callback_opt_out', 'Further callbacks blocked: ' + ('wrong number' if reason == 'wrong_number' else 'resident opted out'), actor=by, evidence=[f'report:{report.id}'])
