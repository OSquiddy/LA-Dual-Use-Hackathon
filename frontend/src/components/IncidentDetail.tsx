import { useEffect, useState } from "react";
import { fetchIncident, simulateCallback } from "../api";
import type { IncidentDetail as Detail, Outcome } from "../types";

interface Props {
  id: number;
  onClose: () => void;
}

const OUTCOMES: Outcome[] = ["worse", "same", "better", "no_answer"];
const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

/** TODO(C4/C10): live "calling resident…" indicator, nicer timeline. */
export default function IncidentDetail({ id, onClose }: Props) {
  const [detail, setDetail] = useState<Detail | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => fetchIncident(id).then((d) => alive && setDetail(d)).catch(() => {});
    load();
    const timer = setInterval(load, 2000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [id]);

  return (
    <aside className="drawer">
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      {!detail ? (
        <p className="muted">Loading…</p>
      ) : (
        <>
          <h2>{detail.title}</h2>
          <p className="muted">
            {detail.assignment?.department} · {detail.owner ?? "no owner yet"} · risk {detail.risk_score} · step {detail.ladder_step}/5
          </p>

          <h3>Still missing</h3>
          {detail.debts.length ? (
            <ul className="debts">{detail.debts.map((d) => <li key={d.kind}>{d.label}</li>)}</ul>
          ) : (
            <p className="muted">Nothing outstanding.</p>
          )}

          <h3>Why it's here</h3>
          <ol className="timeline">
            {detail.events.map((e, i) => (
              <li key={i}>
                <time>{time(e.at)}</time> {e.reason}
              </li>
            ))}
          </ol>

          <h3>Callbacks</h3>
          {detail.callbacks.length ? (
            <ul>
              {detail.callbacks.map((c) => (
                <li key={c.attempt_no}>
                  #{c.attempt_no} · {c.outcome ?? "ringing…"} {c.summary && `— ${c.summary}`}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No callbacks yet.</p>
          )}
          <div className="sim">
            <span className="muted">Simulate callback:</span>
            {OUTCOMES.map((o) => (
              <button key={o} onClick={() => simulateCallback(id, o, o === "worse")}>{o.replace("_", " ")}</button>
            ))}
          </div>

          <h3>Reports ({detail.reports.length})</h3>
          {detail.reports.map((r) => (
            <div key={r.id} className="report">
              <div className="muted">{time(r.created_at)} · {r.location_text ?? "location unknown"} · {r.hazard_type}</div>
              <p>“{r.transcript}”</p>
            </div>
          ))}
        </>
      )}
    </aside>
  );
}
