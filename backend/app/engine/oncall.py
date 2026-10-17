"""B8: default on-call owner per department and area, from seeds/oncall.json. Never invented."""
import json
from functools import cache

from app.config import SEEDS_DIR


@cache
def _roster() -> dict:
    data = json.loads((SEEDS_DIR / "oncall.json").read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def default_owner(department: str, area: str | None) -> str | None:
    return _roster().get(department, {}).get(area or "")
