import type { Alert } from "../types";

export default function AlertBanner({ alerts }: { alerts: Alert[] }) {
  if (alerts.length === 0) return null;
  return (
    <div className="alerts">
      {alerts.map((a, i) => (
        <div key={i} className="alert">⚠ {a.text}</div>
      ))}
    </div>
  );
}
