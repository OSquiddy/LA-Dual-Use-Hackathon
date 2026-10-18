"""Validate complete scenarios before destructive demo reset, then ingest each source report."""
import json
from datetime import datetime, timedelta, timezone

from app.config import DEMO_RESIDENT_PHONE, SEEDS_DIR
from app.contracts import ReportIn
from app.engine import twists
from app.engine.ingest import ingest_report


def prepare_seed(name: str) -> tuple[str, list[ReportIn]]:
    if not name.isidentifier():
        raise ValueError("Invalid scenario name")
    data = json.loads((SEEDS_DIR / f"{name}.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("reports"), list) or not data["reports"]:
        raise ValueError("Not a report scenario")
    domain = data.get("domain", "storm")
    if not isinstance(domain, str) or not domain:
        raise ValueError("Invalid scenario domain")
    now = datetime.now(timezone.utc)
    reports = []
    for row in data["reports"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid scenario row")
        fields = {k: row[k] for k in ReportIn.model_fields if k in row}
        fields.update(source="seed", created_at=now + timedelta(seconds=row.get("offset_s", 0)))
        if row.get("demo_resident") and DEMO_RESIDENT_PHONE:
            fields["phone"] = DEMO_RESIDENT_PHONE
        report = ReportIn.model_validate(fields)
        if not report.call_id.strip():
            raise ValueError("Missing scenario call ID")
        reports.append(report)
    if len({r.call_id for r in reports}) != len(reports):
        raise ValueError("Duplicate scenario call IDs")
    return domain, reports


def seed_exists(name: str) -> bool:
    try:
        prepare_seed(name)
    except (OSError, ValueError, TypeError, OverflowError):
        return False
    return True


def load_seed(name: str) -> int:
    domain, reports = prepare_seed(name)
    twists.reset(domain=domain)
    for report in reports:
        ingest_report(report)
    return len(reports)
