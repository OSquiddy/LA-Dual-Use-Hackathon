import stateFixture from "./fixtures/state.json";
import incidentFixture from "./fixtures/incident.json";
import type { AppState, AssignmentHistoryPage, AssignmentOptions, IncidentDetail, Outcome } from "./types";

export const API_MODE = import.meta.env.VITE_API ?? "fixture";

/** Resolves to "sent" in live mode and "skipped" in fixture mode, so the UI can say which. */
export type ActionResult = "sent" | "skipped";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) throw new Error(`${init?.method ?? "GET"} ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

function post<T>(path: string, body: unknown, reviewerKey?: string): Promise<T | void> {
  if (API_MODE === "fixture") {
    console.info(`[fixture mode] skipped POST ${path}`, body);
    return "skipped";
  }
  return request<T>(path, { method: "POST", body: JSON.stringify(body),
    ...(reviewerKey !== undefined ? { headers: { "Content-Type": "application/json", Authorization: `Bearer ${reviewerKey}` } } : {}),
  });
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

export function fetchAssignmentHistory(beforeId?: number): Promise<AssignmentHistoryPage> {
  if (API_MODE === 'fixture') return Promise.resolve({ entries: (incidentFixture.assignment_history ?? [incidentFixture.assignment]).map(assignment => ({
    incident_id: incidentFixture.id, title: incidentFixture.title, status: incidentFixture.status as IncidentDetail['status'], assignment,
  })), next_before_id: null });
  return request('/api/assignment-history' + (beforeId ? `?before_id=${beforeId}` : ''));
}

export function fetchIncidentEvidence(id: number, reviewerKey: string): Promise<IncidentDetail> {
  if (API_MODE === "fixture") return Promise.resolve({ ...(incidentFixture as IncidentDetail), id });
  return request(`/api/incidents/${id}/evidence`, {
    cache: "no-store", headers: { Authorization: `Bearer ${reviewerKey}` },
  });
}

export const acceptIncident = (id: number, owner: string, expected_assignment_id?: number, reviewerKey?: string) =>
  post(`/api/incidents/${id}/accept`, { owner, expected_assignment_id }, reviewerKey);

export const acknowledgeIncident = (id: number, by: string, expected_assignment_id?: number, reviewerKey?: string) =>
  post(`/api/incidents/${id}/acknowledge`, { by, expected_assignment_id }, reviewerKey);

export function fetchAssignmentOptions(id: number): Promise<AssignmentOptions> {
  if (API_MODE === "fixture") return Promise.resolve({ recommended_department: incidentFixture.assignment.department,
    area: null, departments: [], fictional_roster: true });
  return request(`/api/incidents/${id}/assignment-options`);
}

export const reassignIncident = (id: number, body: { department: string; owner: string | null; by: string; reason: string; expected_assignment_id?: number }, reviewerKey: string) =>
  post(`/api/incidents/${id}/reassign`, body, reviewerKey);

export const simulateCallback = (id: number, outcome: Outcome, danger = false, reviewerKey?: string) =>
  post(`/api/incidents/${id}/simulate-callback`, { outcome, danger }, reviewerKey);

export const requestCallback = (id: number, by: string, reviewerKey: string, confirm_live = false) =>
  post(`/api/incidents/${id}/request-callback`, { by, confirm_live }, reviewerKey);

export const optOutReport = (id: number, by: string, reviewerKey: string, reason = 'opt_out') =>
  post(`/api/reports/${id}/callback-opt-out`, { by, reason }, reviewerKey);

export const setTwist = (name: string, body: { on?: boolean; domain?: string }) => post(`/api/twists/${name}`, body);

export const resetDemo = (seed = "storm_night") => post("/api/demo/reset", { seed });
