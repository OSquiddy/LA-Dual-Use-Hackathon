import { useState } from "react";
import { API_MODE } from "./api";
import { useHandoffState } from "./useHandoffState";
import AlertBanner from "./components/AlertBanner";
import DepartmentQueue from "./components/DepartmentQueue";
import IncidentDetail from "./components/IncidentDetail";
import SupervisorQueue from "./components/SupervisorQueue";
import TwistPanel from "./components/TwistPanel";

export default function App() {
  const { state, error } = useHandoffState();
  const [openId, setOpenId] = useState<number | null>(null);

  return (
    <div className="app">
      <header className="topbar">
        <h1>HandoffProof</h1>
        <span className="tagline">An incident isn't handled until someone accepts responsibility — and the evidence is still visible.</span>
        <span className="badges">
          <span className="badge prototype">Prototype demo · not a city service</span>
          <span className="badge">{API_MODE}</span>
          {state && <span className="badge">{state.timing_profile} timing</span>}
          {state && <span className="badge">{state.twists.domain}</span>}
        </span>
      </header>

      {error && <div className="error">Backend unreachable: {error}</div>}
      {state && <AlertBanner alerts={state.alerts} />}

      {state ? (
        <main className="panes">
          <DepartmentQueue state={state} onOpen={setOpenId} />
          <SupervisorQueue state={state} onOpen={setOpenId} />
        </main>
      ) : (
        !error && <p className="muted pad">Loading…</p>
      )}

      {openId !== null && <IncidentDetail id={openId} onClose={() => setOpenId(null)} />}
      {state && <TwistPanel twists={state.twists} />}
    </div>
  );
}
