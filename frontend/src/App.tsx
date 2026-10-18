import { useState } from 'react';
import { API_MODE } from './api';
import { useHandoffState } from './useHandoffState';
import { accepted, filterIncidents, initialFilters, type Filters } from './workspace';
import AlertBanner from './components/AlertBanner';
import CriticalAlerts from './components/CriticalAlerts';
import IncidentCard from './components/IncidentCard';
import IncidentDetail from './components/IncidentDetail';
import TwistPanel from './components/TwistPanel';
import DepartmentDirectory from './components/DepartmentDirectory';
import HistoryWorkspace from './components/HistoryWorkspace';
import Icon from './components/Icon';
import SupervisorReviewList from './components/SupervisorReviewList';
import BrandDialog from './components/BrandDialog';

type View = 'dashboard' | 'incidents' | 'departments' | 'history' | 'critical';
const navigation: { id: View; label: string }[] = [
  { id: 'dashboard', label: 'Operations Dashboard' }, { id: 'incidents', label: 'Incidents' },
  { id: 'departments', label: 'Departments' }, { id: 'history', label: 'Assignment History' }, { id: 'critical', label: 'Critical Review' },
];
export default function App() {
  const { state, error } = useHandoffState();
  const [openId, setOpenId] = useState<number | null>(null);
  const [view, setView] = useState<View>('dashboard');
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [demoOpen, setDemoOpen] = useState(false);
  const [logoOpen, setLogoOpen] = useState(false);
  const active = state?.incidents.filter(i => i.status !== 'closed') ?? [];
  const counts = [active.length, active.filter(i => !accepted(i)).length, state?.critical_alerts.length ?? 0, active.filter(accepted).length];
  const metricLabels = ['Active Incidents', 'Awaiting Acceptance', 'Critical Reviews', 'Accepted / In Progress'];
  const filtered = filterIncidents(active, filters);
  const changeFilter = (field: keyof Filters, value: string) => setFilters(f => ({ ...f, [field]: value }));
  return <div className="app">
    <a className="skip-link" href="#workspace">Skip to workspace</a>
    <aside className="sidebar">
      <div className="compact-brand"><img src="/assets/handoffproof-mark.svg" alt="" /><div><strong>HandoffProof</strong><span>INCIDENT ACCOUNTABILITY</span></div></div>
      <p className="nav-label">OPERATIONS WORKSPACE</p>
      <nav aria-label="Main navigation">{navigation.map(item => <button key={item.id} aria-current={view === item.id ? 'page' : undefined} onClick={() => setView(item.id)}>
        <Icon name={item.id} /><span>{item.label}</span>{item.id === 'critical' && counts[2] > 0 && <b className="nav-count">{counts[2]}</b>}
      </button>)}</nav>
      <div className="sidebar-bottom"><button className="demo-button" onClick={() => setDemoOpen(o => !o)}><Icon name="settings" />Demo controls</button>
        <div className="prototype"><span className="status-dot" /><strong>Prototype demo</strong><p>Not a city service.<br />Fictional response roster.</p></div></div>
    </aside>
    <div className="shell">
      <header className="topbar"><div><span className="eyebrow">LOS ANGELES DEMONSTRATION</span><strong>Municipal operations workspace</strong></div>
        <div className="connection"><span className={`status-dot ${error ? 'offline' : ''}`} />{error ? 'Connection interrupted' : state ? API_MODE === 'fixture' ? 'Fixture preview' : 'Backend connected' : 'Connecting'}
          {state && <time dateTime={state.now}>{new Intl.DateTimeFormat('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' }).format(new Date(state.now))}</time>}</div></header>
      <main id="workspace" tabIndex={-1}>
        <section className="page-intro"><div><div className="eyebrow">REPORT. ASSIGN. TRACK. VERIFY.</div><h1>{navigation.find(n => n.id === view)?.label}</h1><p>Clear responsibility. Documented handoffs. Evidence that stays visible.</p>
          <span className="mode-label">{state?.call_mode === 'live' ? state.automatic_live_enabled ? 'Live callbacks · automatic dispatch enabled' : 'Live callbacks · automatic dispatch paused' : 'Simulated callbacks'} · {state?.timing_profile ?? 'Connecting'} timing</span></div>
          <button className="brand-surface" aria-label="View complete official HandoffProof logo" onClick={() => setLogoOpen(true)}><img src="/assets/handoffproof-logo.png?v=route-accountability" alt="HandoffProof — Report, Assign, Track, Verify. Safer cities through accountability." /></button></section>
        {error && <div className="error" role="alert">Backend unreachable. {state ? 'Showing the last received data; updates and actions may be unavailable.' : 'Check the local server. Reconnecting automatically.'}</div>}
        {!state ? <div className="empty-state" role="status">{error ? 'Waiting for the backend connection.' : 'Loading operations workspace…'}</div> : <>
          <section className="metrics" aria-label="Live incident metrics">{metricLabels.map((label, index) => <button key={label} className={`metric metric-${index}`} onClick={() => { setView(index === 2 ? 'critical' : 'incidents'); setFilters({ ...initialFilters, ownership: index === 1 ? 'pending' : index === 3 ? 'accepted' : '' }); }}>
            <div className="metric-label">{label}<Icon name={index === 2 ? 'critical' : index === 3 ? 'history' : 'incidents'} /></div><strong>{counts[index]}</strong><span>{['Open cases across all departments', 'Human responsibility still pending', 'Persistent until human closure', 'Accepted responsibility; case still open'][index]}</span></button>)}</section>
          <AlertBanner alerts={state.alerts} />
          {(view === 'dashboard' || view === 'incidents') && <div className={view === 'dashboard' ? 'operations-grid' : ''}><section className="workspace-panel">
            <div className="section-heading"><div><h2>Incident workspace</h2><p>Prioritize evidence and complete the next handoff.</p></div><span className="count-label">{filtered.length} of {active.length} active</span></div>
            <div className="filters"><label className="search-field"><span className="sr-only">Search incidents</span><Icon name="search" /><input type="search" placeholder="Search incident, location, or person" value={filters.search} onChange={e => changeFilter('search', e.target.value)} /></label>
              <label><span>Department</span><select value={filters.department} onChange={e => changeFilter('department', e.target.value)}><option value="">All departments</option>{Array.from(new Set([...state.departments.map(d => d.name), ...active.map(i => i.department).filter((d): d is string => !!d)])).map(d => <option key={d}>{d}</option>)}</select></label>
              <label><span>Priority</span><select value={filters.priority} onChange={e => changeFilter('priority', e.target.value)}><option value="">All priorities</option>{['critical','high','medium','low'].map(p => <option key={p} value={p}>{p[0].toUpperCase()+p.slice(1)}</option>)}</select></label>
              <label><span>Ownership</span><select value={filters.ownership} onChange={e => changeFilter('ownership', e.target.value)}><option value="">All ownership states</option><option value="pending">Awaiting acceptance</option><option value="unrouted">Awaiting department</option><option value="department">Department only</option><option value="assigned">Awaiting acknowledgment</option><option value="acknowledged">Acknowledged</option><option value="accepted">Accepted</option></select></label>
              <label><span>Sort by</span><select value={filters.sort} onChange={e => changeFilter('sort', e.target.value)}><option value="risk">Highest risk</option><option value="age">Oldest first</option><option value="updated">Most recent update</option></select></label>
            </div>
            <div className="incident-list">{filtered.map(i => <IncidentCard key={i.id} incident={i} now={state.now} onOpen={setOpenId} />)}{!filtered.length && <div className="empty-state"><h3>{active.length ? 'No incidents match your filters' : 'No open incidents'}</h3><p>{active.length ? 'Try a different search or ownership state.' : 'New reports will appear here when received.'}</p>{active.length > 0 && <button onClick={() => setFilters(initialFilters)}>Clear filters</button>}</div>}</div>
          </section>{view === 'dashboard' && <aside className="review-rail">{state.critical_alerts.length ? <CriticalAlerts alerts={state.critical_alerts} incidents={state.incidents} onOpen={setOpenId} /> : <section className="workspace-panel"><h2>Critical review</h2><p className="muted">No critical review flags recorded.</p></section>}
            <SupervisorReviewList state={state} onOpen={setOpenId} />
            <section className="workspace-panel workload"><div className="section-heading"><h2>Department workload</h2><button className="text-button" onClick={() => setView('departments')}>View all <Icon name="arrow" /></button></div>{state.departments.map(d => <button className="workload-row" key={d.name} onClick={() => { setView('incidents'); setFilters({ ...initialFilters, department: d.name }); }}><span>{d.name}</span><strong>{d.active_incidents ?? active.filter(i => i.department === d.name).length}</strong></button>)}</section>
          </aside>}</div>}
          {view === 'critical' && (state.critical_alerts.length ? <CriticalAlerts alerts={state.critical_alerts} incidents={state.incidents} onOpen={setOpenId} /> : <div className="empty-state"><h2>No critical reviews</h2><p>No active critical review flags are recorded. Acceptance alone does not clear a safety flag.</p></div>)}
          {view === 'departments' && <DepartmentDirectory state={state} onOpen={setOpenId} onDepartment={department => { setFilters({ ...initialFilters, department }); setView('incidents'); }} />}
          {view === 'history' && <HistoryWorkspace onOpen={setOpenId} />}
          <footer className="workspace-footer"><span>Prototype demo · not a city service</span><span>Assignment records a handoff. Acceptance records human responsibility.</span></footer>
        </>}
      </main>
    </div>
    {openId !== null && <IncidentDetail id={openId} onClose={() => setOpenId(null)} />}
    {state && <TwistPanel twists={state.twists} controlledOpen={demoOpen} onToggle={setDemoOpen} live={state.call_mode === 'live'} />}
    {logoOpen && <BrandDialog onClose={() => setLogoOpen(false)} />}
  </div>;
}
