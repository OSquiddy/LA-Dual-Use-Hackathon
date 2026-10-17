import { useEffect, useState } from "react";
import { fetchState } from "./api";
import type { AppState } from "./types";

/** Polls /api/state. Polling (not websockets) is deliberate: one less thing to break on stage. */
export function useHandoffState(intervalMs = 1000) {
  const [state, setState] = useState<AppState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const next = await fetchState();
        if (alive) {
          setState(next);
          setError(null);
        }
      } catch (e) {
        if (alive) setError(String(e));
      }
    };
    tick();
    const timer = setInterval(tick, intervalMs);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [intervalMs]);

  return { state, error };
}
