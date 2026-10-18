"""B8: default on-call owner per department and area, from seeds/oncall.json. Never invented."""
import json
from functools import cache

from app.config import HAZARD_DEPARTMENT, SEEDS_DIR


@cache
def _roster() -> dict:
    data = json.loads((SEEDS_DIR / "oncall.json").read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def default_owner(department: str, area: str | None) -> str | None:
    entries = _roster().get(department, {})
    if not isinstance(entries, dict):
        return None
    name = entries.get(area or "")
    return name.strip() if isinstance(name, str) and name.strip() else None


def assignment_options(area: str | None) -> list[dict]:
    return [
        {"department": department, "owners": [name] if (name := default_owner(department, area)) else []}
        for department in sorted(set(HAZARD_DEPARTMENT.values()))
    ]
