import { Check, CircleCheck, Eye, Flag, Send } from "lucide-react";
import { clock, secondsUntil, time } from "../../format";
import type { Incident, IncidentDetail } from "../../types";

const LADDER = ["Assigned", "Nudge", "On-call", "Follow-up", "Supervisor"];

interface Props {
  incident: Incident;
  detail: IncidentDetail | null;
  now: string;
}

export default function AccountabilityChain({ incident, detail, now }: Props) {
  const a = detail?.assignment ?? null;
  const closedEvent = [...(detail?.events ?? [])].reverse().find((e) => e.type === "closed");
  const left = secondsUntil(incident.next_step_at, now);

  const steps = [
    {
      label: "Assigned",
      icon: Send,
      state: "done",
      detail: incident.owner && !incident.accepted ? `${incident.department} · proposed ${incident.owner}` : incident.department ?? "—",
      at: a?.assigned_at,
    },
    {
      label: "Acknowledged",
      icon: Eye,
      state: a?.acknowledged_at ? "done" : "pending",
      detail: a?.acknowledged_at ? `by ${a.acknowledged_by}` : "Receipt not confirmed",
      at: a?.acknowledged_at,
    },
    {
      label: "Accepted",
      icon: CircleCheck,
      state: incident.accepted ? "done" : incident.critical ? "missing" : "pending",
      detail: incident.accepted ? `by ${a?.accepted_by ?? incident.owner}` : "No one has accepted",
      at: a?.accepted_at,
    },
    {
      label: "Resolved",
      icon: Flag,
      state: closedEvent ? "done" : "pending",
      detail: closedEvent ? closedEvent.reason : "Only a person can close",
      at: closedEvent?.at,
    },
  ];

  return (
    <>
      <ol className="chain" style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {steps.map(({ label, icon: Icon, state, detail: text, at }) => (
          <li key={label} className={`chain-step ${state}`}>
            <span className="chain-icon">{state === "done" ? <Check /> : <Icon />}</span>
            <div className="chain-label">{label}</div>
            <div className="chain-detail">{text}</div>
            {at && <div className="chain-time mono">{time(at)}</div>}
          </li>
        ))}
      </ol>

      <div className="ladder">
        <div className="ladder-head">
          <span>Escalation ladder · step {incident.ladder_step} of 5</span>
          <span className="mono faint">
            {incident.accepted ? "stopped: accepted" : left !== null ? `next step in ${clock(left)}` : "waiting on a person"}
          </span>
        </div>
        <div className="ladder-bar">
          {LADDER.map((name, i) => (
            <span key={name} className={`ladder-seg ${i < incident.ladder_step ? "on" : ""} ${incident.critical ? "danger" : ""}`} />
          ))}
        </div>
        <div className="ladder-labels">
          {LADDER.map((name, i) => (
            <span key={name} className={i + 1 === incident.ladder_step ? "current" : ""}>{name}</span>
          ))}
        </div>
      </div>
    </>
  );
}
