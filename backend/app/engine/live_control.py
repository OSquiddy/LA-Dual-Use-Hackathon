"""Read the private local switch before every automatic live dispatch.

Startup must explicitly authorize live automation as well. File edits can pause/resume
that authorized process; missing or invalid settings fail closed without logging them.
"""
from dotenv import dotenv_values

from app.config import REPO_ROOT

SETTINGS_FILE = REPO_ROOT / '.env'


def automatic_enabled(startup_authorized: bool) -> bool:
    if not startup_authorized:
        return False
    try:
        settings = dotenv_values(SETTINGS_FILE, interpolate=False)
    except (OSError, UnicodeError):
        return False
    return settings.get('CALL_MODE') == 'live' and settings.get('LIVE_CALLBACKS_ENABLED') == '1'
