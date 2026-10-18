import { Bot, PhoneOff, ShieldCheck } from "lucide-react";
import { time } from "../../format";
import type { Tone } from "../../hooks";
import type { Callback, Incident, IncidentDetail, Outcome } from "../../types";

const OUTCOMES: Outcome[] = ["worse", "same", "better", "no_answer"];

const OUTCOME_VIEW: Record<Outcome, { label: string; tone: Tone }> = {
  worse: { label: "Resident says worse", tone: "danger" },
  same: { label: "Resident says same", tone: "neutral" },
  better: { label: "Resident says better", tone: "ok" },
  no_answer: { label: "No answer · status unknown", tone: "warn" },
};

interface Props {
  incident: Incident;
  detail: IncidentDetail | null;
  disabled: boolean;
  onSimulate: (outcome: Outcome) => void;
}

/** Retell callbacks. Only callers who clearly said yes are ever called. */
export default function FollowUpCard({ incident, detail, disabled, onSimulate }: Props) {
  const reports = detail?.reports ?? [];
  const consenting = reports.filter((r) => r.callback_ok);
  const callbacks = detail?.callbacks ?? [];
  const latest: Callback | undefined = callbacks[callbacks.length - 1];
  const ringing = latest && latest.outcome === null;
  const answered = [...callbacks].reverse().find((c) => c.outcome !== null);

  let pill = { label: "No calls yet", tone: "neutral" as Tone };
  if (detail && consenting.length === 0) pill = { label: "No permission · no calls", tone: "neutral" };
  if (answered) pill = OUTCOME_VIEW[answered.outcome!];
  if (ringing) pill = { label: "Calling resident…", tone: "accent" };

  return (
    <section className="card">
      <div className="card-head">
        <h3 className="card-title"><Bot /> Resident follow-up</h3>
        <span className={`pill ${pill.tone}`}>
          <span className={`dot ${pill.tone}`} /> {pill.label}
        </span>
      </div>

      {detail && (
        <div className="consent">
          {consenting.length ? <ShieldCheck /> : <PhoneOff />}
          <span>
            {consenting.length
              ? `${consenting.length} of ${reports.length} callers agreed to a callback (${consenting.map((r) => r.phone).join(", ")}). Nobody else is called.`
              : "No caller gave callback permission, so no calls will be placed. A person must follow up."}
          </span>
        </div>
      )}

      {ringing && (
        <div className="calling">
          <span className="wave" aria-hidden><span /><span /><span /><span /><span /><span /></span>
          Calling the resident who gave permission · attempt {latest.attempt_no}
        </div>
      )}

      {answered && (answered.summary || answered.outcome === "no_answer") && (
        <div className={`quote ${answered.outcome === "worse" || answered.danger ? "danger" : ""}`}>
          <div className="section-label">Callback #{answered.attempt_no} · {time(answered.called_at)}</div>
          <p>
            {answered.outcome === "no_answer"
              ? "No answer. We don't know whether conditions changed. That is not treated as worse."
              : `“${answered.summary}”`}
          </p>
        </div>
      )}

      {callbacks.length > 0 && (
        <div className="attempts">
          {callbacks.map((c) => (
            <div key={c.attempt_no} className="attempt">
              <span className={`dot ${c.outcome ? OUTCOME_VIEW[c.outcome].tone : "accent"}`} />
              #{c.attempt_no} · {c.outcome ? OUTCOME_VIEW[c.outcome].label : "ringing"}
              {c.danger && <span className="pill tag danger">danger reported</span>}
              <span className="mono">{time(c.called_at)}</span>
            </div>
          ))}
        </div>
      )}

      {!disabled && (
        <div className="sim">
          <span className="pill tag caps accent">Simulated</span>
          {OUTCOMES.map((o) => (
            <button key={o} className="btn sm" onClick={() => onSimulate(o)} title={`Record a simulated "${o.replace("_", " ")}" answer for ${incident.title}`}>
              {o.replace("_", " ")}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
