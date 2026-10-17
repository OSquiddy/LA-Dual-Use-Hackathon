"""Demo twist toggles (B13–B15). In-memory on purpose: /api/demo/reset clears them."""
from app.contracts import TwistIn, TwistsView

_state = TwistsView()


def current() -> TwistsView:
    return _state


def reset(domain: str = "storm") -> None:
    global _state
    _state = TwistsView(domain=domain)


def set_twist(name: str, body: TwistIn) -> None:
    """Raises KeyError for an unknown twist.

    TODO(B13): surge -> replay seeds/surge_50.json · TODO(B14): phones_down -> callbacks fail
    TODO(B15): domain -> reset with seeds/<domain>.json
    """
    if name == "domain":
        if body.domain:
            _state.domain = body.domain
        return
    if name not in ("dept_silent", "surge", "phones_down"):
        raise KeyError(name)
    setattr(_state, name, bool(body.on))
