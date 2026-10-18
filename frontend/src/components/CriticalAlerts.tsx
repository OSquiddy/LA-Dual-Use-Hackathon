import type { CriticalAlert } from "../types";

interface Props {
  alerts: CriticalAlert[];
  onOpen: (id: number) => void;
}

/** Independent of queue rank and acceptance; only human closure removes an alert. */
export default function CriticalAlerts({ alerts, onOpen }: Props) {
  if (alerts.length === 0) return null;
  return (
    <section className="critical-alerts" aria-label="Persistent critical alerts">
      <h2>Critical review · {alerts.length}</h2>
      {alerts.map((alert) => (
        <article className="critical-alert" key={alert.incident_id}>
          <h3>{alert.title}</h3>
          <p>{alert.reason}</p>
          {alert.quote && <blockquote>{alert.quote}</blockquote>}
          <p className="muted">
            {alert.accepted ? `Accepted by ${alert.owner ?? "department"}` : "Awaiting acceptance"}
            {" · Remains visible until human closure"}
          </p>
          {alert.evidence.length > 0 && (
            <p className="muted">Evidence: {alert.evidence.join(", ")}</p>
          )}
          <button onClick={() => onOpen(alert.incident_id)}>Review incident</button>
        </article>
      ))}
    </section>
  );
}
