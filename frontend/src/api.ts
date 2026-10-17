import stateFixture from "./fixtures/state.json";
import incidentFixture from "./fixtures/incident.json";
import type { AppState, IncidentDetail, Outcome } from "./types";

export const API_MODE = import.meta.env.VITE_API ?? "fixture";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) throw new Error(`${init?.method ?? "GET"} ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

function post<T>(path: string, body: unknown): Promise<T | void> {
  if (API_MODE === "fixture") {
    console.info(`[fixture mode] skipped POST ${path}`, body);
    return Promise.resolve();
  }
  return request<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export function fetchState(): Promise<AppState> {
  if (API_MODE === "fixture") return Promise.resolve(stateFixture as AppState);
  return request("/api/state");
}

export function fetchIncident(id: number): Promise<IncidentDetail> {
  if (API_MODE === "fixture") return Promise.resolve({ ...(incidentFixture as IncidentDetail), id });
  return request(`/api/incidents/${id}`);
}

export const acceptIncident = (id: number, owner: string) => post(`/api/incidents/${id}/accept`, { owner });

export const simulateCallback = (id: number, outcome: Outcome, danger = false) =>
  post(`/api/incidents/${id}/simulate-callback`, { outcome, danger });

export const setTwist = (name: string, body: { on?: boolean; domain?: string }) => post(`/api/twists/${name}`, body);

export const resetDemo = (seed = "storm_night") => post("/api/demo/reset", { seed });
