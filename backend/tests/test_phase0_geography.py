
"""Phase 0 checks for the Highland Park demo geography."""

import json

import pytest

from app.config import LINK_RADIUS_M, SEEDS_DIR
from app.engine.geocode import geocode
from app.engine.linker import distance_m, hazard_group


def test_storm_reports_have_demo_locations():
    data = json.loads(
        (SEEDS_DIR / "storm_night.json").read_text(
            encoding="utf-8"
        )
    )

    hits = []

    for report in data["reports"]:
        hit = geocode(report["location_text"])
        assert hit is not None
        assert hit.area == "Highland Park"
        assert hazard_group(report["hazard_type"]) == "water"
        hits.append(hit)

    assert len(hits) == 3
    assert len({(h.lat, h.lng) for h in hits}) == 3

    for i in range(len(hits)):
        for j in range(i + 1, len(hits)):
            distance = distance_m(
                hits[i].lat,
                hits[i].lng,
                hits[j].lat,
                hits[j].lng,
            )
            assert distance <= LINK_RADIUS_M


def test_distant_street_is_outside_link_radius():
    near = geocode("Figueroa and Avenue 52")
    far = geocode("Figueroa and Avenue 57")

    assert near is not None
    assert far is not None

    assert distance_m(
        near.lat, near.lng,
        far.lat, far.lng,
    ) > LINK_RADIUS_M


def test_cross_street_order_does_not_matter():
    first = geocode("Figueroa and Avenue 52")
    second = geocode("Avenue 52 by Figueroa")

    assert first is not None
    assert first == second


def test_unknown_location_is_not_guessed():
    assert geocode("Unknown location") is None


@pytest.mark.parametrize("location", [
    "Figueroa and Avenue fifty two",
    "Figueroa and Ave 52",
    "Avenue Fifty-Two by Figueroa",
    "Ave fifty two and Figueroa",
])
def test_numbered_avenue_variants(location):
    expected = geocode("Figueroa and Avenue 52")
    assert expected is not None
    assert geocode(location) == expected


@pytest.mark.parametrize("location", [
    "Figueroa and Ave 520",
    "Figueroa and Avenue fifty nine",
    "Other street and Avenue fifty two",
])
def test_unlisted_avenue_is_not_guessed(location):
    assert geocode(location) is None
