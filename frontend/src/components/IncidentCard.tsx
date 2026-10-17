import type { Incident } from "../types";

const STEPS = ["Assigned", "Nudge", "Default owner", "Callback", "Supervisor"];

interface Props {
  incident: Incident;
  now: string;
  rank?: number;
  onOpen: (id: number) => void;
  onAccept?: (incident: Incident) => void;
}

/** TODO(C3/C5): hazard icon, big-screen sizing, red pulse when a card enters the supervisor queue (C8). */
export default function IncidentCard({ incident, now, rank, onOpen, onAccept }: Props) {
  const tone = incident.accepted ? "accepted" : incident.ladder_step >= 5 ? "danger" : incident.ladder_step >= 3 ? "warn" : "open";
  const secondsLeft = incident.next_step_at
    ? Math.max(0, Math.round((Date.parse(incident.next_step_at) - Date.parse(now)) / 1000))
    : null;

  return (
    <article className={`card ${tone}`} onClick={() => onOpen(incident.id)}>
      <div className="card-head">
        {rank !== undefined && <span className="rank">{rank}</span>}
        <h3>{incident.title}</h3>
        <span className="risk" title="Risk score">{incident.risk_score}</span>
      </div>

      <div className="meta">
        <span>{incident.report_count} {incident.report_count === 1 ? "witness" : "witnesses"}</span>
        <span>{incident.owner ?? incident.department ?? "Unassigned"}</span>
        {secondsLeft !== null && <span>next step in {secondsLeft}s</span>}
      </div>

      <ol className="ladder" aria-label={`Ladder step ${incident.ladder_step} of 5`}>
        {STEPS.map((label, i) => (
          <li key={label} className={i < incident.ladder_step ? "on" : ""} title={label} />
        ))}
      </ol>

      {incident.debts.length > 0 && (
        <ul className="debts">
          {incident.debts.map((d) => (
            <li key={d.kind}>{d.label}</li>
          ))}
        </ul>
      )}

      {incident.why && <p className="why">{incident.why}</p>}

      {onAccept && !incident.accepted && (
        <button
          className="accept"
          onClick={(e) => {
            e.stopPropagation();
            onAccept(incident);
          }}
        >
          Accept
        </button>
      )}
    </article>
  );
}
