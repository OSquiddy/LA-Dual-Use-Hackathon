import type { Incident } from './types';

export const priority = (i: Incident) => i.critical ? 'critical' : i.priority ?? (i.risk_score >= 60 ? 'high' : i.risk_score >= 30 ? 'medium' : 'low');
export const accepted = (i: Incident) => i.assignment ? Boolean(i.assignment.accepted_at) : i.accepted;
export const acknowledged = (i: Incident) => i.assignment ? Boolean(i.assignment.acknowledged_at) : i.acknowledged;
export function ownership(i: Incident) {
  if (i.status === 'closed') return 'closed';
  if (accepted(i)) return 'accepted';
  if (acknowledged(i)) return 'acknowledged';
  if (!(i.assignment?.department ?? i.department)) return 'unrouted';
  return (i.assignment?.owner ?? i.owner) ? 'assigned' : 'department';
}
export interface Filters { search: string; department: string; priority: string; ownership: string; sort: string }
export const initialFilters: Filters = { search: '', department: '', priority: '', ownership: '', sort: 'risk' };
export function filterIncidents(incidents: Incident[], filters: Filters): Incident[] {
  const needle = filters.search.trim().toLowerCase();
  const timestamp = (s?: string | null) => s && Number.isFinite(Date.parse(s)) ? Date.parse(s) : 0;
  return incidents.filter(i => i.status !== 'closed')
    .filter(i => !needle || [i.id, i.title, i.department, i.owner, i.assignment?.department_display_name, i.assignment?.operational_unit, i.assignment?.owner_display_name, i.assignment?.owner_role].join(' ').toLowerCase().includes(needle))
    .filter(i => !filters.department || (i.assignment?.department ?? i.department) === filters.department)
    .filter(i => !filters.priority || priority(i) === filters.priority)
    .filter(i => !filters.ownership || (filters.ownership === 'pending' ? !accepted(i) : ownership(i) === filters.ownership))
    .sort((a,b) => (filters.sort === 'age' ? timestamp(a.created_at) - timestamp(b.created_at) : filters.sort === 'updated' ? timestamp(b.updated_at) - timestamp(a.updated_at) : b.risk_score - a.risk_score) || a.id - b.id);
}
