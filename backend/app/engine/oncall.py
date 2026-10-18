"""Configured fictional operations directory. Assignment selection is stable, never random."""
import json
from functools import cache

from app.config import HAZARD_DEPARTMENT, SEEDS_DIR


@cache
def _configuration() -> dict:
    return json.loads((SEEDS_DIR / 'oncall.json').read_text(encoding='utf-8'))


def department_info(department: str) -> dict:
    return _configuration().get('_departments', {}).get(department, {})


def staff_profile(identity: str | None) -> dict | None:
    if not identity:
        return None
    for person in _configuration().get('_staff', []):
        if identity in (person['id'], person['name'], *person.get('aliases', [])):
            return person
    return None


def available_staff(department: str, area: str | None) -> list[dict]:
    areas = _configuration().get(department, {})
    if not isinstance(areas, dict):
        return []
    entries = areas.get(area or '', areas.get('*', []))
    entries = [entries] if isinstance(entries, str) else entries
    if not isinstance(entries, list):
        return []
    people = []
    for entry in entries:
        person = staff_profile(entry)
        if person and person.get('department') == department and person.get('on_call') is True:
            people.append(person)
        elif person is None and isinstance(entry, str) and entry.strip():
            people.append({'id': entry, 'name': entry.strip(), 'role': None, 'on_call': True, 'fictional': True})
    return people


def default_owner(department: str, area: str | None, incident_id: int | None = None) -> str | None:
    people = available_staff(department, area)
    return people[((incident_id or 1) - 1) % len(people)]['name'] if people else None


def assignment_profile(department: str, owner: str | None, area: str | None) -> dict:
    info, person = department_info(department), staff_profile(owner)
    person = person if person and person.get('department') == department else None
    return {
        'department_display_name': info.get('display_name', department),
        'operational_unit': info.get('unit'),
        'owner_display_name': person['name'] if person else owner,
        'owner_role': person.get('role') if person else None,
        'staff_id': person.get('id') if person else None,
        'roster_area': area if area and area in _configuration().get(department, {}) else 'Citywide demo coverage' if '*' in _configuration().get(department, {}) else None,
        'fictional_personnel': bool(person),
    }


def assignment_options(area: str | None) -> list[dict]:
    return [{'department': department, 'owners': [p['name'] for p in available_staff(department, area)],
             'display_name': department_info(department).get('display_name', department),
             'operational_unit': department_info(department).get('unit'),
             'staff': available_staff(department, area)} for department in sorted(set(HAZARD_DEPARTMENT.values()))]


def directory() -> dict[str, dict]:
    return _configuration().get('_departments', {})


def department_staff(department: str) -> list[dict]:
    return [p for p in _configuration().get('_staff', []) if p.get('department') == department]
