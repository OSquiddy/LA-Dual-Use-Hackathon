import type { Incident } from '../types';
import AssignmentSummary, { AssignmentTime } from './AssignmentSummary';
import { priority } from '../workspace';
interface Props { incident: Incident; now: string; rank?: number; onOpen: (id: number) => void; onAccept?: (incident: Incident) => void }
export default function IncidentCard({ incident, now, rank, onOpen, onAccept }: Props) {
  const level = priority(incident);
  const next = incident.next_step_at ? Math.max(0, Math.round((Date.parse(incident.next_step_at) - Date.parse(now)) / 1000)) : null;
  const safeReason = incident.why.length > 260 || /[\r\n]|\b(?:Agent|User|Assistant):/i.test(incident.why) ? 'Review incident evidence for the current assessment.' : incident.why;
  return <article className={`card priority-${level}`}>
    <div className="card-head"><div><div className="incident-identifier">INCIDENT #{incident.id}{rank !== undefined && ` · SUPERVISOR RANK ${rank}`}</div><h3>{incident.title}</h3></div><span className={`priority-pill ${level}`}>{level}</span></div>
    <AssignmentSummary incident={incident} compact />
    <div className="card-evidence"><p>{safeReason}</p><span className="risk">Risk {incident.risk_score}/100</span></div>
    <div className="card-footer"><div className="meta"><span>{incident.report_count} {incident.report_count === 1 ? 'report' : 'reports'}</span><span>Updated <AssignmentTime value={incident.updated_at} /></span>{incident.callback_state && <span>Callback: {incident.callback_state}</span>}{next !== null && <span>Next step: {next}s</span>}</div><button className="text-button" onClick={() => onOpen(incident.id)}>Review incident <span aria-hidden="true">→</span></button>{onAccept && !incident.accepted && incident.status !== 'closed' && <button onClick={() => onAccept(incident)}>Accept</button>}</div>
    {incident.debts.length > 0 && <ul className="debts">{incident.debts.map(d => <li key={d.kind}>{d.label}</li>)}</ul>}
  </article>;
}
