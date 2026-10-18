import { useState } from "react";
import { MousePointerClick, WifiOff } from "lucide-react";
import CriticalLane from "./components/CriticalLane";
import IncidentList from "./components/IncidentList";
import Inspector from "./components/Inspector";
import Toasts from "./components/Toasts";
import TopBar from "./components/TopBar";
import { useCallMode, useHandoffState, useNewCriticalAlerts, useStoredString, useTheme, useToasts } from "./hooks";

export default function App() {
  const { state, error, refresh } = useHandoffState();
  const [theme, setTheme] = useTheme();
  const [operator, setOperator] = useStoredString("hp.operator", "Supervisor desk");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const { toasts, notify } = useToasts();
  const callMode = useCallMode();
  const fresh = useNewCriticalAlerts(state, notify);

  // Until the user picks one (or theirs is closed): first critical alert, else the highest-risk incident.
  const picked = state?.incidents.find((i) => i.id === selectedId);
  const fallbackId = state?.critical_alerts.find((a) => state.incidents.some((i) => i.id === a.incident_id))?.incident_id;
  const selected = picked ?? state?.incidents.find((i) => i.id === fallbackId) ?? state?.incidents[0] ?? null;
  const activeId = selected?.id ?? null;

  return (
    <div className="app">
      <TopBar
        state={state}
        callMode={callMode}
        query={query}
        onQuery={setQuery}
        theme={theme}
        onTheme={setTheme}
        operator={operator}
        onOperator={setOperator}
        notify={notify}
        onChanged={refresh}
      />

      {error && (
        <div className="banner-error" role="alert">
          <WifiOff /> Backend unreachable ({error}). Showing the last known state.
        </div>
      )}

      <div className="workspace">
        <aside className="sidebar">
          {state && (
            <>
              <CriticalLane alerts={state.critical_alerts} selectedId={activeId} fresh={fresh} onSelect={setSelectedId} />
              <IncidentList state={state} query={query} selectedId={activeId} onSelect={setSelectedId} />
              {state.departments.length > 0 && (
                <footer className="depts" aria-label="Department acceptance, last hour">
                  {state.departments.map((d) => (
                    <div key={d.name} className={`dept-line ${d.silent ? "silent" : ""}`}>
                      <span>{d.name}{d.silent && " · silent"}</span>
                      <span className="mono">accepted {d.accepted_1h}/{d.assigned_1h} · 1h</span>
                    </div>
                  ))}
                </footer>
              )}
            </>
          )}
          {!state && !error && <p className="list-empty">Loading…</p>}
        </aside>

        <main className="inspector-pane">
          {state && selected ? (
            <Inspector
              key={selected.id}
              incident={selected}
              now={state.now}
              operator={operator}
              notify={notify}
              onChanged={refresh}
            />
          ) : (
            <div className="inspector-empty">
              <div>
                <MousePointerClick />
                <p>{state ? "No open incidents. Reset the demo with T." : "Waiting for the backend…"}</p>
              </div>
            </div>
          )}
        </main>
      </div>

      <Toasts toasts={toasts} />
    </div>
  );
}
