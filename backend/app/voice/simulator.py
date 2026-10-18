"""CALL_MODE=simulate stand-in for Retell, and the backing for the "simulate callback" fallback button."""
import threading
import uuid

from sqlmodel import Session, func, select

from app.contracts import CallbackOutcome, Outcome
from app.db import engine
from app.models import Callback

SIMULATED_DELAY_S = 8
SCRIPTED_ANSWER: tuple[Outcome, bool, str] = ("worse", True, "Water is at the curb and rising")


def schedule(incident_id: int, call_id: str, attempt_no: int) -> None:
    """Pretend the resident answers after a few seconds with the scripted answer."""
    outcome, danger, summary = SCRIPTED_ANSWER
    timer = threading.Timer(
        SIMULATED_DELAY_S,
        _deliver_scheduled,
        args=(CallbackOutcome(incident_id=incident_id, call_id=call_id, attempt_no=attempt_no,
                              outcome=outcome, danger=danger, summary=summary),),
    )
    timer.daemon = True
    timer.start()


def simulate_now(incident_id: int, outcome: Outcome, danger: bool = False) -> None:
    with Session(engine) as s:
        attempts = s.exec(select(func.count()).select_from(Callback).where(Callback.incident_id == incident_id)).one()
    summary = SCRIPTED_ANSWER[2] if outcome == "worse" else ""
    _deliver(CallbackOutcome(incident_id=incident_id, call_id=f"sim-{uuid.uuid4().hex[:8]}",
                             attempt_no=attempts + 1, outcome=outcome, danger=danger, summary=summary))


def _deliver(outcome: CallbackOutcome) -> None:
    from app.engine.ladder import record_callback_outcome

    record_callback_outcome(outcome)


def _deliver_scheduled(outcome: CallbackOutcome) -> None:
    from app.engine.ladder import record_scheduled_callback_outcome

    record_scheduled_callback_outcome(outcome)
