import { useEffect, useRef, useState } from "react";
import { fetchIncident } from "../api";
import type { IncidentDetail as Detail } from "../types";
import EvidenceReview from "./EvidenceReview";
import AssignmentSummary from "./AssignmentSummary";
import AssignmentActions from "./AssignmentActions";
import AssignmentHistory from "./AssignmentHistory";
import CallbackPanel from "./CallbackPanel";

interface Props {
  id: number;
  onClose: () => void;
}

const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export default function IncidentDetail({ id, onClose }: Props) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState(false);

  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    panel.current?.focus();
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
      if (event.key === 'Tab') {
        const targets = Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), summary, a[href], [tabindex="0"]') ?? []);
        const first = targets[0], last = targets[targets.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === panel.current)) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener('keydown', keyboard);
    return () => { document.body.style.overflow = overflow; document.removeEventListener('keydown', keyboard); previous?.focus(); };
  }, []);
  useEffect(() => {
    let alive = true;
    setDetail(null);
    setError(false);
    const load = () => fetchIncident(id).then((d) => {
      if (alive) {
        setDetail(d);
        setError(false);
      }
    }).catch(() => { if (alive) setError(true); });
    load();
    const timer = setInterval(load, 2000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [id]);

  return (
    <div className="drawer-backdrop" onClick={onClose}><aside ref={panel} className="drawer" role="dialog" aria-modal="true" aria-label={`Incident ${id} details`} tabIndex={-1} onClick={event => event.stopPropagation()}>
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      {error && <p role="alert">Could not load this incident. Retrying…</p>}
      {!detail ? (
        !error && <p className="muted">Loading…</p>
      ) : (
        <>
          <div className="eyebrow">INCIDENT #{detail.id} · {detail.status}</div><h2>{detail.title}</h2>
          <nav className="detail-nav" aria-label="Incident sections">{["Overview", "Responsibility", "Assignment History", "Follow-up", "Evidence"].map(label => <a key={label} href={`#detail-${label.toLowerCase().replace(/ /g, "-")}`}>{label}</a>)}</nav>
          <h3 id="detail-overview">Overview</h3><p>Hazard: {detail.hazard_type.replace(/_/g, " ")}. Reported location: {detail.reports.find(r => r.location_text)?.location_text ?? "Not confirmed"}.</p>
          <p className="muted">
            Risk {detail.risk_score}/100 · step {detail.ladder_step}/5
          </p>
          <h3 id="detail-responsibility">Responsibility</h3><AssignmentSummary incident={detail} />
          <AssignmentActions key={detail.id} incident={detail} onChanged={() => {
            fetchIncident(id).then(setDetail).catch(() => setError(true));
          }} />
          <div id="detail-assignment-history"><AssignmentHistory incident={detail} /></div>

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
                <div className="muted">
                  {e.actor}{e.evidence.length > 0 && ` · Evidence: ${e.evidence.join(", ")}`}
                </div>
              </li>
            ))}
          </ol>

          <h3 id="detail-follow-up">Follow-up</h3>
          <CallbackPanel key={detail.id} incident={detail} onChanged={() => {
            fetchIncident(id).then(setDetail).catch(() => setError(true));
          }} />

          <h3 id="detail-evidence">Evidence · reports ({detail.reports.length})</h3>
          {detail.reports.map((r) => (
            <div key={r.id} className="report">
              <div className="muted">{time(r.created_at)} · {r.location_text ?? "location unknown"} · {r.hazard_type}</div>
              <div className="muted">
                Report #{r.id} · Callback permission: {r.callback_ok ? "given" : "not given"}
                {r.danger_words.length > 0 && ` · Extracted danger phrases: ${r.danger_words.join(", ")}`}
              </div>
            </div>
          ))}
          <EvidenceReview key={detail.id} id={detail.id} />
        </>
      )}
    </aside></div>
  );
}
