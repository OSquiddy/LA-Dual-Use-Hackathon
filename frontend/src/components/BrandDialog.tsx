import { useEffect, useRef } from 'react';
export default function BrandDialog({ onClose }: { onClose: () => void }) {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    close.current?.focus();
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
      if (event.key === 'Tab') { event.preventDefault(); close.current?.focus(); }
    };
    document.addEventListener('keydown', keyboard);
    return () => { document.body.style.overflow = overflow; document.removeEventListener('keydown', keyboard); previous?.focus(); };
  }, []);
  return <div className="modal-backdrop" onClick={onClose}><section className="logo-dialog" role="dialog" aria-modal="true" aria-label="Official HandoffProof identity" onClick={event => event.stopPropagation()}><button ref={close} onClick={onClose}>Close logo</button><img src="/assets/handoffproof-logo.png" alt="HandoffProof. Report, Assign, Track, Verify. Safer cities through accountability." /></section></div>;
}
