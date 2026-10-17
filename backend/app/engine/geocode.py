"""B3: location text -> lat/lng from seeds/gazetteer.json (no external geocoder on stage)."""
import json
from dataclasses import dataclass
from functools import cache

from app.config import SEEDS_DIR


@dataclass(frozen=True)
class GeoHit:
    name: str
    lat: float
    lng: float
    area: str


@cache
def _gazetteer() -> list[dict]:
    return json.loads((SEEDS_DIR / "gazetteer.json").read_text(encoding="utf-8"))["places"]


def geocode(location_text: str | None) -> GeoHit | None:
    """Match "<street> ... <cross street>" in either order. None means open a location debt."""
    if not location_text:
        return None
    text = location_text.lower()
    for place in _gazetteer():
        if place["street"] in text and any(cross in text for cross in place["cross"]):
            return GeoHit(place["name"], place["lat"], place["lng"], place["area"])
    # TODO(B3): fuzzy match, street-only fallback, optional LLM cleanup of messy location text
    return None
