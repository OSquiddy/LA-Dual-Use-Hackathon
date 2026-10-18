import stateFixture from "./fixtures/state.json";
import incidentFixture from "./fixtures/incident.json";
import type { AppState, IncidentDetail, Outcome } from "./types";

export const API_MODE = import.meta.env.VITE_API ?? "fixture";

/** Resolves to "sent" in live mode and "skipped" in fixture mode, so the UI can say which. */
export type ActionResult = "sent" | "skipped";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) throw new Error(`${init?.method ?? "GET"} ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function post(path: string, body: unknown): Promise<ActionResult> {
  if (API_MODE === "fixture") {
    console.info(`[fixture mode] skipped POST ${path}`, body);
    return "skipped";
  }
  await request(path, { method: "POST", body: JSON.stringify(body) });
  return "sent";
}

export function fetchState(): Promise<AppState> {
  if (API_MODE === "fixture") return Promise.resolve(stateFixture as AppState);
  return request("/api/state");
}

export function fetchIncident(id: number): Promise<IncidentDetail> {
  if (API_MODE === "fixture") {
    if (id === incidentFixture.id) return Promise.resolve(incidentFixture as IncidentDetail);
    const summary = (stateFixture as AppState).incidents.find((i) => i.id === id);
    if (!summary) return Promise.reject(new Error(`incident ${id} not in fixtures`));
    return Promise.resolve({ ...summary, reports: [], events: [], callbacks: [], assignment: null });
  }
  return request(`/api/incidents/${id}`);
}

export async function fetchCallMode(): Promise<string | null> {
  if (API_MODE === "fixture") return null;
  try {
    return (await request<{ call_mode: string }>("/health")).call_mode;
  } catch {
    return null;
  }
}

export const acknowledgeIncident = (id: number, by: string) => post(`/api/incidents/${id}/acknowledge`, { by });

export const acceptIncident = (id: number, owner: string) => post(`/api/incidents/${id}/accept`, { owner });

export const closeIncident = (id: number, by: string, note: string) => post(`/api/incidents/${id}/close`, { by, note });

export const simulateCallback = (id: number, outcome: Outcome, danger = false) =>
  post(`/api/incidents/${id}/simulate-callback`, { outcome, danger });

export const setTwist = (name: string, body: { on?: boolean; domain?: string }) => post(`/api/twists/${name}`, body);

export const resetDemo = (seed = "storm_night") => post("/api/demo/reset", { seed });
