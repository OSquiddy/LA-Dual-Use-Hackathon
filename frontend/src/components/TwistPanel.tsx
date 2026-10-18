import { useEffect, useState } from 'react';
import { resetDemo, setTwist } from '../api';
import type { Twists } from '../types';
const TOGGLES: { name: keyof Omit<Twists, 'domain'>; label: string }[] = [
  { name: 'dept_silent', label: 'Department goes silent' }, { name: 'surge', label: 'Call surge' }, { name: 'phones_down', label: 'Phones down' },
];
export default function TwistPanel({ twists, controlledOpen, onToggle, live = false }: { twists: Twists; controlledOpen?: boolean; onToggle?: (open: boolean) => void; live?: boolean }) {
  const [localOpen, setLocalOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const open = controlledOpen ?? localOpen;
  const toggle = (value: boolean) => onToggle ? onToggle(value) : setLocalOpen(value);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 't' && !(e.target instanceof HTMLElement && (e.target.isContentEditable || /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)))) toggle(!open);
      if (e.key === 'Escape') toggle(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onToggle]);
  async function change(action: () => Promise<unknown>) {
    setPending(true); setMessage('');
    try { await action(); setMessage('Demo action acknowledged.'); setConfirmation(''); }
    catch { setMessage('Demo action failed. Check the backend before retrying.'); }
    finally { setPending(false); }
  }
  if (!open) return null;
  return <section className="twists" aria-label="Demo controls"><div className="section-heading"><h2>Demo controls</h2><button onClick={() => toggle(false)}>Close</button></div><p className="muted">Demonstration settings change the current environment.</p>{TOGGLES.map(t => <label key={t.name}><input type="checkbox" disabled={pending} checked={twists[t.name]} onChange={e => void change(() => setTwist(t.name, { on: e.target.checked }))} />{t.label}</label>)}
    <details><summary>Reset demonstration data</summary><p>Reset replaces all current incident records with the storm-night scenario.</p>{live ? <p>Reset is disabled in the dashboard while live calling is configured.</p> : <label>Type RESET to confirm<input value={confirmation} onChange={e => setConfirmation(e.target.value)} /></label>}<button disabled={live || pending || confirmation !== 'RESET'} onClick={() => void change(() => resetDemo('storm_night'))}>Reset: storm night</button></details>{message && <p role="status">{message}</p>}
  </section>;
}
