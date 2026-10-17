"""B2: replay a seed file through ingest_report, exactly like live calls arrive."""
import json
from datetime import datetime, timedelta, timezone

from app.config import DEMO_RESIDENT_PHONE, SEEDS_DIR
from app.contracts import ReportIn
from app.engine import twists
from app.engine.ingest import ingest_report


def seed_exists(name: str) -> bool:
    try:
        prepare_seed(name)
        return True
    except (ValueError, OSError, KeyError, TypeError):
        return False


def prepare_seed(name: str) -> tuple[str, list[ReportIn]]:
    """Validate every row before the caller can erase any existing data."""
    if not name.isidentifier():
        raise ValueError("Invalid scenario name")
    data = json.loads((SEEDS_DIR / f"{name}.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("reports"), list) or not data["reports"]:
        raise ValueError("Not a report scenario")
    now = datetime.now(timezone.utc)
    reports = []
    for row in data["reports"]:
        phone = DEMO_RESIDENT_PHONE if row.get("demo_resident") and DEMO_RESIDENT_PHONE else row.get("phone")
        reports.append(ReportIn.model_validate(dict(
            row, source="seed", phone=phone,
            created_at=now + timedelta(seconds=row.get("offset_s", 0)),
        )))
    if len({r.call_id for r in reports}) != len(reports):
        raise ValueError("Duplicate scenario call IDs")
    return data.get("domain", "storm"), reports


def load_seed(name: str) -> int:
    """Load seeds/<name>.json. offset_s is relative to now (negative = already happened).

    The report marked "demo_resident" gets DEMO_RESIDENT_PHONE so the live callback rings a teammate.
    TODO(B2): replay rows with a positive offset_s over time (needed for the surge twist).
    """
    domain, reports = prepare_seed(name)
    twists.reset(domain=domain)
    for report in reports:
        ingest_report(report)
    return len(reports)
