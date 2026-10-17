"""B2: replay a seed file through ingest_report, exactly like live calls arrive."""
import json
from datetime import datetime, timedelta, timezone

from app.config import DEMO_RESIDENT_PHONE, SEEDS_DIR
from app.contracts import ReportIn
from app.engine import twists
from app.engine.ingest import ingest_report


def seed_exists(name: str) -> bool:
    return name.isidentifier() and (SEEDS_DIR / f"{name}.json").exists()


def load_seed(name: str) -> int:
    """Load seeds/<name>.json. offset_s is relative to now (negative = already happened).

    The report marked "demo_resident" gets DEMO_RESIDENT_PHONE so the live callback rings a teammate.
    TODO(B2): replay rows with a positive offset_s over time (needed for the surge twist).
    """
    data = json.loads((SEEDS_DIR / f"{name}.json").read_text(encoding="utf-8"))
    twists.reset(domain=data.get("domain", "storm"))
    now = datetime.now(timezone.utc)
    for row in data["reports"]:
        phone = DEMO_RESIDENT_PHONE if row.get("demo_resident") and DEMO_RESIDENT_PHONE else row.get("phone")
        ingest_report(
            ReportIn(
                source="seed",
                call_id=row["call_id"],
                phone=phone,
                location_text=row.get("location_text"),
                lat=row.get("lat"),
                lng=row.get("lng"),
                hazard_type=row["hazard_type"],
                danger_words=row.get("danger_words", []),
                anyone_in_danger=row.get("anyone_in_danger", False),
                transcript=row.get("transcript", ""),
                created_at=now + timedelta(seconds=row.get("offset_s", 0)),
            )
        )
    return len(data["reports"])
