import { useEffect, useRef, useState } from "react";
import { API_MODE, fetchIncidentEvidence } from "../api";
import type { IncidentDetail } from "../types";

/** Reviewer credentials and fetched evidence live only in this open drawer's memory. */
export default function EvidenceReview({ id }: { id: number }) {
  const [reviewerKey, setReviewerKey] = useState("");
  const [evidence, setEvidence] = useState<IncidentDetail | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; };
  }, []);

  async function unlock() {
    setLoading(true);
    setError("");
    try {
      const result = await fetchIncidentEvidence(id, reviewerKey);
      if (active.current) setEvidence(result);
    } catch {
      if (active.current) setError("Evidence unavailable. Check reviewer authorization and server configuration.");
    } finally {
      if (active.current) {
        setLoading(false);
        setReviewerKey("");
      }
    }
  }

  return (
    <section aria-label="Restricted incident evidence">
      <h3>Incident evidence · reviewer access</h3>
      {evidence ? (
        <>
          <button onClick={() => setEvidence(null)}>Lock evidence</button>
          {evidence.reports.map((report) => (
            <div className="report" key={report.id}>
              <h4>Report #{report.id} · Full transcript</h4>
              <pre className="transcript">{report.transcript || "No transcript recorded."}</pre>
            </div>
          ))}
          {evidence.callbacks.filter((callback) => callback.summary || callback.transcript).map((callback) => (
            <div className="report" key={callback.attempt_no}>
              <h4>Callback #{callback.attempt_no} · Source summary</h4>
              <pre className="transcript">{callback.summary}</pre>
              <h4>Full callback transcript</h4>
              <pre className="transcript">{callback.transcript || "No transcript recorded."}</pre>
            </div>
          ))}
        </>
      ) : (
        <form onSubmit={(event) => { event.preventDefault(); void unlock(); }}>
          <p className="muted">Full conversations are available to authorized reviewers. Permission to call back is shown separately for each report.</p>
          {API_MODE !== "fixture" && (
            <label>Reviewer access key
              <input type="password" value={reviewerKey} autoComplete="off" onChange={(event) => setReviewerKey(event.target.value)} />
            </label>
          )}
          <button type="submit" disabled={loading || (API_MODE !== "fixture" && !reviewerKey)}>
            {loading ? "Loading evidence…" : "Unlock incident evidence"}
          </button>
          {error && <p role="alert">{error}</p>}
        </form>
      )}
    </section>
  );
}
