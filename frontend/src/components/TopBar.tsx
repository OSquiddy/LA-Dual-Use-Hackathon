import { useEffect, useRef, useState } from "react";
import { Monitor, Moon, Search, ShieldAlert, Sun, TriangleAlert } from "lucide-react";
import { API_MODE } from "../api";
import type { ThemeChoice, Tone } from "../hooks";
import type { AppState } from "../types";
import DemoControls from "./DemoControls";

interface Props {
  state: AppState | null;
  callMode: string | null;
  query: string;
  onQuery: (q: string) => void;
  theme: ThemeChoice;
  onTheme: (t: ThemeChoice) => void;
  operator: string;
  onOperator: (name: string) => void;
  notify: (text: string, tone?: Tone) => void;
  onChanged: () => void;
}

const NEXT_THEME: Record<ThemeChoice, ThemeChoice> = { system: "light", light: "dark", dark: "system" };
const THEME_ICON = { system: Monitor, light: Sun, dark: Moon };

export default function TopBar(props: Props) {
  const { state, callMode, query, onQuery, theme, onTheme, operator, onOperator, notify, onChanged } = props;
  const searchRef = useRef<HTMLInputElement>(null);
  const ThemeIcon = THEME_ICON[theme];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const opsAlert = state?.alerts[0];

  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark"><ShieldAlert /></span>
        HandoffProof
      </div>
      <span className="divider hide-md" />

      <div className="topbar-group">
        {API_MODE === "live" ? (
          <span className="pill ok mono">
            <span className="live-dot" /> Live{state ? ` · ${state.timing_profile} timing` : ""}
          </span>
        ) : (
          <span className="pill warn mono">Sample data</span>
        )}
        {callMode && (
          <span className={`pill mono hide-md ${callMode === "live" ? "danger" : "accent"}`}>
            Calls {callMode === "live" ? "live" : "simulated"}
          </span>
        )}
        {opsAlert && (
          <span className="pill warn hide-lg" title={opsAlert.text}>
            <TriangleAlert /> {opsAlert.text}
          </span>
        )}
      </div>

      <div className="topbar-spacer" />

      <span className="pill tag hide-md" title="Hackathon prototype. Not affiliated with the City of Los Angeles; not connected to 911 or dispatch.">
        Prototype · not a city service
      </span>

      <label className="search">
        <Search />
        <span className="sr-only">Search incidents</span>
        <input ref={searchRef} value={query} onChange={(e) => onQuery(e.target.value)} placeholder="Search incidents…" />
        <kbd>⌘K</kbd>
      </label>

      <DemoControls twists={state?.twists ?? null} notify={notify} onChanged={onChanged} />

      <button
        className="btn ghost icon"
        onClick={() => onTheme(NEXT_THEME[theme])}
        title={`Theme: ${theme} (click to change)`}
        aria-label={`Theme: ${theme}. Switch to ${NEXT_THEME[theme]}`}
      >
        <ThemeIcon />
      </button>

      <OperatorChip name={operator} onChange={onOperator} />
    </header>
  );
}

/** Who is acting. Acknowledge / Accept / Close are recorded under this name. */
function OperatorChip({ name, onChange }: { name: string; onChange: (n: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(name);
  const initials = name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase() || "?";

  const save = () => {
    const next = draft.trim();
    if (next) onChange(next);
    else setDraft(name);
    setEditing(false);
  };

  if (editing) {
    return (
      <span className="operator">
        <span className="avatar">{initials}</span>
        <input
          autoFocus
          value={draft}
          aria-label="Your name for the audit trail"
          onChange={(e) => setDraft(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => {
            if (e.key === "Enter") save();
            if (e.key === "Escape") {
              setDraft(name);
              setEditing(false);
            }
          }}
        />
      </span>
    );
  }
  return (
    <button className="operator" onClick={() => setEditing(true)} title="Your name, recorded on every action you take">
      <span className="avatar">{initials}</span>
      <span className="hide-md">{name}</span>
    </button>
  );
}
