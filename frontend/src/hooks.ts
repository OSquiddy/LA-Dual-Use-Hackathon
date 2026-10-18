import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCallMode, fetchIncident, fetchState } from "./api";
import type { AppState, IncidentDetail } from "./types";

/** Polls /api/state. Polling (not websockets) is deliberate: one less thing to break on stage. */
export function useHandoffState(intervalMs = 1000) {
  const [state, setState] = useState<AppState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const alive = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const next = await fetchState();
      if (alive.current) {
        setState(next);
        setError(null);
      }
    } catch (e) {
      if (alive.current) setError(String(e));
    }
  }, []);

  useEffect(() => {
    alive.current = true;
    refresh();
    const timer = setInterval(refresh, intervalMs);
    return () => {
      alive.current = false;
      clearInterval(timer);
    };
  }, [refresh, intervalMs]);

  return { state, error, refresh };
}

export function useIncidentDetail(id: number, intervalMs = 1500) {
  const [detail, setDetail] = useState<IncidentDetail | null>(null);
  const alive = useRef(true);

  const reload = useCallback(async () => {
    try {
      const next = await fetchIncident(id);
      if (alive.current) setDetail(next);
    } catch {
      // keep the last good copy; the state poll shows the backend banner
    }
  }, [id]);

  useEffect(() => {
    alive.current = true;
    setDetail(null);
    reload();
    const timer = setInterval(reload, intervalMs);
    return () => {
      alive.current = false;
      clearInterval(timer);
    };
  }, [reload, intervalMs]);

  return { detail, reload };
}

export function useCallMode() {
  const [mode, setMode] = useState<string | null>(null);
  useEffect(() => {
    fetchCallMode().then(setMode);
  }, []);
  return mode;
}

// --- per-viewer preferences (browser storage may be blocked; never required) -------------------

function readStored(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStored(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // private window or blocked storage: the preference just won't persist
  }
}

export function useStoredString(key: string, fallback: string) {
  const [value, setValue] = useState(() => readStored(key) || fallback);
  useEffect(() => writeStored(key, value), [key, value]);
  return [value, setValue] as const;
}

export type ThemeChoice = "system" | "light" | "dark";

export function useTheme() {
  const [stored, setStored] = useStoredString("hp.theme", "system");
  const choice: ThemeChoice = stored === "light" || stored === "dark" ? stored : "system";
  useEffect(() => {
    const root = document.documentElement;
    if (choice === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", choice);
  }, [choice]);
  return [choice, setStored as (t: ThemeChoice) => void] as const;
}

// --- toasts ------------------------------------------------------------------------------------

export type Tone = "danger" | "warn" | "ok" | "accent" | "neutral";
export interface Toast {
  id: number;
  text: string;
  tone: Tone;
}

let toastSeq = 0;

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const notify = useCallback((text: string, tone: Tone = "neutral") => {
    const id = ++toastSeq;
    setToasts((t) => [...t.slice(-3), { id, text, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);
  return { toasts, notify };
}

/** Ids of critical alerts that appeared since the previous poll (for the arrival animation + toast). */
export function useNewCriticalAlerts(state: AppState | null, notify: (text: string, tone: Tone) => void) {
  const previous = useRef<Set<number> | null>(null);
  const [fresh, setFresh] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!state) return;
    const ids = new Set(state.critical_alerts.map((a) => a.incident_id));
    if (previous.current) {
      const added = state.critical_alerts.filter((a) => !previous.current!.has(a.incident_id));
      if (added.length) {
        added.forEach((a) => notify(`Critical: ${a.title} — ${a.reason}`, "danger"));
        setFresh(new Set(added.map((a) => a.incident_id)));
        setTimeout(() => setFresh(new Set()), 5000);
      }
    }
    previous.current = ids;
  }, [state, notify]);

  return fresh;
}
