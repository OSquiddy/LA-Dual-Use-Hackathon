import { useEffect, useRef, useState } from "react";
import { API_MODE, acceptIncident, acknowledgeIncident, fetchAssignmentOptions, reassignIncident } from "../api";
import type { AssignmentOptions, IncidentDetail } from "../types";

/** Human actions require an explicitly entered name; opening the drawer performs no write. */
export default function AssignmentActions({ incident, onChanged }: { incident: IncidentDetail; onChanged: () => void }) {
  const [actor, setActor] = useState("");
  const [department, setDepartment] = useState(incident.department ?? "");
  const [owner, setOwner] = useState("__choose__");
  const [reason, setReason] = useState("");
  const [options, setOptions] = useState<AssignmentOptions | null>(null);
  const [optionsError, setOptionsError] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [reviewerKey, setReviewerKey] = useState("");
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    if (incident.status !== "closed") fetchAssignmentOptions(incident.id).then((value) => {
      if (active.current) setOptions(value);
    }).catch(() => { if (active.current) setOptionsError(true); });
    return () => { active.current = false; };
  }, [incident.id, incident.status]);
  useEffect(() => {
    setDepartment(incident.department ?? "");
    setOwner("__choose__");
    setReviewerKey("");
    setSuccess("");
  }, [incident.assignment?.id, incident.department]);

  if (incident.status === "closed") return null;
  const expectedId = incident.assignment?.id ?? undefined;
  const disabled = pending || !actor.trim() || !reviewerKey.trim() || API_MODE === "fixture";
  const owners = options?.departments.find((option) => option.department === department)?.owners ?? [];
  async function record(action: "acknowledge" | "accept" | "reassign") {
    if (!reviewerKey.trim()) {
      setError("Reviewer authorization is required to record a human action.");
      return;
    }
    setPending(true);
    setError("");
    setSuccess("");
    try {
      if (action === "acknowledge") await acknowledgeIncident(incident.id, actor.trim(), expectedId, reviewerKey);
      else if (action === "accept") await acceptIncident(incident.id, actor.trim(), expectedId, reviewerKey);
      else await reassignIncident(incident.id, { department, owner: owner || null, by: actor.trim(), reason: reason.trim(), expected_assignment_id: expectedId }, reviewerKey);
      if (active.current) {
        setSuccess(action === "acknowledge" ? "Acknowledgment recorded. Responsibility has not been accepted." : action === "accept" ? "Acceptance recorded under your entered name." : "Assignment updated. A new acknowledgment and acceptance are required.");
        onChanged();
      }
    } catch {
      if (active.current) setError(action === "reassign"
        ? "Reassignment was not confirmed. Check reviewer authorization and server configuration, then refresh the incident before retrying."
        : "Action was not confirmed. Refresh the incident and check the selected assignment before retrying.");
    } finally {
      if (active.current) {
        setPending(false);
        setReviewerKey("");
      }
    }
  }

  return (
    <section className="assignment-actions" aria-label="Record responsibility actions">
      <h3>Record a human action</h3>
      <label>Your name
        <input value={actor} maxLength={80} autoComplete="name" onChange={(event) => setActor(event.target.value)} placeholder="Enter the person taking this action" />
      </label>
      <label>Reviewer authorization key
        <input type="password" value={reviewerKey} autoComplete="off" onChange={(event) => setReviewerKey(event.target.value)} />
      </label>
      <p className="muted">Acknowledgment records receipt. Acceptance records responsibility under your entered name.</p>
      <div className="action-buttons">
        <button disabled={disabled || !incident.department || incident.acknowledged || incident.accepted} onClick={() => void record("acknowledge")}>Record acknowledgment</button>
        <button className="accept" disabled={disabled || !incident.department || incident.accepted} onClick={() => void record("accept")}>Accept responsibility</button>
      </div>
      <details>
        <summary>Assign or reassign responsibility</summary>
        {optionsError ? <p role="alert">Assignment options unavailable. Reopen this incident to retry.</p> : !options ? <p className="muted">Loading configured roster…</p> : (
          <>
            <p className="muted">Hazard routing recommends {options.recommended_department}. Changing the department requires a recorded reason.</p>
            <label>Responsible department
              <select value={department} onChange={(event) => { setDepartment(event.target.value); setOwner("__choose__"); }}>
                <option value="">Select a department</option>
                {options.departments.map((option) => <option key={option.department}>{option.department}</option>)}
              </select>
            </label>
            <label>Assigned individual · configured demo roster
              <select value={owner} onChange={(event) => setOwner(event.target.value)}>
                <option value="__choose__" disabled>Select an individual assignment</option>
                <option value="">Department only · individual not assigned</option>
                {owners.map((name) => <option key={name}>{name}</option>)}
              </select>
            </label>
            {!owners.length && department && <p className="muted">No on-call individual is configured for this department and area. No person will be invented.</p>}
            <label>Reason for assignment change
              <input value={reason} maxLength={240} onChange={(event) => setReason(event.target.value)} />
            </label>
            <button disabled={disabled || !reviewerKey.trim() || !department || owner === "__choose__" || !reason.trim() ||
              (department === incident.department && (owner || null) === incident.owner)} onClick={() => void record("reassign")}>Save assignment</button>
          </>
        )}
      </details>
      {API_MODE === "fixture" && <p className="muted">Fictional fixture preview · human actions require live mode.</p>}
      {pending && <p role="status">Recording action…</p>}
      {success && <p role="status">{success}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
