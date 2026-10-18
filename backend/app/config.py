"""Settings, timing profiles and the rule tables the engine reads.

Everything tunable lives here so every escalation decision stays transparent.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
SEEDS_DIR = BACKEND_DIR / "seeds"

load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Timing:
    nudge_s: int
    default_owner_s: int
    callback_s: int
    callback_retry_s: int


TIMING_PROFILES = {
    "real": Timing(nudge_s=600, default_owner_s=1200, callback_s=1800, callback_retry_s=300),
    "demo": Timing(nudge_s=15, default_owner_s=30, callback_s=45, callback_retry_s=20),
}

RETELL_API_KEY = os.getenv("RETELL_API_KEY", "")
RETELL_FROM_NUMBER = os.getenv("RETELL_FROM_NUMBER", "")
RETELL_INTAKE_AGENT_ID = os.getenv("RETELL_INTAKE_AGENT_ID", "")
RETELL_CALLBACK_AGENT_ID = os.getenv("RETELL_CALLBACK_AGENT_ID", "")
REVIEWER_API_KEY = os.getenv("REVIEWER_API_KEY", "")  # local reviewer evidence access; never a VITE_* setting
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
CALL_MODE = os.getenv("CALL_MODE", "simulate")  # simulate | live
TIMING_PROFILE = os.getenv("TIMING_PROFILE", "demo")  # demo | real
TIMING = TIMING_PROFILES[TIMING_PROFILE]
DB_PATH = os.getenv("DB_PATH") or str(BACKEND_DIR / "handoffproof.db")
DEMO_RESIDENT_PHONE = os.getenv("DEMO_RESIDENT_PHONE", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")  # optional; the engine must work without it
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

LADDER_ENABLED = os.getenv("LADDER_ENABLED", "1") != "0"  # tests drive the ladder by hand
LADDER_TICK_S = 2
LINK_RADIUS_M = 300
LINK_WINDOW_MIN = 60
SUPERVISOR_QUEUE_SIZE = 10
SUPERVISOR_MIN_RISK = 40  # unaccepted cases below this stay with their department
HIGH_RISK_THRESHOLD = 60  # high risk + no way to reach the caller -> supervisor review
MAX_CALLBACK_ATTEMPTS = max(1, int(os.getenv("MAX_CALLBACK_ATTEMPTS", "2")))
CALLBACK_RESULT_TIMEOUT_S = max(30, int(os.getenv("CALLBACK_RESULT_TIMEOUT_S", "180")))
LIVE_CALLBACKS_ENABLED = os.getenv("LIVE_CALLBACKS_ENABLED", "0") == "1"
DEPT_SILENCE_MIN_ASSIGNED = 5

HAZARD_GROUPS = {
    "water": {"flood", "blocked_drain", "water_on_road", "stalled_vehicle"},
    "road": {"pothole", "debris", "downed_tree"},
    "power": {"downed_line", "outage"},
}
HAZARD_TYPES = sorted({h for group in HAZARD_GROUPS.values() for h in group} | {"other"})

# Different reports in one group add up to a bigger incident: drain + road water + stalled car = flood.
EMERGING_HAZARD = {"water": "flood"}

HAZARD_LABELS = {
    "flood": "Flooding",
    "blocked_drain": "Blocked drain",
    "water_on_road": "Water across road",
    "stalled_vehicle": "Stalled vehicle",
    "pothole": "Pothole",
    "debris": "Debris",
    "downed_tree": "Downed tree",
    "downed_line": "Downed power line",
    "outage": "Power outage",
    "other": "Report",
}

HAZARD_DEPARTMENT = {
    "flood": "Street Services",
    "blocked_drain": "Street Services",
    "water_on_road": "Street Services",
    "stalled_vehicle": "Street Services",
    "pothole": "Street Services",
    "debris": "Street Services",
    "downed_tree": "Urban Forestry",
    "downed_line": "Power & Water",
    "outage": "Power & Water",
    "other": "Street Services",
}

HAZARD_BASE_RISK = {
    "flood": 30,
    "stalled_vehicle": 35,
    "water_on_road": 25,
    "blocked_drain": 15,
    "downed_line": 40,
    "downed_tree": 20,
    "outage": 15,
    "debris": 10,
    "pothole": 5,
    "other": 10,
}

DANGER_WORDS = [
    "trapped",
    "car stuck",
    "can't get out",
    "rising",
    "swept",
    "someone in the water",
    "sparking",
    "injured",
    "child",
    "elderly",
]
