import { time } from "../../format";
import type { Tone } from "../../hooks";
import type { IncidentEvent } from "../../types";

const EVENT_TONE: Record<string, Tone> = {
  critical: "danger",
  accepted: "ok",
  closed: "ok",
  acknowledged: "accent",
  callback: "accent",
  callback_requested: "accent",
  nudge: "warn",
  default_owner: "warn",
  no_default_owner: "warn",
  no_callback: "warn",
};

export default function AuditTrail({ events }: { events: IncidentEvent[] | null }) {
  if (!events) return <p className="faint">Loading…</p>;
  if (events.length === 0) return <p className="faint">No events recorded.</p>;
  return (
    <ol className="trail" style={{ listStyle: "none", margin: 0 }}>
      {[...events].reverse().map((e, i) => (
        <li key={`${e.at}-${i}`} className="trail-item">
          <span className={`trail-dot ${EVENT_TONE[e.type] ?? ""}`} />
          <div className="trail-reason">{e.reason}</div>
          <div className="trail-meta">
            <span className="mono">{time(e.at)}</span>
            <span>·</span>
            <span className="actor">{e.actor === "engine" ? "HandoffProof" : e.actor}</span>
            {e.evidence.map((ref) => (
              <span key={ref} className="evidence" title="Source of this decision">{ref}</span>
            ))}
          </div>
        </li>
      ))}
    </ol>
  );
}
