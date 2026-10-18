import type { Tone } from "./hooks";
import type { Incident } from "./types";

export const hpId = (id: number) => `HP-${String(id).padStart(4, "0")}`;

export const HAZARD_LABELS: Record<string, string> = {
  flood: "Flooding",
  blocked_drain: "Blocked drain",
  water_on_road: "Water across road",
  stalled_vehicle: "Stalled vehicle",
  pothole: "Pothole",
  debris: "Debris",
  downed_tree: "Downed tree",
  downed_line: "Downed power line",
  outage: "Power outage",
  other: "Report",
};

export const hazardLabel = (h: string) => HAZARD_LABELS[h] ?? h.replace(/_/g, " ");

export function secondsUntil(iso: string | null, nowIso: string): number | null {
  if (!iso) return null;
  return Math.max(0, Math.round((Date.parse(iso) - Date.parse(nowIso)) / 1000));
}

export function clock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  return `${m}:${String(seconds % 60).padStart(2, "0")}`;
}

export function time(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

/** Red is reserved for critical or genuinely high-risk cases, never just for "old" or "unaccepted". */
export function incidentTone(i: Incident): Tone {
  if (i.status === "closed") return "neutral";
  if (i.accepted) return "ok";
  if (i.critical) return "danger";
  return "warn";
}

export function riskTone(i: Incident): Tone {
  if (i.critical || i.risk_score >= 60) return "danger";
  if (i.risk_score >= 30) return "warn";
  return "neutral";
}

export function ownershipLabel(i: Incident): string {
  if (i.status === "closed") return "Closed";
  if (i.accepted) return `Accepted by ${i.owner ?? "someone"}`;
  if (i.critical) return "Supervisor review · not accepted";
  if (i.acknowledged) return "Acknowledged · not accepted";
  if (i.owner) return `Proposed: ${i.owner}`;
  return "Waiting for Accept";
}
