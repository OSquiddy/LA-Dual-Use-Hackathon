// Mirrors backend/app/contracts.py. Change both together (and message the team).

export type Status = "open" | "accepted" | "escalated" | "closed";
export type Outcome = "worse" | "same" | "better" | "no_answer";

export interface Debt {
  kind: string; // location | caller_unreachable | no_owner | no_update | consent_unknown
  label: string;
}

export interface Incident {
  id: number;
  title: string;
  hazard_type: string;
  status: Status;
  ladder_step: number; // 1 assigned · 2 nudge · 3 default owner · 4 callback · 5 supervisor (= critical)
  risk_score: number; // physical risk from evidence only
  report_count: number;
  department: string | null;
  owner: string | null; // proposed (default on-call) or accepting owner; see `accepted`
  accepted: boolean;
  next_step_at: string | null;
  debts: Debt[];
  why: string;
  lat: number | null;
  lng: number | null;
  acknowledged: boolean; // receipt only; never implies accepted
  critical: boolean; // also listed in AppState.critical_alerts
  assignment: Assignment | null;
  closed_at: string | null;
  closed_by: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  callback_state?: string | null;
  priority?: "critical" | "high" | "medium" | "low";
}

export interface Department {
  name: string;
  assigned_1h: number;
  accepted_1h: number;
  silent: boolean;
  display_name?: string | null;
  operational_unit?: string | null;
  active_incidents?: number;
  awaiting_acceptance?: number;
  staff?: Staff[];
}

export interface Staff { id: string; name: string; role: string | null; on_call: boolean; fictional: boolean }

export interface Alert {
  type: string;
  department: string | null;
  text: string;
}

/** Pinned safety alert. Never capped by the top 10; stays until a human closes the case. */
export interface CriticalAlert {
  incident_id: number;
  title: string;
  reason: string;
  quote: string; // the resident's own words behind the alert
  evidence: string[]; // e.g. ["report:3", "callback:2"]
  since: string;
  accepted: boolean;
  owner: string | null;
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
  supervisor_queue: number[]; // highest risk first, capped at 10
  departments: Department[];
  alerts: Alert[];
  critical_alerts: CriticalAlert[]; // uncapped, shown apart from the top 10
  call_mode?: string;
  automatic_live_enabled?: boolean;
}

export interface Report {
  id: number;
  call_id: string;
  phone: string | null; // masked, e.g. "•••0103"
  location_text: string | null;
  hazard_type: string;
  danger_words: string[];
  transcript: string;
  created_at: string;
  callback_ok: boolean;
  callback_opt_out?: boolean;
  callback_eligible?: boolean;
}

export interface IncidentEvent {
  type: string;
  reason: string;
  at: string;
  actor: string; // engine | resident | a named person
  evidence: string[]; // e.g. ["report:3"]
}

export interface Callback {
  attempt_no: number;
  outcome: Outcome | null;
  danger: boolean;
  summary: string;
  called_at: string;
  id?: number | null;
  state?: string;
  scheduled_at?: string | null;
  completed_at?: string | null;
  error_code?: string | null;
  mode?: string;
  transcript?: string; // restricted evidence only
}

export interface CallbackStatus {
  eligible: boolean;
  reason: string;
  scheduled_at: string | null;
  call_mode: string;
  attempts_used: number;
  max_attempts: number;
  automatic_live_enabled: boolean;
}

export interface Assignment {
  department: string;
  owner: string | null;
  assigned_at: string;
  accepted_at: string | null;
  default_owner_at: string | null;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  accepted_by: string | null;
  id: number | null;
  assigned_by: string | null;
  change_reason: string | null;
  department_display_name?: string | null;
  operational_unit?: string | null;
  owner_display_name?: string | null;
  owner_role?: string | null;
  staff_id?: string | null;
  roster_area?: string | null;
  fictional_personnel?: boolean;
  profile_recorded?: boolean;
}

export interface AssignmentOptions {
  recommended_department: string;
  area: string | null;
  departments: { department: string; owners: string[]; display_name?: string | null; operational_unit?: string | null; staff?: Staff[] }[];
  fictional_roster: boolean;
}

export interface IncidentDetail extends Incident {
  reports: Report[];
  events: IncidentEvent[];
  callbacks: Callback[];
  assignment_history: Assignment[];
  callback_status?: CallbackStatus;
}

export interface AssignmentHistoryEntry { incident_id: number; title: string; status: Status; assignment: Assignment }
export interface AssignmentHistoryPage { entries: AssignmentHistoryEntry[]; next_before_id: number | null }
