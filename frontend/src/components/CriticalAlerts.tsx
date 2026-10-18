import type { CriticalAlert, Incident } from "../types";
import AssignmentSummary from "./AssignmentSummary";
import { accepted, acknowledged } from '../workspace';

interface Props {
  alerts: CriticalAlert[];
  incidents: Incident[];
  onOpen: (id: number) => void;
}

/** Independent of queue rank and acceptance; only human closure removes an alert. */
export default function CriticalAlerts({ alerts, incidents, onOpen }: Props) {
  if (alerts.length === 0) return null;
  return (
    <section className="critical-alerts" aria-label="Persistent critical alerts">
      <h2>Critical review · {alerts.length}</h2>
      {alerts.map((alert) => {
        const incident = incidents.find((row) => row.id === alert.incident_id);
        // Fail closed for an older backend/cache sending a conversation in this field.
        // The backend generates finite summaries; an unsafe payload gets no excerpt.
        const reason = alert.reason.length > 260 || /[\r\n]|\b(?:Agent|User|Assistant):/i.test(alert.reason)
          ? "Incident evidence requires review; a concise assessment is unavailable."
          : alert.reason;
        const indicator = reason.startsWith("High risk") ? "Current conditions unknown"
          : reason.includes("possible injuries") ? "Possible injuries reported"
          : reason.includes("possibly trapped") ? "Possibly trapped person reported"
          : reason.includes("possibly in the water") ? "Person possibly in water"
          : reason.includes("electrical sparking") ? "Possible electrical sparking"
          : reason.includes("rising water") ? "Possibly rising water"
          : reason.includes("worse") ? "Worsening reported" : "Possible danger reported";
        return (
        <article className="critical-alert" key={alert.incident_id}>
          <h3>{alert.title}</h3>
          {incident ? <AssignmentSummary incident={incident} compact /> : <p>Assignment data unavailable · open incident to review</p>}
          <p><strong>Danger indicator: {indicator}</strong></p>
          <p>{reason}</p>
          <p className="muted">
            Priority: critical review · Risk {incident?.risk_score ?? "unknown"}/100
          </p>
          <p><strong>Pending action:</strong> {!incident ? 'Review the incident and confirm responsibility.' : accepted(incident)
            ? 'Review current evidence and verify action before human closure.'
            : !(incident.assignment?.owner ?? incident.owner) ? 'Assign an individual and record responsibility.'
            : acknowledged(incident) ? 'Record acceptance or coordinate a documented handoff.' : 'Record acknowledgment and acceptance; review the reported danger.'}</p>
          <button onClick={() => onOpen(alert.incident_id)}>Review incident evidence</button>
        </article>
        );
      })}
    </section>
  );
}
