"""B3: location text -> lat/lng from seeds/gazetteer.json (no external geocoder on stage)."""
import json
import re
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


def _normalize(text: str) -> str:
    """Normalize numbered avenues using only names present in the gazetteer."""
    text = text.lower()
    units = ("", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
    tens = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"}
    for place in _gazetteer():
        for cross in place["cross"]:
            match = re.fullmatch(r"(?:avenue|ave) (\d+)", cross)
            if not match:
                continue
            number = int(match[1])
            if 20 <= number <= 99:
                words = tens[number // 10]
                if number % 10:
                    words += r"[\s-]+" + units[number % 10]
                else:
                    # "fifty two" must never become "50 two".
                    words += rf"(?![\s-]+(?:{'|'.join(units[1:])})\b)"
                text = re.sub(rf"\b(avenue|ave)\s+{words}\b", rf"\g<1> {number}", text)
    return text


def geocode(location_text: str | None) -> GeoHit | None:
    """Match "<street> ... <cross street>" in either order. None means open a location debt."""
    if not location_text:
        return None
    text = _normalize(location_text)
    for place in _gazetteer():
        if re.search(rf"\b{re.escape(place['street'])}\b", text) and any(
            re.search(rf"\b{re.escape(cross)}\b", text) for cross in place["cross"]
        ):
            return GeoHit(place["name"], place["lat"], place["lng"], place["area"])
    # TODO(B3): fuzzy match, optional LLM cleanup of messy location text
    return None


def streets_in(location_text: str | None) -> set[str]:
    """Known gazetteer streets named in the text; the linker's fallback when there is no exact spot."""
    if not location_text:
        return set()
    text = _normalize(location_text)
    return {p["street"] for p in _gazetteer() if re.search(rf"\b{re.escape(p['street'])}\b", text)}
