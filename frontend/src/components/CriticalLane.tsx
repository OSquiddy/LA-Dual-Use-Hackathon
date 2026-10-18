import { CircleCheck, Lock, OctagonAlert, User } from "lucide-react";
import { time } from "../format";
import type { CriticalAlert } from "../types";

interface Props {
  alerts: CriticalAlert[];
  selectedId: number | null;
  fresh: Set<number>;
  onSelect: (id: number) => void;
}

/** Pinned safety alerts. Never filtered, searched away or capped by the top 10. */
export default function CriticalLane({ alerts, selectedId, fresh, onSelect }: Props) {
  return (
    <section className="lane" aria-label="Critical alerts">
      <div className="lane-head">
        <span className="lane-title"><OctagonAlert /> Critical · {alerts.length}</span>
        <span className="lane-note">Pinned until a person closes the case</span>
      </div>
      {alerts.length === 0 ? (
        <div className="lane-empty"><CircleCheck /> No critical alerts</div>
      ) : (
        <div className="lane-list">
          {alerts.map((a) => (
            <button
              key={a.incident_id}
              className={[
                "alert-card",
                a.incident_id === selectedId ? "selected" : "",
                fresh.has(a.incident_id) ? "fresh" : "",
                a.accepted ? "owned" : "",
              ].join(" ")}
              onClick={() => onSelect(a.incident_id)}
            >
              <span className="alert-top">
                <span className={`dot ${a.accepted ? "ok" : "danger"}`} />
                <span className="alert-title">{a.title}</span>
              </span>
              <span className="alert-reason">{a.reason}</span>
              {a.quote && <span className="alert-quote">“{a.quote}”</span>}
              <span className="alert-meta">
                {a.accepted ? <Lock /> : <User />}
                {a.accepted ? `Accepted by ${a.owner}` : `Not accepted${a.owner ? ` · proposed ${a.owner}` : ""}`}
                <span className="since">· since {time(a.since)}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
