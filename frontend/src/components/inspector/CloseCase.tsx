import { useEffect, useState } from "react";
import { Flag } from "lucide-react";

interface Props {
  operator: string;
  onClose: (by: string, note: string) => void;
}

/** Human-only resolution. Nothing in the engine can close a case. */
export default function CloseCase({ operator, onClose }: Props) {
  const [open, setOpen] = useState(false);
  const [by, setBy] = useState(operator);
  const [note, setNote] = useState("");
  useEffect(() => setBy(operator), [operator]);

  return (
    <section className="card">
      <div className="card-head" style={{ marginBottom: open ? 14 : 0 }}>
        <h3 className="card-title"><Flag /> Resolve &amp; close</h3>
        {!open && (
          <button className="btn sm" onClick={() => setOpen(true)}>Record resolution…</button>
        )}
      </div>
      {open && (
        <form
          className="close-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (by.trim() && note.trim()) onClose(by.trim(), note.trim());
          }}
        >
          <label className="field">
            Closed by
            <input value={by} onChange={(e) => setBy(e.target.value)} required />
          </label>
          <label className="field">
            What was verified as done?
            <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Crew cleared the drain at Ave 52; water receding" required />
          </label>
          <div className="close-row">
            <p className="close-note">
              Only close when the work is verified. A "better" callback or silence never closes a case.
            </p>
            <span style={{ display: "flex", gap: 8 }}>
              <button type="button" className="btn ghost sm" onClick={() => setOpen(false)}>Cancel</button>
              <button type="submit" className="btn sm danger-outline" disabled={!by.trim() || !note.trim()}>Close case</button>
            </span>
          </div>
        </form>
      )}
    </section>
  );
}
