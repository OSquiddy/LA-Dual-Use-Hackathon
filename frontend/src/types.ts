// Mirrors backend/app/contracts.py. Change both together (and message the team).

export type Status = "open" | "accepted" | "escalated" | "closed";
export type Outcome = "worse" | "same" | "better" | "no_answer";

export interface Debt {
  kind: string; // location | caller_unreachable | no_owner | no_update
  label: string;
}

export interface Incident {
  id: number;
  title: string;
  hazard_type: string;
  status: Status;
  ladder_step: number; // 1 assigned · 2 nudge · 3 default owner · 4 callback · 5 supervisor
  risk_score: number;
  report_count: number;
  department: string | null;
  owner: string | null;
  accepted: boolean;
  next_step_at: string | null;
  debts: Debt[];
  why: string;
  lat: number | null;
  lng: number | null;
}

export interface Department {
  name: string;
  assigned_1h: number;
  accepted_1h: number;
  silent: boolean;
}

export interface Alert {
  type: string;
  department: string | null;
  text: string;
}

export interface Twists {
  dept_silent: boolean;
  surge: boolean;
  phones_down: boolean;
  domain: string;
}

export interface AppState {
  now: string;
  timing_profile: string;
  twists: Twists;
  incidents: Incident[];
  supervisor_queue: number[];
  departments: Department[];
  alerts: Alert[];
}

export interface Report {
  id: number;
  call_id: string;
  phone: string | null;
  location_text: string | null;
  hazard_type: string;
  danger_words: string[];
  transcript: string;
  created_at: string;
}

export interface IncidentEvent {
  type: string;
  reason: string;
  at: string;
}

export interface Callback {
  attempt_no: number;
  outcome: Outcome | null;
  danger: boolean;
  summary: string;
  called_at: string;
}

export interface Assignment {
  department: string;
  owner: string | null;
  assigned_at: string;
  accepted_at: string | null;
  default_owner_at: string | null;
}

export interface IncidentDetail extends Incident {
  reports: Report[];
  events: IncidentEvent[];
  callbacks: Callback[];
  assignment: Assignment | null;
}
