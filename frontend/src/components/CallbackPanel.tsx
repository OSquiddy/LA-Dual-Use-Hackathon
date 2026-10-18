import { useEffect, useRef, useState } from "react";
import { API_MODE, optOutReport, requestCallback, simulateCallback } from "../api";
import type { Callback, IncidentDetail, Outcome } from "../types";

const OUTCOMES: Outcome[] = ["worse", "same", "better", "no_answer"];
const STATES: Record<string, string> = { scheduled: "Scheduled", dispatching: "Dispatching", calling: "Calling",
  completed: "Completed", failed: "Failed", cancelled: "Cancelled", unknown: "Unknown · human review required" };
const time = (stamp: string) => new Date(stamp).toLocaleString();

// Older backends may put a whole conversation in summary. Project finite structured
// facts here too; raw summaries and transcripts belong to the restricted evidence view.
function explanation(callback: Callback): string {
  if (callback.error_code === "wrong_number") return "Wrong number reported; further callbacks blocked. Conditions unknown.";
  if (callback.error_code === "opt_out") return "Resident opted out; further callbacks blocked. Conditions unknown.";
  if (callback.outcome === "no_answer") return "Resident unreachable; conditions unknown, not confirmed worse.";
  const condition = callback.outcome === "worse" ? "Resident reports worsening."
    : callback.outcome === "same" ? "Resident reports conditions unchanged."
    : callback.outcome === "better" ? "Resident reports improvement; the case remains open until human closure."
    : "No verified condition update is available.";
  return condition + (callback.danger ? " Possible danger reported; details are unverified." : "");
}

/** Controls use stored contacts only. Keys remain in memory and never enter the request body. */
export default function CallbackPanel({ incident, onChanged }: { incident: IncidentDetail; onChanged: () => void }) {
  const [actor, setActor] = useState("");
  const [key, setKey] = useState("");
  const [confirmLive, setConfirmLive] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const active = useRef(true);
  const busy = useRef(false);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  const status = incident.callback_status;
  const live = status?.call_mode === "live";
  const disabled = API_MODE === "fixture" || pending || !actor.trim() || !key.trim();

  async function act(action: "request" | "opt_out" | "simulate", reportId?: number, outcome?: Outcome) {
    if (disabled || busy.current || (action === "request" && (!status?.eligible || (live && !confirmLive)))) return;
    busy.current = true;
    setPending(true);
    setMessage("");
    try {
      if (action === "request") await requestCallback(incident.id, actor.trim(), key, live && confirmLive);
      else if (action === "opt_out" && reportId !== undefined) await optOutReport(reportId, actor.trim(), key);
      else if (action === "simulate" && outcome && !live) await simulateCallback(incident.id, outcome, outcome === "worse", key);
      else return;
      if (active.current) {
        setMessage(action === "opt_out" ? "Opt-out recorded. Further callbacks to this contact are blocked." : "Request acknowledged. The callback history shows the recorded result.");
        onChanged();
      }
    } catch {
      if (active.current) setMessage("Action was not confirmed. Refresh the incident and check eligibility and authorization before retrying.");
    } finally {
      busy.current = false;
      if (active.current) { setKey(""); setConfirmLive(false); setPending(false); }
    }
  }

  return (
    <section className="assignment-actions" aria-label="Resident callbacks">
      <h3>Resident callbacks</h3>
      <p><strong>{live ? "Live calling mode" : "Simulation · no phone calls"}</strong></p>
      <p>Callback eligibility: {status?.eligible ? "Eligible contact" : "Unavailable"}. {status?.reason ?? "Eligibility has not been checked."}</p>
      {status?.scheduled_at && <p>Scheduled callback time: <time dateTime={status.scheduled_at}>{time(status.scheduled_at)}</time></p>}
      {status && <p className="muted">Attempts: {status.attempts_used}/{status.max_attempts}. {live && !status.automatic_live_enabled && "Automatic live dispatch is disabled."}</p>}
      <p className="muted">Risk {incident.risk_score}/100. {incident.critical ? "Supervisor review required; see the incident evidence and audit trail." : "No critical review flag recorded."}</p>
      {incident.callbacks.length ? <ol className="timeline">{incident.callbacks.map((callback) => (
        <li key={callback.id ?? callback.attempt_no}>
          <strong>Attempt #{callback.attempt_no} · {STATES[callback.state ?? "unknown"] ?? "Status unavailable"}</strong>
          <div>{callback.mode === "simulate" && "Simulated · "}Outcome: {callback.outcome === "no_answer" ? "No answer · conditions unknown" : callback.outcome ?? "Conditions unknown"}</div>
          {callback.danger && <div>Possible immediate danger reported · supervisor review</div>}
          <p>{explanation(callback)}</p>
          {callback.scheduled_at && <div>Scheduled: <time dateTime={callback.scheduled_at}>{time(callback.scheduled_at)}</time></div>}
          {callback.completed_at && <time dateTime={callback.completed_at}>{time(callback.completed_at)}</time>}
        </li>
      ))}</ol> : <p className="muted">No callbacks yet.</p>}
      <p className="muted">Automatic follow-up waits for the configured deadline and stops when a human accepts or closes the case. Assignment alone does not mean acceptance.</p>
      {incident.reports.map((report) => <p key={report.id}>
        Report #{report.id} · Callback permission: {report.callback_ok ? "given" : "not given"}
        {report.callback_opt_out ? " · Contact opted out or number blocked" : report.callback_eligible ? " · Eligible stored contact" : " · Contact not eligible"}
      </p>)}
      <details>
        <summary>Authorized callback controls</summary>
        <label>Your name<input value={actor} maxLength={80} autoComplete="name" onChange={(event) => setActor(event.target.value)} /></label>
        <label>Reviewer authorization key<input type="password" value={key} autoComplete="off" onChange={(event) => setKey(event.target.value)} /></label>
        <p className="muted">Request one callback now using an eligible resident's stored number. This skips the wait and still checks consent, opt-outs, and attempt limits.</p>
        {live && <label className="callback-confirm"><input type="checkbox" checked={confirmLive} onChange={(event) => setConfirmLive(event.target.checked)} /> I confirm one real phone call to the consenting resident for this incident.</label>}
        <button disabled={disabled || !status?.eligible || (live && !confirmLive)} onClick={() => void act("request")}>
          {live ? "Place one confirmed live callback" : "Request one simulated callback"}
        </button>
        {incident.reports.filter((report) => !report.callback_opt_out).map((report) => <button key={report.id} disabled={disabled}
          onClick={() => void act("opt_out", report.id)}>Record opt-out for report #{report.id}</button>)}
        {!live && <details><summary>Synthetic outcome demonstration</summary>
          <p className="muted">Adds clearly simulated evidence without dialing a phone. These controls do not represent resident answers.</p>
          {OUTCOMES.map((outcome) => <button key={outcome} disabled={disabled} onClick={() => void act("simulate", undefined, outcome)}>Simulate {outcome.replace("_", " ")}</button>)}
        </details>}
        {API_MODE === "fixture" && <p className="muted">Fixture preview · controls require live dashboard integration.</p>}
      </details>
      {pending && <p role="status">Recording callback action…</p>}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
