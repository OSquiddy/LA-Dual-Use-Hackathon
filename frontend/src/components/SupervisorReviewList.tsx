import type { AppState } from '../types';
import { assignmentStatus } from './AssignmentSummary';
export default function SupervisorReviewList({ state, onOpen }: { state: AppState; onOpen: (id: number) => void }) {
  const ranked = state.supervisor_queue.flatMap(id => state.incidents.find(i => i.id === id) ?? []);
  return <section className="workspace-panel supervisor-review" aria-label="Ranked supervisor queue"><h2>Supervisor queue <span>· top {ranked.length}</span></h2><p className="muted">Ranked attention queue. Critical flags remain visible separately until human closure.</p>
    {ranked.map((incident, index) => <button key={incident.id} className="supervisor-row" onClick={() => onOpen(incident.id)}><span className="queue-rank">{index + 1}</span><span><strong>{incident.title}</strong><small>{incident.assignment?.department_display_name ?? incident.department ?? 'Department not assigned'}</small><small>{incident.assignment?.owner_display_name ?? incident.owner ?? 'Individual not assigned'} · {assignmentStatus(incident)}</small></span><span className="risk">{incident.risk_score}/100</span></button>)}
    {!ranked.length && <p className="muted">No incidents currently appear in the ranked supervisor queue.</p>}
  </section>;
}
