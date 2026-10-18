"""Demo twist toggles (B13–B15). In-memory on purpose: /api/demo/reset clears them."""
from app.contracts import TwistIn, TwistsView

_state = TwistsView()


def current() -> TwistsView:
    return _state


def reset(domain: str = "storm") -> None:
    global _state
    _state = TwistsView(domain=domain)


def set_twist(name: str, body: TwistIn) -> None:
    """Apply supported demo actions; reject unsupported domains without mutating state."""
    if name == "domain":
        # Storm is the only implemented domain; do not pretend an arbitrary label is a demo.
        if body.domain != "storm":
            raise KeyError(body.domain)
        _state.domain = "storm"
        return
    if name not in ("dept_silent", "surge", "phones_down"):
        raise KeyError(name)
    if name == "surge" and body.on and not _state.surge:
        from app.engine.seeds import prepare_seed
        from app.engine.ingest import ingest_report

        _, reports = prepare_seed("surge_50")
        for report in reports:
            ingest_report(report)
    setattr(_state, name, bool(body.on))
