import { PhoneOff, ShieldCheck } from "lucide-react";
import { hazardLabel, time } from "../../format";
import type { Report } from "../../types";

export default function ReportsList({ reports }: { reports: Report[] | null }) {
  if (!reports) return <p className="faint">Loading…</p>;
  if (reports.length === 0) return <p className="faint">No reports loaded for this incident.</p>;
  return (
    <div className="reports">
      {reports.map((r) => (
        <article key={r.id} className="report">
          <div className="report-top">
            <span className="evidence">report:{r.id}</span>
            <span className="loc">{r.location_text ?? "Location unknown"}</span>
            <span className="chip">{hazardLabel(r.hazard_type)}</span>
            {r.danger_words.map((w) => (
              <span key={w} className="pill tag danger">{w}</span>
            ))}
            <span style={{ marginLeft: "auto" }} className="mono">{r.phone ?? "no number"} · {time(r.created_at)}</span>
            {r.callback_ok ? (
              <span className="pill tag ok"><ShieldCheck /> callback OK</span>
            ) : (
              <span className="pill tag"><PhoneOff /> no callback</span>
            )}
          </div>
          <p>“{r.transcript}”</p>
        </article>
      ))}
    </div>
  );
}
