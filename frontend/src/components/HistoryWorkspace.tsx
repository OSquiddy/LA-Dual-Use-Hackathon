import { useEffect, useState } from 'react';
import { fetchAssignmentHistory } from '../api';
import type { AssignmentHistoryEntry } from '../types';
import { AssignmentTime } from './AssignmentSummary';
export default function HistoryWorkspace({ onOpen }: { onOpen: (id: number) => void }) {
  const [entries, setEntries] = useState<AssignmentHistoryEntry[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setPending(true); setError(false);
    fetchAssignmentHistory().then(page => { if (active) { setEntries(page.entries); setCursor(page.next_before_id); } }).catch(() => { if (active) setError(true); }).finally(() => { if (active) setPending(false); });
    return () => { active = false; };
  }, [revision]);
  async function loadMore() {
    if (!cursor || pending) return;
    setPending(true); setError(false);
    try { const page = await fetchAssignmentHistory(cursor); setEntries(old => [...old, ...page.entries.filter(e => !old.some(o => o.assignment.id === e.assignment.id))]); setCursor(page.next_before_id); }
    catch { setError(true); } finally { setPending(false); }
  }
  return <section className="workspace-panel"><div className="section-heading"><div><h2>Assignment audit trail</h2><p>Recorded handoffs across active and closed incidents. Newest assignments first.</p></div><button disabled={pending} onClick={() => setRevision(r => r + 1)}>Refresh history</button></div>
    {error && <p className="error" role="alert">Assignment history unavailable. Retry without changing existing records.</p>}
    <div className="audit-table"><table><thead><tr><th>Incident</th><th>Responsible department / individual</th><th>Assigned / initiated by</th><th>Human actions</th><th>Review</th></tr></thead><tbody>{entries.map((e,index) => <tr key={e.assignment.id ?? index}><td><strong>#{e.incident_id} · {e.title}</strong><small>{e.status}</small></td><td>{e.assignment.department_display_name ?? e.assignment.department}<small>{e.assignment.operational_unit ?? 'Unit not recorded'}</small><strong>{e.assignment.owner_display_name ?? e.assignment.owner ?? 'Individual not assigned'}</strong><small>{e.assignment.owner_role ?? 'Role not recorded'}</small></td><td><AssignmentTime value={e.assignment.assigned_at} /><small>{e.assignment.assigned_by ?? 'Initiator not recorded'}</small><small>{e.assignment.change_reason ?? 'No reason recorded'}</small></td><td><div>Acknowledgment: {e.assignment.acknowledged_at ? <><AssignmentTime value={e.assignment.acknowledged_at} /> · {e.assignment.acknowledged_by}</> : 'Not recorded'}</div><div>Acceptance: {e.assignment.accepted_at ? <><AssignmentTime value={e.assignment.accepted_at} /> · {e.assignment.accepted_by}</> : 'Not accepted'}</div></td><td><button onClick={() => onOpen(e.incident_id)}>Review #{e.incident_id}</button></td></tr>)}</tbody></table></div>
    {!entries.length && !pending && !error && <div className="empty-state">No assignment history recorded.</div>}{pending && <p role="status">Loading assignment history…</p>}{cursor && <button disabled={pending} onClick={() => void loadMore()}>Load earlier assignments</button>}
  </section>;
}
