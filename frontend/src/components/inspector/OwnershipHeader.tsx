import { CircleCheck, Eye, Lock, MapPin, OctagonAlert, ShieldAlert, User } from "lucide-react";
import { clock, hazardLabel, hpId, riskTone, secondsUntil } from "../../format";
import type { Assignment, Incident } from "../../types";

interface Props {
  incident: Incident;
  assignment: Assignment | null;
  now: string;
  onAcknowledge: () => void;
  onAccept: () => void;
}

export default function OwnershipHeader({ incident, assignment, now, onAcknowledge, onAccept }: Props) {
  const closed = incident.status === "closed";
  const left = secondsUntil(incident.next_step_at, now);
  const next = left !== null ? ` Next escalation step in ${clock(left)}.` : "";

  let tone = "warn";
  let status = "Awaiting accept";
  let Icon = User;
  let text = (
    <>
      Not accepted yet.{incident.owner && <> Proposed owner <b>{incident.owner}</b>.</>}
      {next}
    </>
  );
  if (closed) {
    tone = "";
    status = "Closed";
    Icon = CircleCheck;
    text = <>Closed by a person. Kept for the record.</>;
  } else if (incident.accepted) {
    tone = "ok";
    status = "Owned";
    Icon = Lock;
    text = (
      <>
        Accepted by <b>{incident.owner}</b>. The ladder has stopped; the case stays open until a person closes it.
        {incident.critical && " Its critical alert stays pinned until then."}
      </>
    );
  } else if (incident.critical) {
    tone = "danger";
    status = "Supervisor review";
    Icon = ShieldAlert;
    text = (
      <>
        {incident.owner ? <>Proposed owner <b>{incident.owner}</b>, not accepted. </> : <>No owner. </>}
        {incident.why}
      </>
    );
  } else if (incident.acknowledged) {
    status = "Acknowledged";
    Icon = Eye;
    text = (
      <>
        Acknowledged by <b>{assignment?.acknowledged_by ?? "someone"}</b>: receipt only, not accepted.{next}
      </>
    );
  }

  return (
    <header className="inspector-head">
      <div className="head-inner">
        <div className="head-row">
          <div style={{ minWidth: 0 }}>
            <div className="head-meta">
              {incident.department && <span className="chip">{incident.department}</span>}
              <span className="mono">{hpId(incident.id)}</span>
              <span className="sep">•</span>
              <span>{incident.report_count} {incident.report_count === 1 ? "report" : "linked reports"}</span>
              <span className="sep">•</span>
              <span>{hazardLabel(incident.hazard_type)}</span>
              <span className={`pill tag mono ${riskTone(incident)}`} title="Risk from evidence only; time and silence never change it">
                Risk {incident.risk_score}
              </span>
              {incident.critical && <span className="pill tag danger"><OctagonAlert /> Critical</span>}
            </div>
            <h1 className="head-title">{incident.title}</h1>
            {incident.lat !== null && incident.lng !== null && (
              <div className="head-sub mono">
                <MapPin /> {incident.lat.toFixed(4)}, {incident.lng.toFixed(4)} · approximate
              </div>
            )}
          </div>

          {!closed && (
            <div className="head-actions">
              {incident.accepted ? (
                <button className="btn locked" disabled>
                  <Lock /> Accepted by {incident.owner}
                </button>
              ) : (
                <>
                  <button className="btn" onClick={onAcknowledge} disabled={incident.acknowledged} title="Confirms you've seen it. Does not take responsibility.">
                    <Eye /> {incident.acknowledged ? "Acknowledged" : "Acknowledge receipt"}
                  </button>
                  <button className="btn primary" onClick={onAccept} title="Take responsibility for this case under your name">
                    <CircleCheck /> Accept responsibility
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        <div className={`callout ${tone}`}>
          <span className="callout-text"><Icon /> <span>{text}</span></span>
          <span className={`pill caps ${tone}`}>{status}</span>
        </div>
      </div>
    </header>
  );
}
